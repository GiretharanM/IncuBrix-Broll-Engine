"""
Tests for Stage 7: FFmpeg Video Normalisation
-----------------------------------------------
Tests smart crop calculations, filter chain construction,
segment hashing, fallback card generation, and batch normalisation.
FFmpeg subprocess calls are mocked (no FFmpeg required on host).
"""

import json
import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from app.pipeline.stage7_normalize import (
    VideoNormalizer,
    NormalizedClip,
    FFmpegError,
    RESOLUTION_MAP,
    TARGET_FPS,
    TARGET_PIX_FMT,
)


class TestSmartCrop:
    """Tests for saliency-aware smart crop calculations."""

    def setup_method(self):
        self.normalizer = VideoNormalizer(cache_dir=tempfile.mkdtemp())

    def test_landscape_to_portrait_rule_of_thirds(self):
        """9:16 from 16:9 should use rule-of-thirds (0.33), NOT blind centre."""
        crop = self.normalizer.compute_smart_crop(
            src_w=1920, src_h=1080, target_w=1080, target_h=1920
        )
        # Crop width should be narrower than source
        assert crop["crop_w"] < 1920
        # Method should NOT be blind centre — should be rule_of_thirds
        assert crop["method"] == "rule_of_thirds"
        # Crop X should be biased left (not dead centre at 960-crop_w//2)
        blind_centre_x = (1920 - crop["crop_w"]) // 2
        assert crop["crop_x"] < blind_centre_x, (
            f"Smart crop should bias left of centre. Got crop_x={crop['crop_x']}, "
            f"blind centre would be {blind_centre_x}"
        )

    def test_landscape_to_portrait_with_saliency(self):
        """When saliency_x is provided, crop should centre on that point."""
        crop = self.normalizer.compute_smart_crop(
            src_w=1920, src_h=1080, target_w=1080, target_h=1920,
            saliency_x=0.75,  # Subject on right side
        )
        assert crop["method"] == "saliency"
        # Crop should be centred around x=0.75*1920=1440
        expected_centre = int(0.75 * 1920)
        actual_centre = crop["crop_x"] + crop["crop_w"] // 2
        assert abs(actual_centre - expected_centre) < crop["crop_w"] // 2

    def test_same_aspect_ratio_scale_only(self):
        """Same aspect ratio should just scale, not crop."""
        crop = self.normalizer.compute_smart_crop(
            src_w=1920, src_h=1080, target_w=1920, target_h=1080
        )
        assert crop["method"] == "scale_only"
        assert crop["crop_x"] == 0
        assert crop["crop_y"] == 0

    def test_portrait_to_landscape_vertical_crop(self):
        """16:9 from 9:16 should crop height, keeping upper portion."""
        crop = self.normalizer.compute_smart_crop(
            src_w=1080, src_h=1920, target_w=1920, target_h=1080
        )
        assert crop["crop_h"] < 1920  # Height should be reduced
        assert crop["method"] == "rule_of_thirds_vertical"

    def test_square_to_landscape(self):
        """16:9 from 1:1 should crop height."""
        crop = self.normalizer.compute_smart_crop(
            src_w=1080, src_h=1080, target_w=1920, target_h=1080
        )
        assert crop["crop_h"] <= 1080
        assert crop["crop_w"] == 1080

    def test_crop_stays_within_bounds(self):
        """Crop coordinates must never exceed source frame."""
        # Edge case: saliency at far right
        crop = self.normalizer.compute_smart_crop(
            src_w=1920, src_h=1080, target_w=1080, target_h=1920,
            saliency_x=0.99,
        )
        assert crop["crop_x"] >= 0
        assert crop["crop_x"] + crop["crop_w"] <= 1920
        assert crop["crop_y"] >= 0
        assert crop["crop_y"] + crop["crop_h"] <= 1080

        # Edge case: saliency at far left
        crop2 = self.normalizer.compute_smart_crop(
            src_w=1920, src_h=1080, target_w=1080, target_h=1920,
            saliency_x=0.01,
        )
        assert crop2["crop_x"] >= 0
        assert crop2["crop_x"] + crop2["crop_w"] <= 1920


class TestFilterChain:
    """Tests for FFmpeg filter chain construction."""

    def setup_method(self):
        self.normalizer = VideoNormalizer(cache_dir=tempfile.mkdtemp())

    def test_filter_chain_for_portrait_includes_crop(self):
        """16:9→9:16 conversion should include a crop filter."""
        src_meta = {"width": 1920, "height": 1080, "fps": 24}
        filters = self.normalizer.build_filter_chain(
            src_meta, 1080, 1920, 3.0
        )
        assert "crop=" in filters
        assert "scale=1080:1920" in filters
        assert "fps=30" in filters
        assert f"format={TARGET_PIX_FMT}" in filters

    def test_filter_chain_same_ratio_no_crop(self):
        """Same aspect ratio should NOT include crop filter."""
        src_meta = {"width": 1920, "height": 1080, "fps": 30}
        filters = self.normalizer.build_filter_chain(
            src_meta, 1920, 1080, 3.0
        )
        assert "crop=" not in filters
        assert "scale=1920:1080" in filters

    def test_filter_chain_includes_colour_normalisation(self):
        """Colour normalisation should be applied when enabled."""
        src_meta = {"width": 1920, "height": 1080, "fps": 30}
        filters = self.normalizer.build_filter_chain(
            src_meta, 1920, 1080, 3.0, colour_normalize=True
        )
        assert "eq=" in filters

    def test_filter_chain_no_colour_when_disabled(self):
        """Colour normalisation should be skipped when disabled."""
        src_meta = {"width": 1920, "height": 1080, "fps": 30}
        filters = self.normalizer.build_filter_chain(
            src_meta, 1920, 1080, 3.0, colour_normalize=False
        )
        assert "eq=" not in filters


class TestSegmentHash:
    """Tests for deterministic segment hashing."""

    def test_same_inputs_same_hash(self):
        """Identical inputs must produce the same hash."""
        h1 = VideoNormalizer.compute_segment_hash("clip1", "16:9", 0.0, 3.0, "scale=1920:1080")
        h2 = VideoNormalizer.compute_segment_hash("clip1", "16:9", 0.0, 3.0, "scale=1920:1080")
        assert h1 == h2

    def test_different_clip_different_hash(self):
        """Different clip IDs must produce different hashes."""
        h1 = VideoNormalizer.compute_segment_hash("clip1", "16:9", 0.0, 3.0, "scale=1920:1080")
        h2 = VideoNormalizer.compute_segment_hash("clip2", "16:9", 0.0, 3.0, "scale=1920:1080")
        assert h1 != h2

    def test_different_ratio_different_hash(self):
        """Different ratios must produce different hashes."""
        h1 = VideoNormalizer.compute_segment_hash("clip1", "16:9", 0.0, 3.0, "filters")
        h2 = VideoNormalizer.compute_segment_hash("clip1", "9:16", 0.0, 3.0, "filters")
        assert h1 != h2

    def test_hash_length(self):
        """Hash should be 16 chars (truncated SHA-256)."""
        h = VideoNormalizer.compute_segment_hash("clip1", "16:9", 0.0, 3.0, "filters")
        assert len(h) == 16


class TestNormalizeClipMocked:
    """Tests for clip normalisation with mocked FFmpeg."""

    def setup_method(self):
        self.normalizer = VideoNormalizer(cache_dir=tempfile.mkdtemp())

    @patch.object(VideoNormalizer, 'run_ffmpeg')
    @patch.object(VideoNormalizer, 'probe_clip')
    @patch.object(VideoNormalizer, 'detect_black_frozen_frames')
    def test_normalize_clip_calls_ffmpeg(self, mock_detect, mock_probe, mock_run):
        """Normalisation should probe, build command, and run FFmpeg."""
        mock_probe.return_value = {
            "width": 1920, "height": 1080, "fps": 24,
            "duration": 10.0, "codec": "h264", "pix_fmt": "yuv420p",
        }
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_detect.return_value = []

        # Create a fake clip file
        clip_path = os.path.join(self.normalizer.cache_dir, "test_clip.mp4")
        with open(clip_path, "w") as f:
            f.write("fake")

        result = self.normalizer.normalize_clip(
            clip_path=clip_path,
            scene_id="test_s01",
            scene_index=0,
            clip_id="clip_001",
            ratio="16:9",
            scene_duration=3.5,
        )

        assert isinstance(result, NormalizedClip)
        assert result.scene_id == "test_s01"
        assert result.ratio == "16:9"
        assert result.width == 1920
        assert result.height == 1080
        assert result.duration == 3.5
        assert len(result.segment_hash) == 16
        mock_probe.assert_called_once()
        # FFmpeg should be called for transcode (run_ffmpeg called once for transcode)
        assert mock_run.called


class TestResolutionMap:
    """Tests for resolution target mapping."""

    def test_all_ratios_defined(self):
        """All supported ratios should have resolution targets."""
        assert "16:9" in RESOLUTION_MAP
        assert "9:16" in RESOLUTION_MAP
        assert "1:1" in RESOLUTION_MAP

    def test_resolution_values(self):
        assert RESOLUTION_MAP["16:9"] == (1920, 1080)
        assert RESOLUTION_MAP["9:16"] == (1080, 1920)
        assert RESOLUTION_MAP["1:1"] == (1080, 1080)
