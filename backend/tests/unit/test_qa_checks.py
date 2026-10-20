"""
Tests for Automated Output QA Checks
---------------------------------------
Tests all QA verifications: aspect ratio, fps, codecs,
black/frozen frames, audio drift, repeated clips, narration coverage.
Uses mocked ffprobe results (no FFmpeg needed on host).
"""

import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from app.pipeline.qa_checks import (
    OutputQAChecker,
    QAReport,
    QAResult,
)
from app.pipeline.stage7_normalize import VideoNormalizer


class TestQAResult:
    """Tests for QAResult data structure."""

    def test_passed_result(self):
        r = QAResult(check_name="test", passed=True, message="")
        assert r.passed
        assert r.severity == "error"

    def test_failed_result(self):
        r = QAResult(check_name="test", passed=False, severity="warning", message="oops")
        assert not r.passed
        assert r.message == "oops"


class TestQAReport:
    """Tests for QAReport aggregation."""

    def test_report_passes_when_all_checks_pass(self):
        report = QAReport(job_id="j1", ratio="16:9", video_path="/tmp/v.mp4")
        report.add_check(QAResult(check_name="c1", passed=True))
        report.add_check(QAResult(check_name="c2", passed=True))
        assert report.passed

    def test_report_fails_on_error_severity(self):
        report = QAReport(job_id="j1", ratio="16:9", video_path="/tmp/v.mp4")
        report.add_check(QAResult(check_name="c1", passed=True))
        report.add_check(QAResult(
            check_name="c2", passed=False, severity="error", message="bad"
        ))
        assert not report.passed
        assert len(report.errors) == 1

    def test_report_still_passes_on_warning_severity(self):
        report = QAReport(job_id="j1", ratio="16:9", video_path="/tmp/v.mp4")
        report.add_check(QAResult(
            check_name="c1", passed=False, severity="warning", message="meh"
        ))
        assert report.passed  # warnings don't fail the report
        assert len(report.warnings) == 1

    def test_report_summary(self):
        report = QAReport(job_id="j1", ratio="16:9", video_path="/tmp/v.mp4")
        report.add_check(QAResult(check_name="c1", passed=True))
        report.add_check(QAResult(
            check_name="c2", passed=False, severity="error", message="err"
        ))

        summary = report.summary()
        assert summary["total_checks"] == 2
        assert summary["passed_checks"] == 1
        assert summary["failed_checks"] == 1


class TestNoRepeatedClips:
    """Tests for the repeated-clip QA check."""

    def setup_method(self):
        self.checker = OutputQAChecker()

    def test_unique_clips_pass(self):
        """All unique clip IDs should pass."""
        reports = {"16:9": QAReport(job_id="j1", ratio="16:9", video_path="v.mp4")}
        scenes = [
            {"clip_id": "clip_a"},
            {"clip_id": "clip_b"},
            {"clip_id": "clip_c"},
        ]
        self.checker._check_no_repeated_clips(reports, scenes)
        check = [c for c in reports["16:9"].checks if c.check_name == "no_repeated_clips"][0]
        assert check.passed

    def test_duplicate_clips_fail(self):
        """Duplicate clip IDs should fail the check."""
        reports = {"16:9": QAReport(job_id="j1", ratio="16:9", video_path="v.mp4")}
        scenes = [
            {"clip_id": "clip_a"},
            {"clip_id": "clip_b"},
            {"clip_id": "clip_a"},  # duplicate!
        ]
        self.checker._check_no_repeated_clips(reports, scenes)
        check = [c for c in reports["16:9"].checks if c.check_name == "no_repeated_clips"][0]
        assert not check.passed
        assert "clip_a" in check.message


class TestNarrationCoverage:
    """Tests for narration coverage QA check."""

    def setup_method(self):
        self.checker = OutputQAChecker()

    def test_full_coverage_passes(self):
        """Contiguous scenes from 0 to duration should pass."""
        reports = {"16:9": QAReport(job_id="j1", ratio="16:9", video_path="v.mp4")}
        scenes = [
            {"start_time": 0.0, "end_time": 3.0},
            {"start_time": 3.0, "end_time": 6.0},
            {"start_time": 6.0, "end_time": 10.0},
        ]
        self.checker._check_narration_coverage(reports, scenes, 10.0)
        check = [c for c in reports["16:9"].checks if c.check_name == "narration_coverage"][0]
        assert check.passed

    def test_gap_in_coverage_fails(self):
        """A gap between scenes should fail the coverage check."""
        reports = {"16:9": QAReport(job_id="j1", ratio="16:9", video_path="v.mp4")}
        scenes = [
            {"start_time": 0.0, "end_time": 3.0},
            # GAP from 3.0 to 5.0
            {"start_time": 5.0, "end_time": 10.0},
        ]
        self.checker._check_narration_coverage(reports, scenes, 10.0)
        check = [c for c in reports["16:9"].checks if c.check_name == "narration_coverage"][0]
        assert not check.passed
        assert "gap" in check.message.lower()

    def test_empty_scenes_fails(self):
        """No scenes at all should fail."""
        reports = {"16:9": QAReport(job_id="j1", ratio="16:9", video_path="v.mp4")}
        self.checker._check_narration_coverage(reports, [], 10.0)
        check = [c for c in reports["16:9"].checks if c.check_name == "narration_coverage"][0]
        assert not check.passed

    def test_non_zero_start_fails(self):
        """Scenes not starting at 0 should fail."""
        reports = {"16:9": QAReport(job_id="j1", ratio="16:9", video_path="v.mp4")}
        scenes = [
            {"start_time": 1.0, "end_time": 5.0},  # starts at 1.0, not 0
            {"start_time": 5.0, "end_time": 10.0},
        ]
        self.checker._check_narration_coverage(reports, scenes, 10.0)
        check = [c for c in reports["16:9"].checks if c.check_name == "narration_coverage"][0]
        assert not check.passed


class TestAspectRatioCheck:
    """Tests for aspect ratio verification with mocked ffprobe."""

    def setup_method(self):
        self.checker = OutputQAChecker()

    @patch.object(VideoNormalizer, 'probe_clip')
    def test_correct_ratio_passes(self, mock_probe):
        """Correct resolution should pass."""
        mock_probe.return_value = {"width": 1920, "height": 1080, "fps": 30}
        report = QAReport(job_id="j1", ratio="16:9", video_path="v.mp4")
        self.checker._check_aspect_ratio(report, "v.mp4", "16:9")
        check = [c for c in report.checks if c.check_name == "aspect_ratio"][0]
        assert check.passed

    @patch.object(VideoNormalizer, 'probe_clip')
    def test_wrong_ratio_fails(self, mock_probe):
        """Wrong resolution should fail."""
        mock_probe.return_value = {"width": 1280, "height": 720, "fps": 30}
        report = QAReport(job_id="j1", ratio="16:9", video_path="v.mp4")
        self.checker._check_aspect_ratio(report, "v.mp4", "16:9")
        check = [c for c in report.checks if c.check_name == "aspect_ratio"][0]
        assert not check.passed

    @patch.object(VideoNormalizer, 'probe_clip')
    def test_portrait_ratio_check(self, mock_probe):
        """9:16 should expect 1080x1920."""
        mock_probe.return_value = {"width": 1080, "height": 1920, "fps": 30}
        report = QAReport(job_id="j1", ratio="9:16", video_path="v.mp4")
        self.checker._check_aspect_ratio(report, "v.mp4", "9:16")
        check = [c for c in report.checks if c.check_name == "aspect_ratio"][0]
        assert check.passed


class TestFPSCheck:
    """Tests for frame rate verification."""

    def setup_method(self):
        self.checker = OutputQAChecker()

    @patch.object(VideoNormalizer, 'probe_clip')
    def test_30fps_passes(self, mock_probe):
        mock_probe.return_value = {"width": 1920, "height": 1080, "fps": 30}
        report = QAReport(job_id="j1", ratio="16:9", video_path="v.mp4")
        self.checker._check_fps(report, "v.mp4")
        check = [c for c in report.checks if c.check_name == "fps"][0]
        assert check.passed

    @patch.object(VideoNormalizer, 'probe_clip')
    def test_24fps_fails(self, mock_probe):
        mock_probe.return_value = {"width": 1920, "height": 1080, "fps": 24}
        report = QAReport(job_id="j1", ratio="16:9", video_path="v.mp4")
        self.checker._check_fps(report, "v.mp4")
        check = [c for c in report.checks if c.check_name == "fps"][0]
        assert not check.passed


class TestCodecCheck:
    """Tests for codec verification."""

    def setup_method(self):
        self.checker = OutputQAChecker()

    @patch.object(VideoNormalizer, 'probe_clip')
    def test_h264_passes(self, mock_probe):
        mock_probe.return_value = {
            "width": 1920, "height": 1080, "fps": 30,
            "codec": "h264",
        }
        report = QAReport(job_id="j1", ratio="16:9", video_path="v.mp4")
        self.checker._check_codecs(report, "v.mp4")
        check = [c for c in report.checks if c.check_name == "video_codec"][0]
        assert check.passed

    @patch.object(VideoNormalizer, 'probe_clip')
    def test_vp9_fails(self, mock_probe):
        mock_probe.return_value = {
            "width": 1920, "height": 1080, "fps": 30,
            "codec": "vp9",
        }
        report = QAReport(job_id="j1", ratio="16:9", video_path="v.mp4")
        self.checker._check_codecs(report, "v.mp4")
        check = [c for c in report.checks if c.check_name == "video_codec"][0]
        assert not check.passed


class TestAudioDriftCheck:
    """Tests for audio drift detection."""

    def setup_method(self):
        self.checker = OutputQAChecker()

    @patch.object(VideoNormalizer, 'probe_clip')
    def test_no_drift_passes(self, mock_probe):
        """Video duration matching narration should pass."""
        mock_probe.return_value = {
            "width": 1920, "height": 1080, "fps": 30,
            "duration": 10.0,
        }
        report = QAReport(job_id="j1", ratio="16:9", video_path="v.mp4")
        self.checker._check_audio_drift(report, "v.mp4", 10.0)
        check = [c for c in report.checks if c.check_name == "audio_drift"][0]
        assert check.passed

    @patch.object(VideoNormalizer, 'probe_clip')
    def test_drift_within_tolerance_passes(self, mock_probe):
        """Up to 0.5s drift should pass."""
        mock_probe.return_value = {
            "width": 1920, "height": 1080, "fps": 30,
            "duration": 10.4,
        }
        report = QAReport(job_id="j1", ratio="16:9", video_path="v.mp4")
        self.checker._check_audio_drift(report, "v.mp4", 10.0)
        check = [c for c in report.checks if c.check_name == "audio_drift"][0]
        assert check.passed

    @patch.object(VideoNormalizer, 'probe_clip')
    def test_excessive_drift_warns(self, mock_probe):
        """More than 0.5s drift should warn."""
        mock_probe.return_value = {
            "width": 1920, "height": 1080, "fps": 30,
            "duration": 12.0,
        }
        report = QAReport(job_id="j1", ratio="16:9", video_path="v.mp4")
        self.checker._check_audio_drift(report, "v.mp4", 10.0)
        check = [c for c in report.checks if c.check_name == "audio_drift"][0]
        assert not check.passed
        assert "drift" in check.message.lower()
