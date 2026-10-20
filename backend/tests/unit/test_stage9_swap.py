"""
Tests for Stage 9: Swap-a-Clip & Segment Cache
-------------------------------------------------
Tests segment caching, cache invalidation, and the
clip swap workflow with mocked FFmpeg.
"""

import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from app.pipeline.stage9_swap import SegmentCache, ClipSwapper
from app.pipeline.stage7_normalize import NormalizedClip, VideoNormalizer
from app.pipeline.stage8_render import VideoRenderer


class TestSegmentCache:
    """Tests for per-scene segment caching."""

    def setup_method(self):
        self.cache_dir = tempfile.mkdtemp()
        self.cache = SegmentCache(cache_dir=self.cache_dir)

    def test_register_and_retrieve_segment(self):
        """Registered segments should be retrievable by hash."""
        # Create a fake segment file
        ratio_dir = os.path.join(self.cache_dir, "16x9")
        os.makedirs(ratio_dir, exist_ok=True)
        fake_file = os.path.join(ratio_dir, "abc123_s01.mp4")
        with open(fake_file, "w") as f:
            f.write("fake video data")

        # Register it
        self.cache.register_segment("abc123", "16:9", fake_file)

        # Retrieve it
        cached = self.cache.get_cached_path("abc123", "16:9")
        assert cached is not None
        assert os.path.isfile(cached)

    def test_missing_segment_returns_none(self):
        """Non-existent segments should return None."""
        result = self.cache.get_cached_path("nonexistent", "16:9")
        assert result is None

    def test_invalidate_removes_file(self):
        """Invalidating a segment should remove it from cache."""
        ratio_dir = os.path.join(self.cache_dir, "16x9")
        os.makedirs(ratio_dir, exist_ok=True)
        fake_file = os.path.join(ratio_dir, "del123_s01.mp4")
        with open(fake_file, "w") as f:
            f.write("to be deleted")

        removed = self.cache.invalidate("del123", "16:9")
        assert removed is True
        assert not os.path.isfile(fake_file)

    def test_invalidate_missing_returns_false(self):
        """Invalidating a non-existent segment should return False."""
        removed = self.cache.invalidate("nope", "16:9")
        assert removed is False

    def test_different_ratio_dirs(self):
        """Different ratios should use different cache directories."""
        for ratio in ["16:9", "9:16", "1:1"]:
            ratio_dir = os.path.join(self.cache_dir, ratio.replace(":", "x"))
            os.makedirs(ratio_dir, exist_ok=True)
            fake = os.path.join(ratio_dir, f"hash_{ratio.replace(':', 'x')}.mp4")
            with open(fake, "w") as f:
                f.write("data")

        # Each ratio should independently resolve
        assert self.cache.get_cached_path("hash_16x9", "16:9") is not None
        assert self.cache.get_cached_path("hash_9x16", "9:16") is not None
        assert self.cache.get_cached_path("hash_1x1", "1:1") is not None
        # Cross-ratio should NOT match
        assert self.cache.get_cached_path("hash_16x9", "9:16") is None


class TestClipSwapper:
    """Tests for the clip swap workflow."""

    @patch.object(VideoRenderer, 'render_all_ratios')
    @patch.object(VideoNormalizer, 'normalize_clip')
    def test_swap_replaces_correct_scene(self, mock_normalize, mock_render):
        """Swapping should replace only the targeted scene's segment."""
        # Setup mock normalised clip
        new_clip = NormalizedClip(
            scene_id="job1_s01", scene_index=1, ratio="16:9",
            output_path="/tmp/new_s01.mp4", duration=3.0,
            segment_hash="newhash", width=1920, height=1080,
        )
        mock_normalize.return_value = new_clip
        mock_render.return_value = {
            "16:9": {
                "video_path": "/tmp/video_16x9.mp4",
                "srt_path": None,
                "duration": 9.0,
                "ratio": "16:9",
                "warnings": [],
            }
        }

        # Existing segments
        existing_segments = {
            "16:9": [
                NormalizedClip(
                    scene_id="job1_s00", scene_index=0, ratio="16:9",
                    output_path="/tmp/old_s00.mp4", duration=3.0,
                    segment_hash="hash00", width=1920, height=1080,
                ),
                NormalizedClip(
                    scene_id="job1_s01", scene_index=1, ratio="16:9",
                    output_path="/tmp/old_s01.mp4", duration=3.0,
                    segment_hash="hash01", width=1920, height=1080,
                ),
                NormalizedClip(
                    scene_id="job1_s02", scene_index=2, ratio="16:9",
                    output_path="/tmp/old_s02.mp4", duration=3.0,
                    segment_hash="hash02", width=1920, height=1080,
                ),
            ]
        }

        swapper = ClipSwapper()
        swapper.cache = SegmentCache(cache_dir=tempfile.mkdtemp())

        result = swapper.swap_clip(
            job_id="job1",
            scene_id="job1_s01",
            scene_index=1,
            new_clip_path="/tmp/new_raw.mp4",
            new_clip_id="new_clip_id",
            scene_duration=3.0,
            start_time=3.0,
            ratios=["16:9"],
            all_segments=existing_segments,
            narration_audio_path="/tmp/narration.wav",
            transcript_words=[],
        )

        assert result["swapped_scene_id"] == "job1_s01"
        assert result["new_clip_id"] == "new_clip_id"
        assert "time_saved_seconds" in result
        assert "partial_render_seconds" in result
        assert result["partial_render_seconds"] >= 0

        # Verify the second segment was replaced
        assert existing_segments["16:9"][1].segment_hash == "newhash"
        # Other segments should be unchanged
        assert existing_segments["16:9"][0].segment_hash == "hash00"
        assert existing_segments["16:9"][2].segment_hash == "hash02"

    @patch.object(VideoRenderer, 'render_all_ratios')
    @patch.object(VideoNormalizer, 'normalize_clip')
    def test_swap_reports_time_saved(self, mock_normalize, mock_render):
        """Swap should report estimated time savings."""
        mock_normalize.return_value = NormalizedClip(
            scene_id="s01", scene_index=0, ratio="16:9",
            output_path="/tmp/new.mp4", duration=3.0,
            segment_hash="new", width=1920, height=1080,
        )
        mock_render.return_value = {"16:9": {"video_path": "/tmp/v.mp4", "warnings": []}}

        swapper = ClipSwapper()
        swapper.cache = SegmentCache(cache_dir=tempfile.mkdtemp())

        result = swapper.swap_clip(
            job_id="j1",
            scene_id="s01",
            scene_index=0,
            new_clip_path="/tmp/clip.mp4",
            new_clip_id="c1",
            scene_duration=3.0,
            start_time=0.0,
            ratios=["16:9"],
            all_segments={
                "16:9": [
                    NormalizedClip(
                        scene_id="s01", scene_index=0, ratio="16:9",
                        output_path="/tmp/old.mp4", duration=3.0,
                        segment_hash="old", width=1920, height=1080,
                    ),
                ]
            },
            narration_audio_path="/tmp/a.wav",
            transcript_words=[],
        )

        assert result["full_render_estimate_seconds"] > 0
        assert result["partial_render_seconds"] >= 0
