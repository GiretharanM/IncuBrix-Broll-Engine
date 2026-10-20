"""
Stage 9: Swap-a-Clip & Partial Re-render
------------------------------------------
Supports replacing a single scene's clip and re-rendering ONLY
the affected segment, then re-concatenating with unchanged segments.

Per-scene segments are cached by SHA-256 hash of:
    (clip_id, ratio, start_time, duration, filters)

This avoids full re-rendering when only one clip changes.
Reports time saved vs a full render.
"""

import hashlib
import logging
import os
import time
from typing import Any, Dict, List, Optional

from app.config import settings
from app.pipeline.stage7_normalize import (
    NormalizedClip,
    VideoNormalizer,
    video_normalizer,
)
from app.pipeline.stage8_render import VideoRenderer, video_renderer

logger = logging.getLogger(__name__)


class SegmentCache:
    """
    Manages cached per-scene normalised segments. Each segment is
    identified by a deterministic hash of its rendering parameters.
    """

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or os.path.join(settings.CACHE_DIR, "segments")
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_cached_path(self, segment_hash: str, ratio: str) -> Optional[str]:
        """Returns the cached file path if it exists, else None."""
        ratio_dir = ratio.replace(":", "x")
        pattern_dir = os.path.join(self.cache_dir, ratio_dir)
        if not os.path.isdir(pattern_dir):
            return None

        # Look for files starting with the segment hash
        for fname in os.listdir(pattern_dir):
            if fname.startswith(segment_hash):
                full_path = os.path.join(pattern_dir, fname)
                if os.path.isfile(full_path):
                    return full_path
        return None

    def register_segment(
        self, segment_hash: str, ratio: str, file_path: str
    ) -> str:
        """
        Copies/links a normalised segment file into the cache.
        Returns the cached path.
        """
        ratio_dir = ratio.replace(":", "x")
        cache_subdir = os.path.join(self.cache_dir, ratio_dir)
        os.makedirs(cache_subdir, exist_ok=True)

        dest = os.path.join(cache_subdir, os.path.basename(file_path))
        if not os.path.isfile(dest) and os.path.isfile(file_path):
            # Use symlink if possible, else copy
            try:
                os.symlink(file_path, dest)
            except (OSError, NotImplementedError):
                import shutil
                shutil.copy2(file_path, dest)

        return dest

    def invalidate(self, segment_hash: str, ratio: str) -> bool:
        """Removes a cached segment. Returns True if something was removed."""
        cached = self.get_cached_path(segment_hash, ratio)
        if cached and os.path.isfile(cached):
            os.remove(cached)
            return True
        return False


class ClipSwapper:
    """
    Handles the swap-a-clip workflow:

    1. Accept a new clip for a specific scene
    2. Re-normalise ONLY that scene's clip (for each ratio)
    3. Update the cached segment
    4. Re-concat all segments (using cached segments for unchanged scenes)
    5. Report time saved vs full render

    This is triggered by PATCH /api/v1/jobs/{job_id}/scenes/{scene_id}/clip
    """

    def __init__(self):
        self.normalizer = video_normalizer
        self.renderer = video_renderer
        self.cache = SegmentCache()

    def swap_clip(
        self,
        job_id: str,
        scene_id: str,
        scene_index: int,
        new_clip_path: str,
        new_clip_id: str,
        scene_duration: float,
        start_time: float,
        ratios: List[str],
        all_segments: Dict[str, List[NormalizedClip]],
        narration_audio_path: str,
        transcript_words: List[Dict[str, Any]],
        burn_in_captions: bool = True,
        srt_captions: bool = True,
    ) -> Dict[str, Any]:
        """
        Swaps a single scene's clip and performs a partial re-render.

        Args:
            job_id: Job identifier
            scene_id: Scene to swap
            scene_index: Scene position
            new_clip_path: Local path to the new clip file
            new_clip_id: Identifier for the new clip
            scene_duration: Duration of the scene
            start_time: Scene start time in timeline
            ratios: All target aspect ratios
            all_segments: Current segments per ratio (Dict[ratio, List[NormalizedClip]])
            narration_audio_path: Path to narration audio
            transcript_words: Word-level timestamps for captions
            burn_in_captions: Whether to burn in captions
            srt_captions: Whether to generate SRT

        Returns:
            {
                "swapped_scene_id": str,
                "new_clip_id": str,
                "renders": Dict[str, render_result],
                "time_saved_seconds": float,
                "full_render_estimate_seconds": float,
                "partial_render_seconds": float,
            }
        """
        swap_start = time.time()

        # Estimate what a full render would cost (rough: 2s per scene per ratio)
        total_segments = sum(len(segs) for segs in all_segments.values())
        full_render_estimate = total_segments * 2.0

        # Re-normalise the swapped scene for each ratio
        for ratio in ratios:
            new_clip = self.normalizer.normalize_clip(
                clip_path=new_clip_path,
                scene_id=scene_id,
                scene_index=scene_index,
                clip_id=new_clip_id,
                ratio=ratio,
                scene_duration=scene_duration,
                start_time=start_time,
            )

            # Replace the old segment in the list
            if ratio in all_segments:
                updated = False
                for i, seg in enumerate(all_segments[ratio]):
                    if seg.scene_id == scene_id:
                        # Invalidate old cache entry
                        self.cache.invalidate(seg.segment_hash, ratio)
                        # Replace with new segment
                        all_segments[ratio][i] = new_clip
                        # Cache the new segment
                        self.cache.register_segment(
                            new_clip.segment_hash, ratio, new_clip.output_path
                        )
                        updated = True
                        break
                if not updated:
                    logger.warning(
                        "Scene %s not found in ratio %s segments during swap",
                        scene_id, ratio,
                    )

        # Re-concat (uses all segments — cached for unchanged, fresh for swapped)
        renders = self.renderer.render_all_ratios(
            job_id=job_id,
            normalized_clips_by_ratio=all_segments,
            narration_audio_path=narration_audio_path,
            transcript_words=transcript_words,
            burn_in_captions=burn_in_captions,
            srt_captions=srt_captions,
        )

        partial_render_time = time.time() - swap_start
        time_saved = max(0.0, full_render_estimate - partial_render_time)

        logger.info(
            "Swap-a-clip for scene %s in job %s: partial render %.1fs "
            "(est. full: %.1fs, saved: %.1fs)",
            scene_id, job_id, partial_render_time,
            full_render_estimate, time_saved,
        )

        return {
            "swapped_scene_id": scene_id,
            "new_clip_id": new_clip_id,
            "renders": renders,
            "time_saved_seconds": round(time_saved, 2),
            "full_render_estimate_seconds": round(full_render_estimate, 2),
            "partial_render_seconds": round(partial_render_time, 2),
        }


# Module-level singletons
segment_cache = SegmentCache()
clip_swapper = ClipSwapper()
