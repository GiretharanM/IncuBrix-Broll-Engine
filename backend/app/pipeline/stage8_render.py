"""
Stage 8: Video Rendering
-------------------------
Concatenates normalised scene segments, overlays narration audio,
generates SRT caption files, renders ASS burn-in subtitles,
and produces one output video per aspect ratio.

Output: video_{ratio}.mp4 (H.264/AAC, 30fps, 1080p-class)
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.pipeline.stage7_normalize import (
    FFmpegError,
    NormalizedClip,
    TARGET_CODEC,
    TARGET_FPS,
    TARGET_PIX_FMT,
    RESOLUTION_MAP,
    VideoNormalizer,
    video_normalizer,
)

logger = logging.getLogger(__name__)


class CaptionGenerator:
    """
    Generates SRT and ASS caption files from word-level transcript data.
    Supports grouping words into timed subtitle cues.
    """

    @staticmethod
    def build_srt(
        transcript_words: List[Dict[str, Any]],
        max_words_per_cue: int = 8,
        max_cue_duration: float = 4.0,
    ) -> str:
        """
        Generates SRT-formatted subtitle string from word timestamps.

        Groups words into cues of up to max_words_per_cue words,
        with a maximum duration of max_cue_duration seconds per cue.
        """
        if not transcript_words:
            return ""

        cues: List[Tuple[float, float, str]] = []
        current_words: List[str] = []
        cue_start: Optional[float] = None

        for word_info in transcript_words:
            word = word_info.get("word", "")
            start = word_info.get("start", 0.0)
            end = word_info.get("end", start + 0.1)

            if not word.strip():
                continue

            if cue_start is None:
                cue_start = start

            current_words.append(word)

            # Flush cue if we've hit the word limit or duration limit
            if (
                len(current_words) >= max_words_per_cue
                or (end - cue_start) >= max_cue_duration
            ):
                cues.append((cue_start, end, " ".join(current_words)))
                current_words = []
                cue_start = None

        # Flush remaining words
        if current_words and cue_start is not None:
            last_end = transcript_words[-1].get("end", cue_start + 0.5)
            cues.append((cue_start, last_end, " ".join(current_words)))

        # Format as SRT
        srt_lines: List[str] = []
        for idx, (start, end, text) in enumerate(cues, 1):
            srt_lines.append(str(idx))
            srt_lines.append(
                f"{CaptionGenerator._format_srt_time(start)} --> "
                f"{CaptionGenerator._format_srt_time(end)}"
            )
            srt_lines.append(text)
            srt_lines.append("")  # blank separator

        return "\n".join(srt_lines)

    @staticmethod
    def _format_srt_time(seconds: float) -> str:
        """Formats seconds as SRT timestamp: HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def build_ass(
        transcript_words: List[Dict[str, Any]],
        video_width: int = 1920,
        video_height: int = 1080,
        font_name: str = "Arial",
        font_size: int = 48,
        max_words_per_cue: int = 8,
        max_cue_duration: float = 4.0,
    ) -> str:
        """
        Generates ASS (Advanced SubStation Alpha) subtitle string for
        burn-in rendering via FFmpeg's ass filter.

        Uses a clean, readable style with semi-transparent background.
        """
        if not transcript_words:
            return ""

        # Build cues (same logic as SRT)
        cues: List[Tuple[float, float, str]] = []
        current_words: List[str] = []
        cue_start: Optional[float] = None

        for word_info in transcript_words:
            word = word_info.get("word", "")
            start = word_info.get("start", 0.0)
            end = word_info.get("end", start + 0.1)

            if not word.strip():
                continue

            if cue_start is None:
                cue_start = start

            current_words.append(word)

            if (
                len(current_words) >= max_words_per_cue
                or (end - cue_start) >= max_cue_duration
            ):
                cues.append((cue_start, end, " ".join(current_words)))
                current_words = []
                cue_start = None

        if current_words and cue_start is not None:
            last_end = transcript_words[-1].get("end", cue_start + 0.5)
            cues.append((cue_start, last_end, " ".join(current_words)))

        # ASS header
        header = f"""[Script Info]
Title: IncuBrix B-roll Captions
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,3,2,0,2,20,20,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        # ASS dialogue lines
        events: List[str] = []
        for start, end, text in cues:
            start_str = CaptionGenerator._format_ass_time(start)
            end_str = CaptionGenerator._format_ass_time(end)
            # Escape ASS special characters
            clean_text = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
            events.append(
                f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{clean_text}"
            )

        return header + "\n".join(events) + "\n"

    @staticmethod
    def _format_ass_time(seconds: float) -> str:
        """Formats seconds as ASS timestamp: H:MM:SS.cc"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"


class VideoRenderer:
    """
    Concatenates normalised scene segments into a final output video,
    overlays narration audio, and optionally burns in captions.

    Produces one video_<ratio>.mp4 per requested aspect ratio.
    """

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or os.path.join(settings.CACHE_DIR, "output")
        self.normalizer = video_normalizer
        self.caption_gen = CaptionGenerator()

    # ----------------------------------------------------------------
    # Core render pipeline
    # ----------------------------------------------------------------

    def render_final_video(
        self,
        job_id: str,
        ratio: str,
        normalized_clips: List[NormalizedClip],
        narration_audio_path: str,
        transcript_words: List[Dict[str, Any]],
        burn_in_captions: bool = True,
        srt_captions: bool = True,
    ) -> Dict[str, Any]:
        """
        Renders the final video for one aspect ratio:

        1. Writes a concat demuxer file listing all normalised segments
        2. Concatenates segments into a single video stream
        3. Overlays narration audio
        4. Optionally burns in ASS captions
        5. Generates SRT file

        Returns:
            {
                "video_path": str,
                "srt_path": Optional[str],
                "ass_path": Optional[str],
                "duration": float,
                "ratio": str,
                "warnings": List[str],
            }
        """
        warnings: List[str] = []
        ratio_label = ratio.replace(":", "x")

        # Create output directory
        job_output_dir = os.path.join(self.output_dir, job_id)
        os.makedirs(job_output_dir, exist_ok=True)

        # Sort clips by scene index
        sorted_clips = sorted(normalized_clips, key=lambda c: c.scene_index)

        if not sorted_clips:
            raise FFmpegError("No normalised clips to render")

        # ---- Step 1: Write concat file ----
        concat_file_path = os.path.join(job_output_dir, f"concat_{ratio_label}.txt")
        self._write_concat_file(concat_file_path, sorted_clips)

        # ---- Step 2: Generate captions ----
        srt_path: Optional[str] = None
        ass_path: Optional[str] = None
        target_w, target_h = RESOLUTION_MAP.get(ratio, (1920, 1080))

        if srt_captions and transcript_words:
            srt_content = self.caption_gen.build_srt(transcript_words)
            srt_path = os.path.join(job_output_dir, f"captions_{ratio_label}.srt")
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)

        if burn_in_captions and transcript_words:
            ass_content = self.caption_gen.build_ass(
                transcript_words,
                video_width=target_w,
                video_height=target_h,
            )
            ass_path = os.path.join(job_output_dir, f"captions_{ratio_label}.ass")
            with open(ass_path, "w", encoding="utf-8") as f:
                f.write(ass_content)

        # ---- Step 3: Concat + audio overlay + burn-in ----
        output_video_path = os.path.join(
            job_output_dir, f"video_{ratio_label}.mp4"
        )

        cmd = self._build_render_command(
            concat_file=concat_file_path,
            narration_audio=narration_audio_path,
            ass_path=ass_path if burn_in_captions else None,
            output_path=output_video_path,
        )

        self.normalizer.run_ffmpeg(cmd, timeout=600)

        # Calculate total duration from segments
        total_duration = sum(c.duration for c in sorted_clips)

        logger.info(
            "Rendered video_%s.mp4 for job %s (%.1fs, %d scenes)",
            ratio_label, job_id, total_duration, len(sorted_clips),
        )

        return {
            "video_path": output_video_path,
            "srt_path": srt_path,
            "ass_path": ass_path,
            "duration": total_duration,
            "ratio": ratio,
            "warnings": warnings,
        }

    # ----------------------------------------------------------------
    # Render all ratios
    # ----------------------------------------------------------------

    def render_all_ratios(
        self,
        job_id: str,
        normalized_clips_by_ratio: Dict[str, List[NormalizedClip]],
        narration_audio_path: str,
        transcript_words: List[Dict[str, Any]],
        burn_in_captions: bool = True,
        srt_captions: bool = True,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Renders final video for every requested aspect ratio.

        Returns:
            Dict mapping ratio → render result dict
        """
        results: Dict[str, Dict[str, Any]] = {}

        for ratio, clips in normalized_clips_by_ratio.items():
            try:
                result = self.render_final_video(
                    job_id=job_id,
                    ratio=ratio,
                    normalized_clips=clips,
                    narration_audio_path=narration_audio_path,
                    transcript_words=transcript_words,
                    burn_in_captions=burn_in_captions,
                    srt_captions=srt_captions,
                )
                results[ratio] = result
            except FFmpegError as e:
                logger.error(
                    "Render failed for ratio %s in job %s: %s",
                    ratio, job_id, e,
                )
                results[ratio] = {
                    "video_path": None,
                    "error": str(e),
                    "ratio": ratio,
                    "warnings": [f"Render failed: {e}"],
                }

        return results

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def _write_concat_file(
        self, path: str, clips: List[NormalizedClip]
    ) -> None:
        """Writes an FFmpeg concat demuxer file."""
        with open(path, "w", encoding="utf-8") as f:
            for clip in clips:
                # Escape single quotes in path for FFmpeg concat format
                safe_path = clip.output_path.replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")
                f.write(f"duration {clip.duration:.3f}\n")

    def _build_render_command(
        self,
        concat_file: str,
        narration_audio: str,
        ass_path: Optional[str],
        output_path: str,
    ) -> List[str]:
        """
        Builds the FFmpeg command for final concat + audio + burn-in render.

        Pipeline:
          concat demuxer → [ass filter] → H.264 video
          narration audio → AAC audio
          Muxed into a single MP4 with faststart.
        """
        cmd = [
            self.normalizer.ffmpeg_binary,
            "-y",
            # Input 1: concatenated video segments
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            # Input 2: narration audio
            "-i", narration_audio,
        ]

        # Video filter: burn-in ASS subtitles if provided
        if ass_path and os.path.isfile(ass_path):
            # Use the ass filter for styled subtitle rendering
            # Escape backslashes and colons in Windows paths for FFmpeg
            safe_ass = ass_path.replace("\\", "/").replace(":", "\\:")
            cmd.extend(["-vf", f"ass='{safe_ass}'"])

        cmd.extend([
            # Video codec — standard browser playable H.264 High/Main
            "-c:v", TARGET_CODEC,
            "-profile:v", "high",
            "-level", "4.1",
            "-preset", "medium",
            "-crf", "20",
            "-pix_fmt", TARGET_PIX_FMT,
            # Audio codec — encode narration as AAC
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            # Use shortest input to determine output length
            "-shortest",
            # Enable fast seeking for web playback
            "-movflags", "+faststart",
            output_path,
        ])

        return cmd


# Module-level singleton
caption_generator = CaptionGenerator()
video_renderer = VideoRenderer()
