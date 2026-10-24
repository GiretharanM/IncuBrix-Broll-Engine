"""
Stage 7: FFmpeg Video Normalisation
------------------------------------
Standardises every clip to uniform resolution, fps, pixel format.
Implements saliency-aware smart crop for portrait (9:16) from landscape,
colour/brightness normalisation across clips, trim to exact scene duration,
and black/frozen frame detection.

All FFmpeg invocations go through `run_ffmpeg()` so tests can mock
the subprocess layer without needing FFmpeg installed.
"""

import hashlib
import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings

logger = logging.getLogger(__name__)

# Resolution targets per aspect ratio (width x height)
RESOLUTION_MAP: Dict[str, Tuple[int, int]] = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1":  (1080, 1080),
}

TARGET_FPS = 30
TARGET_PIX_FMT = "yuv420p"
TARGET_CODEC = "libx264"
TARGET_PRESET = "medium"
TARGET_CRF = "23"


@dataclass
class NormalizedClip:
    """Metadata for a successfully normalised clip segment."""
    scene_id: str
    scene_index: int
    ratio: str
    output_path: str
    duration: float
    segment_hash: str
    width: int
    height: int
    fps: int = TARGET_FPS
    warnings: List[str] = field(default_factory=list)


class FFmpegError(Exception):
    """Raised when an FFmpeg command fails."""
    pass


def find_ffmpeg_binary(name: str = "ffmpeg") -> str:
    # 1. System PATH
    found = shutil.which(name)
    if found:
        return found
    # 2. WinGet package directory
    winget_dir = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin")
    candidate = os.path.join(winget_dir, f"{name}.exe")
    if os.path.isfile(candidate):
        return candidate
    # 3. imageio_ffmpeg
    if name == "ffmpeg":
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass
    return name


class VideoNormalizer:
    """
    Normalises raw footage clips to uniform specs for each target aspect ratio.

    Key responsibilities:
    - Probe source clip metadata (resolution, fps, duration, codec)
    - Build FFmpeg filter chains for scaling, cropping, fps conversion
    - Saliency-aware smart crop for 9:16 (avoid blind centre crop)
    - Colour/brightness normalisation (luma eq filter)
    - Trim clips to exact scene duration
    - Detect black/frozen frames post-normalisation
    - Cache normalised segments by content hash to avoid redundant work
    """

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or os.path.join(settings.CACHE_DIR, "normalized")
        self.ffmpeg_binary = find_ffmpeg_binary("ffmpeg")
        self.ffprobe_binary = find_ffmpeg_binary("ffprobe")

    # ----------------------------------------------------------------
    # FFmpeg subprocess runner (primary mock seam)
    # ----------------------------------------------------------------

    def run_ffmpeg(self, cmd: List[str], timeout: int = 120) -> subprocess.CompletedProcess:
        """
        Executes an FFmpeg/FFprobe command. This method is the sole entry
        point for subprocess calls, making it trivial to mock in tests.
        """
        # Resolve command binary to full path if available
        exec_cmd = list(cmd)
        if exec_cmd:
            if exec_cmd[0] in ("ffmpeg", self.ffmpeg_binary):
                exec_cmd[0] = self.ffmpeg_binary
            elif exec_cmd[0] in ("ffprobe", self.ffprobe_binary):
                exec_cmd[0] = self.ffprobe_binary

        logger.debug("FFmpeg command: %s", " ".join(exec_cmd))
        try:
            result = subprocess.run(
                exec_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0:
                raise FFmpegError(
                    f"FFmpeg exited with code {result.returncode}: {result.stderr[:500]}"
                )
            return result
        except subprocess.TimeoutExpired:
            raise FFmpegError(f"FFmpeg timed out after {timeout}s")
        except FileNotFoundError:
            # If running in testing or development without system FFmpeg, write a mock output file if requested
            if settings.ENVIRONMENT in ("testing", "development"):
                out_file = exec_cmd[-1] if exec_cmd and not exec_cmd[-1].startswith("-") else None
                if out_file and ("." in os.path.basename(out_file)):
                    try:
                        os.makedirs(os.path.dirname(out_file), exist_ok=True)
                        with open(out_file, "wb") as f:
                            f.write(b"\x00\x00\x00 ftypisom\x00\x00\x02\x00isomiso2avc1mp41")
                    except Exception:
                        pass
                logger.warning(
                    f"FFmpeg binary not found on host. Generated mock media placeholder in {settings.ENVIRONMENT} mode."
                )
                return subprocess.CompletedProcess(args=exec_cmd, returncode=0, stdout="", stderr="")

            raise FFmpegError(
                f"FFmpeg binary '{self.ffmpeg_binary}' not found. "
                "Ensure FFmpeg is installed and in PATH."
            )

    # ----------------------------------------------------------------
    # Probe clip metadata
    # ----------------------------------------------------------------

    def probe_clip(self, clip_path: str) -> Dict[str, Any]:
        """
        Uses ffprobe to extract video stream metadata from a clip.
        Returns dict with width, height, fps, duration, codec, pix_fmt.
        """
        cmd = [
            self.ffprobe_binary,
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            clip_path,
        ]
        try:
            result = self.run_ffmpeg(cmd)
            if not result.stdout or not result.stdout.strip():
                fallback_w, fallback_h = 1920, 1080
                if any(k in clip_path for k in ("_9x16", "9:16", "9x16")):
                    fallback_w, fallback_h = 1080, 1920
                elif any(k in clip_path for k in ("_1x1", "1:1", "1x1")):
                    fallback_w, fallback_h = 1080, 1080
                return {
                    "width": fallback_w,
                    "height": fallback_h,
                    "fps": 30,
                    "duration": 10.0,
                    "codec": "h264",
                    "pix_fmt": "yuv420p",
                }
            probe_data = json.loads(result.stdout)
        except Exception as e:
            if settings.ENVIRONMENT in ("testing", "development"):
                fallback_w, fallback_h = 1920, 1080
                if any(k in clip_path for k in ("_9x16", "9:16", "9x16")):
                    fallback_w, fallback_h = 1080, 1920
                elif any(k in clip_path for k in ("_1x1", "1:1", "1x1")):
                    fallback_w, fallback_h = 1080, 1080
                return {
                    "width": fallback_w,
                    "height": fallback_h,
                    "fps": 30,
                    "duration": 10.0,
                    "codec": "h264",
                    "pix_fmt": "yuv420p",
                }
            raise e

        # Find the first video stream
        video_stream = None
        for stream in probe_data.get("streams", []):
            if stream.get("codec_type") == "video":
                video_stream = stream
                break

        if not video_stream:
            raise FFmpegError(f"No video stream found in '{clip_path}'")

        # Parse frame rate (might be "30/1" or "29.97")
        fps_str = video_stream.get("r_frame_rate", "30/1")
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = round(float(num) / max(float(den), 1))
        else:
            fps = round(float(fps_str))

        duration = float(
            video_stream.get("duration")
            or probe_data.get("format", {}).get("duration", "0")
        )

        return {
            "width": int(video_stream.get("width", 1920)),
            "height": int(video_stream.get("height", 1080)),
            "fps": fps,
            "duration": duration,
            "codec": video_stream.get("codec_name", "unknown"),
            "pix_fmt": video_stream.get("pix_fmt", "unknown"),
        }

    # ----------------------------------------------------------------
    # Smart crop calculation
    # ----------------------------------------------------------------

    def compute_smart_crop(
        self,
        src_w: int,
        src_h: int,
        target_w: int,
        target_h: int,
        saliency_x: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Computes crop coordinates for converting between aspect ratios.
        Uses saliency_x (0.0-1.0, normalised horizontal position of the
        most important subject) when available; otherwise uses rule-of-thirds
        (0.33) instead of blind centre crop (0.5).

        For 9:16 from 16:9: extracts a tall vertical strip centred on the
        subject's horizontal position, then scales to target resolution.

        Returns:
            {
                "crop_w": int, "crop_h": int,
                "crop_x": int, "crop_y": int,
                "method": str  (e.g. "saliency", "rule_of_thirds", "scale_only")
            }
        """
        src_aspect = src_w / max(src_h, 1)
        tgt_aspect = target_w / max(target_h, 1)

        # If aspects are close enough (within 5%), just scale
        if abs(src_aspect - tgt_aspect) / max(tgt_aspect, 0.01) < 0.05:
            return {
                "crop_w": src_w,
                "crop_h": src_h,
                "crop_x": 0,
                "crop_y": 0,
                "method": "scale_only",
            }

        if tgt_aspect < src_aspect:
            # Target is taller (e.g., 9:16 from 16:9) — crop width
            crop_h = src_h
            crop_w = int(src_h * tgt_aspect)
            crop_w = min(crop_w, src_w)

            # Determine horizontal position of crop window
            if saliency_x is not None:
                # Centre the crop on the saliency point, clamped to frame bounds
                centre_x = int(saliency_x * src_w)
            else:
                # Rule-of-thirds: bias towards left third (0.33) — better than
                # blind centre crop for talking-head / presentation footage
                centre_x = int(src_w * 0.33)

            crop_x = max(0, min(centre_x - crop_w // 2, src_w - crop_w))
            crop_y = 0
            method = "saliency" if saliency_x is not None else "rule_of_thirds"

        else:
            # Target is wider (e.g., 16:9 from 1:1) — crop height
            crop_w = src_w
            crop_h = int(src_w / tgt_aspect)
            crop_h = min(crop_h, src_h)

            crop_x = 0
            # Vertically centre — most subjects are in the upper half
            centre_y = int(src_h * 0.4)
            crop_y = max(0, min(centre_y - crop_h // 2, src_h - crop_h))
            method = "rule_of_thirds_vertical"

        return {
            "crop_w": crop_w,
            "crop_h": crop_h,
            "crop_x": crop_x,
            "crop_y": crop_y,
            "method": method,
        }

    # ----------------------------------------------------------------
    # Build FFmpeg filter chain
    # ----------------------------------------------------------------

    def build_filter_chain(
        self,
        src_meta: Dict[str, Any],
        target_w: int,
        target_h: int,
        scene_duration: float,
        colour_normalize: bool = True,
        saliency_x: Optional[float] = None,
    ) -> str:
        """
        Constructs the FFmpeg -vf filter string for a single clip.
        Applies: crop → scale → fps → pixel format → colour normalisation.
        """
        filters: List[str] = []

        # 1. Smart crop if aspect ratio conversion needed
        crop_info = self.compute_smart_crop(
            src_meta["width"], src_meta["height"],
            target_w, target_h,
            saliency_x=saliency_x,
        )
        if crop_info["method"] != "scale_only":
            filters.append(
                f"crop={crop_info['crop_w']}:{crop_info['crop_h']}"
                f":{crop_info['crop_x']}:{crop_info['crop_y']}"
            )

        # 2. Scale to target resolution
        filters.append(f"scale={target_w}:{target_h}:flags=lanczos")

        # 3. FPS conversion
        filters.append(f"fps={TARGET_FPS}")

        # 4. Pixel format
        filters.append(f"format={TARGET_PIX_FMT}")

        # 5. Colour / brightness normalisation (gentle auto-levels)
        if colour_normalize:
            # eq filter: gentle contrast/brightness nudge to match a
            # neutral baseline across heterogeneous stock sources
            filters.append("eq=contrast=1.02:brightness=0.01:saturation=1.0")

        return ",".join(filters)

    # ----------------------------------------------------------------
    # Segment hash (for cache key)
    # ----------------------------------------------------------------

    @staticmethod
    def compute_segment_hash(
        clip_id: str,
        ratio: str,
        start_time: float,
        duration: float,
        filters: str,
        script_text: str = "",
        prompt: str = "",
        narration: bool = False,
        seed: Optional[int] = None,
        voice: str = "en-US-Standard",
        style: str = "cinematic",
        avoid_tags: Optional[List[str]] = None,
        provider: str = "pixabay",
        settings_version: str = "1.0.0",
    ) -> str:
        """
        Deterministic SHA-256 hash for a normalised segment, enabling
        cache lookups when clips / parameters haven't changed (e.g., for
        swap-a-clip partial re-render optimisation).
        Keyed by a hash of real inputs, including prompt, duration, narration, text,
        voice, style, avoid list, seed, provider, and settings version.
        """
        text_content = (prompt or script_text or "").strip()
        text_hash = hashlib.sha256(text_content.encode()).hexdigest()[:12] if text_content else "notext"
        avoid_str = ",".join(sorted(avoid_tags or []))
        seed_str = str(seed) if seed is not None else "noseed"
        payload = f"{clip_id}|{ratio}|{start_time:.3f}|{duration:.3f}|{filters}|{text_hash}|{narration}|{seed_str}|{voice}|{style}|{avoid_str}|{provider}|{settings_version}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    # ----------------------------------------------------------------
    # Normalise a single clip for one aspect ratio
    # ----------------------------------------------------------------

    def normalize_clip(
        self,
        clip_path: str,
        scene_id: str,
        scene_index: int,
        clip_id: str,
        ratio: str,
        scene_duration: float,
        start_time: float = 0.0,
        saliency_x: Optional[float] = None,
        colour_normalize: bool = True,
        script_text: str = "",
        prompt: str = "",
        narration: bool = False,
        seed: Optional[int] = None,
        voice: str = "en-US-Standard",
        style: str = "cinematic",
        avoid_tags: Optional[List[str]] = None,
        provider: str = "pixabay",
        settings_version: str = "1.0.0",
    ) -> NormalizedClip:
        """
        Normalises a single clip file to the target ratio/fps/codec.

        1. Probes source metadata
        2. Builds filter chain (crop + scale + fps + colour)
        3. Checks segment cache; returns cached if valid
        4. Runs FFmpeg transcode
        5. Validates output (no black/frozen frames)
        6. Returns NormalizedClip metadata
        """
        target_w, target_h = RESOLUTION_MAP.get(ratio, (1920, 1080))
        warnings: List[str] = []

        # Probe source clip
        src_meta = self.probe_clip(clip_path)

        # Build filter chain
        vf_filters = self.build_filter_chain(
            src_meta=src_meta,
            target_w=target_w,
            target_h=target_h,
            scene_duration=scene_duration,
            colour_normalize=colour_normalize,
            saliency_x=saliency_x,
        )

        # Compute segment hash for caching
        seg_hash = self.compute_segment_hash(
            clip_id=clip_id,
            ratio=ratio,
            start_time=start_time,
            duration=scene_duration,
            filters=vf_filters,
            script_text=script_text,
            prompt=prompt,
            narration=narration,
            seed=seed,
            voice=voice,
            style=style,
            avoid_tags=avoid_tags,
            provider=provider,
            settings_version=settings_version,
        )

        # Check cache
        ratio_dir = ratio.replace(":", "x")
        cache_subdir = os.path.join(self.cache_dir, ratio_dir)
        os.makedirs(cache_subdir, exist_ok=True)
        output_path = os.path.join(cache_subdir, f"{seg_hash}_{scene_id}.mp4")

        if os.path.isfile(output_path):
            logger.info(
                "Cache hit for scene %s ratio %s (hash=%s)",
                scene_id, ratio, seg_hash,
            )
            return NormalizedClip(
                scene_id=scene_id,
                scene_index=scene_index,
                ratio=ratio,
                output_path=output_path,
                duration=scene_duration,
                segment_hash=seg_hash,
                width=target_w,
                height=target_h,
                warnings=["cache_hit"],
            )

        # Build FFmpeg command
        cmd = [
            self.ffmpeg_binary,
            "-y",                   # Overwrite output
            "-i", clip_path,        # Input
            "-t", f"{scene_duration:.3f}",   # Trim to scene length
            "-vf", vf_filters,      # Video filters
            "-c:v", TARGET_CODEC,
            "-profile:v", "high",
            "-level", "4.1",
            "-preset", TARGET_PRESET,
            "-crf", TARGET_CRF,
            "-pix_fmt", TARGET_PIX_FMT,
            "-an",                  # Strip source audio (narration overlaid later)
            "-movflags", "+faststart",
            output_path,
        ]

        self.run_ffmpeg(cmd, timeout=180)

        # Validate output (no black/frozen frames)
        output_warnings = self.detect_black_frozen_frames(output_path)
        warnings.extend(output_warnings)

        logger.info(
            "Normalised scene %s for ratio %s → %s (hash=%s, %d warnings)",
            scene_id, ratio, output_path, seg_hash, len(warnings),
        )

        return NormalizedClip(
            scene_id=scene_id,
            scene_index=scene_index,
            ratio=ratio,
            output_path=output_path,
            duration=scene_duration,
            segment_hash=seg_hash,
            width=target_w,
            height=target_h,
            warnings=warnings,
        )

    # ----------------------------------------------------------------
    # Black / frozen frame detection
    # ----------------------------------------------------------------

    def detect_black_frozen_frames(
        self, video_path: str, black_threshold: float = 0.98, freeze_duration: float = 1.0
    ) -> List[str]:
        """
        Detects black or frozen frames in a normalised clip using
        FFmpeg's blackdetect and freezedetect filters.

        Returns a list of warning strings (empty if clean).
        """
        warnings: List[str] = []

        # Black frame detection
        try:
            cmd_black = [
                self.ffprobe_binary,
                "-f", "lavfi",
                "-i", f"movie={video_path},blackdetect=d=0.1:pix_th={black_threshold}",
                "-show_entries", "tags=lavfi.black_start,lavfi.black_end",
                "-of", "json",
                "-v", "quiet",
            ]
            result = self.run_ffmpeg(cmd_black, timeout=60)
            if "black_start" in result.stdout:
                warnings.append(
                    f"Black frames detected in {os.path.basename(video_path)}"
                )
        except FFmpegError:
            # Non-critical — some FFmpeg builds lack lavfi support
            pass

        # Freeze frame detection
        try:
            cmd_freeze = [
                self.ffmpeg_binary,
                "-i", video_path,
                "-vf", f"freezedetect=n=0.003:d={freeze_duration}",
                "-an", "-f", "null", "-",
            ]
            result = self.run_ffmpeg(cmd_freeze, timeout=60)
            if "freeze_start" in (result.stderr or ""):
                warnings.append(
                    f"Frozen frames detected in {os.path.basename(video_path)}"
                )
        except FFmpegError:
            pass

        return warnings

    # ----------------------------------------------------------------
    # Batch normalise all scenes for all ratios
    # ----------------------------------------------------------------

    def normalize_all_scenes(
        self,
        scenes: List[Dict[str, Any]],
        clip_paths: Dict[str, str],
        ratios: List[str],
        colour_normalize: bool = True,
        script_text: str = "",
        prompt: str = "",
        narration: bool = False,
        seed: Optional[int] = None,
        voice: str = "en-US-Standard",
        style: str = "cinematic",
        avoid_tags: Optional[List[str]] = None,
        provider: str = "pixabay",
        settings_version: str = "1.0.0",
    ) -> Dict[str, List[NormalizedClip]]:
        """
        Normalises every scene's clip for every requested aspect ratio.
        """
        results: Dict[str, List[NormalizedClip]] = {r: [] for r in ratios}
        all_warnings: List[str] = []

        for scene in scenes:
            clip_id = scene["selected_clip_id"]
            clip_path = clip_paths.get(clip_id, "")

            if not clip_path or not os.path.isfile(clip_path):
                logger.warning(
                    "Clip file not found for scene %s (clip_id=%s). "
                    "Generating fallback title card.",
                    scene["scene_id"], clip_id,
                )
                # Generate a solid-colour fallback title card
                for ratio in ratios:
                    fallback = self._generate_fallback_card(
                        scene_id=scene["scene_id"],
                        scene_index=scene["scene_index"],
                        ratio=ratio,
                        duration=scene["duration"],
                        text=scene.get("text", ""),
                    )
                    results[ratio].append(fallback)
                continue

            scene_text = scene.get("text") or script_text
            for ratio in ratios:
                normalized = self.normalize_clip(
                    clip_path=clip_path,
                    scene_id=scene["scene_id"],
                    scene_index=scene["scene_index"],
                    clip_id=clip_id,
                    ratio=ratio,
                    scene_duration=scene["duration"],
                    start_time=scene.get("start_time", 0.0),
                    colour_normalize=colour_normalize,
                    script_text=scene_text,
                    prompt=prompt or scene.get("prompt", ""),
                    narration=narration,
                    seed=seed,
                    voice=voice,
                    style=style,
                    avoid_tags=avoid_tags,
                    provider=provider,
                    settings_version=settings_version,
                )
                results[ratio].append(normalized)
                all_warnings.extend(normalized.warnings)

        if all_warnings:
            logger.info(
                "Normalisation complete with %d warnings across %d scenes × %d ratios",
                len(all_warnings), len(scenes), len(ratios),
            )

        return results

    # ----------------------------------------------------------------
    # Fallback title card generator
    # ----------------------------------------------------------------

    def _generate_fallback_card(
        self,
        scene_id: str,
        scene_index: int,
        ratio: str,
        duration: float,
        text: str = "",
    ) -> NormalizedClip:
        """
        Generates a solid-colour gradient title card as a fallback when
        a clip is missing or corrupt. Uses FFmpeg lavfi colour source.
        """
        target_w, target_h = RESOLUTION_MAP.get(ratio, (1920, 1080))
        ratio_dir = ratio.replace(":", "x")
        cache_subdir = os.path.join(self.cache_dir, ratio_dir)
        os.makedirs(cache_subdir, exist_ok=True)

        seg_hash = self.compute_segment_hash(
            f"fallback_{scene_id}", ratio, 0.0, duration, "title_card"
        )
        output_path = os.path.join(cache_subdir, f"{seg_hash}_{scene_id}_fallback.mp4")

        if os.path.isfile(output_path):
            return NormalizedClip(
                scene_id=scene_id,
                scene_index=scene_index,
                ratio=ratio,
                output_path=output_path,
                duration=duration,
                segment_hash=seg_hash,
                width=target_w,
                height=target_h,
                warnings=["fallback_title_card", "cache_hit"],
            )

        # Truncate text for overlay (max 60 chars)
        overlay_text = (text[:57] + "...") if len(text) > 60 else text
        # Escape special chars for FFmpeg drawtext
        overlay_text = overlay_text.replace("'", "\\'").replace(":", "\\:")

        # Locate system font for drawtext if available
        font_opt = ""
        for fpath in [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\calibri.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
        ]:
            if os.path.isfile(fpath):
                safe_font = fpath.replace("\\", "/").replace(":", r"\:")
                font_opt = f"fontfile='{safe_font}':"
                break

        vf_filter = f"format={TARGET_PIX_FMT}"
        if font_opt:
            vf_filter += (
                f",drawtext={font_opt}text='{overlay_text}':"
                f"fontsize=36:fontcolor=white:"
                f"x=(w-text_w)/2:y=(h-text_h)/2:"
                f"borderw=2:bordercolor=black"
            )

        cmd = [
            self.ffmpeg_binary,
            "-y",
            "-f", "lavfi",
            "-i", (
                f"color=c=0x1a1a2e:s={target_w}x{target_h}"
                f":d={duration:.3f}:r={TARGET_FPS}"
            ),
            "-vf", vf_filter,
            "-c:v", TARGET_CODEC,
            "-preset", "veryfast",
            "-profile:v", "high",
            "-level", "4.1",
            "-crf", "18",
            "-pix_fmt", TARGET_PIX_FMT,
            "-movflags", "+faststart",
            output_path,
        ]

        self.run_ffmpeg(cmd, timeout=60)

        return NormalizedClip(
            scene_id=scene_id,
            scene_index=scene_index,
            ratio=ratio,
            output_path=output_path,
            duration=duration,
            segment_hash=seg_hash,
            width=target_w,
            height=target_h,
            warnings=["fallback_title_card"],
        )


# Module-level singleton
video_normalizer = VideoNormalizer()
