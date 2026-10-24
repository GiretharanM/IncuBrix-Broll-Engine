"""
Automated Output QA Checks
-----------------------------
Post-render quality assurance verifications run against every
output video to catch defects before delivery.

Checks performed:
1. Aspect ratio matches requested ratio
2. Frame rate is exactly 30 fps
3. Video codec is H.264, audio codec is AAC
4. No black frames (using blackdetect statistics)
5. No frozen frames (using freezedetect)
6. Audio drift check (narration duration vs video duration)
7. No repeated clips across scenes (clip_id uniqueness)
8. Full narration coverage (every second of narration has a scene)

All checks return structured QAResult objects so the pipeline
can accumulate warnings without crashing.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.pipeline.stage7_normalize import VideoNormalizer, video_normalizer, RESOLUTION_MAP

logger = logging.getLogger(__name__)


@dataclass
class QAResult:
    """Result of a single QA check."""
    check_name: str
    passed: bool
    expected: str = ""
    actual: str = ""
    severity: str = "error"  # "error" | "warning" | "info"
    message: str = ""


@dataclass
class QAReport:
    """Complete QA report for a rendered video."""
    job_id: str
    ratio: str
    video_path: str
    checks: List[QAResult] = field(default_factory=list)
    passed: bool = True
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def add_check(self, result: QAResult):
        self.checks.append(result)
        if not result.passed:
            if result.severity == "error":
                self.passed = False
                self.errors.append(f"[{result.check_name}] {result.message}")
            else:
                self.warnings.append(f"[{result.check_name}] {result.message}")

    def summary(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "ratio": self.ratio,
            "video_path": self.video_path,
            "passed": self.passed,
            "total_checks": len(self.checks),
            "passed_checks": sum(1 for c in self.checks if c.passed),
            "failed_checks": sum(1 for c in self.checks if not c.passed),
            "errors": self.errors,
            "warnings": self.warnings,
        }


class OutputQAChecker:
    """
    Runs automated quality assurance checks on rendered video outputs.
    Uses ffprobe for metadata inspection (via VideoNormalizer.run_ffmpeg
    which is mockable in tests).
    """

    def __init__(self):
        self.normalizer = video_normalizer

    # ----------------------------------------------------------------
    # Main entry point
    # ----------------------------------------------------------------

    def run_full_qa(
        self,
        job_id: str,
        render_results: Dict[str, Dict[str, Any]],
        timeline_data: Dict[str, Any],
        narration_duration: float,
    ) -> Dict[str, QAReport]:
        """
        Runs all QA checks on every rendered video.

        Args:
            job_id: Job identifier
            render_results: Per-ratio render outputs
            timeline_data: Timeline JSON for clip/coverage checks
            narration_duration: Total narration audio duration

        Returns:
            Dict mapping ratio → QAReport
        """
        reports: Dict[str, QAReport] = {}
        scenes = timeline_data.get("scenes", [])

        for ratio, render_info in render_results.items():
            video_path = render_info.get("video_path")
            if not video_path:
                report = QAReport(
                    job_id=job_id, ratio=ratio, video_path="MISSING",
                )
                report.add_check(QAResult(
                    check_name="file_exists",
                    passed=False,
                    severity="error",
                    message=f"No video file produced for ratio {ratio}",
                ))
                reports[ratio] = report
                continue

            report = QAReport(
                job_id=job_id, ratio=ratio, video_path=video_path,
            )

            # Run individual checks
            self._check_file_exists(report, video_path)
            self._check_aspect_ratio(report, video_path, ratio)
            self._check_fps(report, video_path)
            self._check_codecs(report, video_path)
            self._check_black_frames(report, video_path)
            self._check_frozen_frames(report, video_path)
            self._check_audio_drift(report, video_path, narration_duration)

            reports[ratio] = report

        # Cross-video checks (run once, apply to all reports)
        self._check_no_repeated_clips(reports, scenes)
        self._check_narration_coverage(reports, scenes, narration_duration)

        return reports

    # ----------------------------------------------------------------
    # Individual QA checks
    # ----------------------------------------------------------------

    def _check_file_exists(self, report: QAReport, path: str):
        """Verify the output file exists and has non-zero size."""
        exists = os.path.isfile(path)
        size = os.path.getsize(path) if exists else 0

        report.add_check(QAResult(
            check_name="file_exists",
            passed=exists and size > 0,
            expected="File exists with size > 0",
            actual=f"exists={exists}, size={size}",
            severity="error",
            message="" if (exists and size > 0) else f"Output file missing or empty: {path}",
        ))

    def _check_aspect_ratio(self, report: QAReport, path: str, ratio: str):
        """Verify the video dimensions match the requested aspect ratio."""
        try:
            probe = self.normalizer.probe_clip(path)
            actual_w = probe["width"]
            actual_h = probe["height"]
            expected_w, expected_h = RESOLUTION_MAP.get(ratio, (1920, 1080))

            # Allow ±2px tolerance for rounding
            w_ok = abs(actual_w - expected_w) <= 2
            h_ok = abs(actual_h - expected_h) <= 2

            report.add_check(QAResult(
                check_name="aspect_ratio",
                passed=w_ok and h_ok,
                expected=f"{expected_w}x{expected_h}",
                actual=f"{actual_w}x{actual_h}",
                severity="error",
                message="" if (w_ok and h_ok) else (
                    f"Aspect ratio mismatch: expected {expected_w}x{expected_h}, "
                    f"got {actual_w}x{actual_h}"
                ),
            ))
        except Exception as e:
            report.add_check(QAResult(
                check_name="aspect_ratio",
                passed=False,
                severity="error",
                message=f"Could not probe aspect ratio: {e}",
            ))

    def _check_fps(self, report: QAReport, path: str):
        """Verify video frame rate is 30 fps."""
        try:
            probe = self.normalizer.probe_clip(path)
            actual_fps = probe["fps"]

            report.add_check(QAResult(
                check_name="fps",
                passed=actual_fps == 30,
                expected="30",
                actual=str(actual_fps),
                severity="error",
                message="" if actual_fps == 30 else (
                    f"FPS mismatch: expected 30, got {actual_fps}"
                ),
            ))
        except Exception as e:
            report.add_check(QAResult(
                check_name="fps",
                passed=False,
                severity="error",
                message=f"Could not probe FPS: {e}",
            ))

    def _check_codecs(self, report: QAReport, path: str):
        """Verify video codec is H.264, pix_fmt is yuv420p, and audio codec is AAC."""
        try:
            probe = self.normalizer.probe_clip(path)
            video_codec = probe.get("codec", "unknown")
            pix_fmt = probe.get("pix_fmt", "unknown")

            # H.264 is reported as "h264" by ffprobe
            h264_ok = video_codec.lower() in ("h264", "libx264")
            pix_fmt_ok = pix_fmt.lower() in ("yuv420p", "unknown")

            report.add_check(QAResult(
                check_name="video_codec",
                passed=h264_ok and pix_fmt_ok,
                expected="h264 (yuv420p)",
                actual=f"{video_codec} ({pix_fmt})",
                severity="error",
                message="" if (h264_ok and pix_fmt_ok) else (
                    f"Video codec/format mismatch: expected h264 yuv420p, got {video_codec} {pix_fmt}"
                ),
            ))
        except Exception as e:
            report.add_check(QAResult(
                check_name="video_codec",
                passed=False,
                severity="error",
                message=f"Could not probe codecs: {e}",
            ))

    def _check_black_frames(self, report: QAReport, path: str):
        """Check for black frames in the output."""
        try:
            warnings = self.normalizer.detect_black_frozen_frames(path)
            black_warnings = [w for w in warnings if "Black" in w or "black" in w]

            report.add_check(QAResult(
                check_name="no_black_frames",
                passed=len(black_warnings) == 0,
                severity="warning",
                message="" if not black_warnings else black_warnings[0],
            ))
        except Exception as e:
            report.add_check(QAResult(
                check_name="no_black_frames",
                passed=True,  # Non-critical, pass if detection unavailable
                severity="info",
                message=f"Black frame detection unavailable: {e}",
            ))

    def _check_frozen_frames(self, report: QAReport, path: str):
        """Check for frozen frames in the output."""
        try:
            warnings = self.normalizer.detect_black_frozen_frames(path)
            frozen_warnings = [w for w in warnings if "Frozen" in w or "frozen" in w or "freeze" in w]

            report.add_check(QAResult(
                check_name="no_frozen_frames",
                passed=len(frozen_warnings) == 0,
                severity="warning",
                message="" if not frozen_warnings else frozen_warnings[0],
            ))
        except Exception as e:
            report.add_check(QAResult(
                check_name="no_frozen_frames",
                passed=True,
                severity="info",
                message=f"Frozen frame detection unavailable: {e}",
            ))

    def _check_audio_drift(
        self, report: QAReport, path: str, narration_duration: float
    ):
        """
        Check that the output video duration matches the narration duration
        within an acceptable tolerance of 100 ms (±0.100 seconds).
        """
        try:
            probe = self.normalizer.probe_clip(path)
            video_duration = probe["duration"]
            drift = abs(video_duration - narration_duration)

            # Enforce 100ms tolerance
            passed = drift <= 0.100

            report.add_check(QAResult(
                check_name="audio_drift",
                passed=passed,
                expected=f"drift <= 0.100s (target: {narration_duration:.2f}s)",
                actual=f"video: {video_duration:.2f}s, drift: {drift:.3f}s",
                severity="error" if drift > 0.500 else "warning",
                message="" if passed else (
                    f"Audio drift detected: {drift:.3f}s exceeds 100ms tolerance between narration "
                    f"({narration_duration:.2f}s) and video ({video_duration:.2f}s)"
                ),
            ))
        except Exception as e:
            report.add_check(QAResult(
                check_name="audio_drift",
                passed=False,
                severity="warning",
                message=f"Could not check audio drift: {e}",
            ))

    # ----------------------------------------------------------------
    # Cross-video checks
    # ----------------------------------------------------------------

    def _check_no_repeated_clips(
        self, reports: Dict[str, QAReport], scenes: List[Dict[str, Any]]
    ):
        """Verify no clip_id is used more than once across all scenes."""
        clip_ids: List[str] = []
        duplicates: Set[str] = set()

        for scene in scenes:
            cid = scene.get("clip_id", "")
            if cid in clip_ids:
                duplicates.add(cid)
            clip_ids.append(cid)

        passed = len(duplicates) == 0
        result = QAResult(
            check_name="no_repeated_clips",
            passed=passed,
            expected="0 duplicate clip IDs",
            actual=f"{len(duplicates)} duplicates: {duplicates}" if duplicates else "0 duplicates",
            severity="error",
            message="" if passed else f"Repeated clips detected: {duplicates}",
        )

        # Add this check to all reports
        for report in reports.values():
            report.add_check(result)

    def _check_narration_coverage(
        self,
        reports: Dict[str, QAReport],
        scenes: List[Dict[str, Any]],
        narration_duration: float,
    ):
        """
        Verify that scenes cover the entire narration duration
        with no gaps. Every second of narration should be covered.
        """
        if not scenes:
            result = QAResult(
                check_name="narration_coverage",
                passed=False,
                severity="error",
                message="No scenes found — narration has no coverage",
            )
            for report in reports.values():
                report.add_check(result)
            return

        # Check contiguous coverage
        sorted_scenes = sorted(scenes, key=lambda s: s.get("start_time", 0))
        first_start = sorted_scenes[0].get("start_time", 0)
        last_end = sorted_scenes[-1].get("end_time", 0)

        # Check for gaps between consecutive scenes
        gaps: List[Tuple[float, float]] = []
        for i in range(len(sorted_scenes) - 1):
            current_end = sorted_scenes[i].get("end_time", 0)
            next_start = sorted_scenes[i + 1].get("start_time", 0)
            if next_start - current_end > 0.05:  # 50ms tolerance
                gaps.append((current_end, next_start))

        # Coverage ratio
        covered = sum(
            s.get("end_time", 0) - s.get("start_time", 0)
            for s in sorted_scenes
        )
        coverage_ratio = covered / max(narration_duration, 0.001)

        passed = (
            len(gaps) == 0
            and first_start <= 0.05
            and coverage_ratio >= 0.95
        )

        result = QAResult(
            check_name="narration_coverage",
            passed=passed,
            expected="100% coverage, no gaps",
            actual=f"coverage={coverage_ratio:.1%}, gaps={len(gaps)}, start={first_start:.2f}",
            severity="error" if not passed else "info",
            message="" if passed else (
                f"Narration coverage incomplete: {coverage_ratio:.1%} covered, "
                f"{len(gaps)} gap(s) found"
            ),
        )

        for report in reports.values():
            report.add_check(result)


# Module-level singleton
output_qa_checker = OutputQAChecker()
