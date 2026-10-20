"""
Tests for Stage 10: Manifest Builder
---------------------------------------
Tests manifest structure, cost estimation, licence summary,
AI-generated labels, timing formatting, and edge cases.
"""

import json
import os
import tempfile
import pytest
from app.pipeline.stage10_manifest import ManifestBuilder, PIPELINE_VERSION


# Shared test data
SAMPLE_TIMELINE = {
    "job_id": "test_job_001",
    "version": "1.0.0",
    "total_scenes": 3,
    "total_duration_seconds": 10.0,
    "aspect_ratios": ["16:9", "9:16"],
    "scenes": [
        {
            "scene_id": "test_job_001_s00",
            "scene_index": 0,
            "narration_text": "Trust is earned slowly.",
            "start_time": 0.0,
            "end_time": 3.5,
            "duration": 3.5,
            "clip_id": "clip_handshake_02",
            "source": "mock_pixabay",
            "licence": "Pixabay Commercial Clean",
            "attribution": "Pixabay Creator",
            "ai_generated": False,
            "selection_reason": "Best semantic match for trust/handshake",
            "relevance_score": 0.65,
            "source_choice_reason": "Stock footage score 0.65 >= 0.28 threshold",
        },
        {
            "scene_id": "test_job_001_s01",
            "scene_index": 1,
            "narration_text": "Revenue grew 40% this quarter.",
            "start_time": 3.5,
            "end_time": 6.5,
            "duration": 3.0,
            "clip_id": "clip_finance_04",
            "source": "mock_pixabay",
            "licence": "Pixabay Commercial Clean",
            "attribution": "Pixabay Creator",
            "ai_generated": False,
            "selection_reason": "Matched financial statistics context",
            "relevance_score": 0.52,
            "source_choice_reason": "Stock footage score 0.52 >= 0.28 threshold",
        },
        {
            "scene_id": "test_job_001_s02",
            "scene_index": 2,
            "narration_text": "Innovation drives the future.",
            "start_time": 6.5,
            "end_time": 10.0,
            "duration": 3.5,
            "clip_id": "clip_gen_kenburns_06",
            "source": "generative",
            "licence": "IncuBrix Generative Commercial",
            "attribution": "IncuBrix AI Engine",
            "ai_generated": True,
            "selection_reason": "AI-generated cinematic footage",
            "relevance_score": 0.72,
            "source_choice_reason": "Generative adapter used (no stock above threshold)",
        },
    ],
}

SAMPLE_RENDER_RESULTS = {
    "16:9": {
        "video_path": "/tmp/output/video_16x9.mp4",
        "srt_path": "/tmp/output/captions_16x9.srt",
        "duration": 10.0,
        "ratio": "16:9",
        "warnings": [],
    },
    "9:16": {
        "video_path": "/tmp/output/video_9x16.mp4",
        "srt_path": "/tmp/output/captions_9x16.srt",
        "duration": 10.0,
        "ratio": "9:16",
        "warnings": [],
    },
}


class TestManifestStructure:
    """Tests for manifest.json structure and content."""

    def setup_method(self):
        self.builder = ManifestBuilder()

    def test_manifest_has_required_fields(self):
        """Manifest must contain all required top-level fields."""
        manifest = self.builder.build_manifest(
            job_id="test_001",
            timeline_data=SAMPLE_TIMELINE,
            render_results=SAMPLE_RENDER_RESULTS,
            pipeline_config={"voice": "en-US-Standard", "style": "cinematic"},
            timings={"stage_7": 2.5, "stage_8": 5.0},
            warnings=["Test warning"],
        )

        required_fields = [
            "manifest_version", "job_id", "generated_at", "engine",
            "models_and_providers", "settings", "seed", "timings",
            "cost_estimate", "outputs", "quality_metrics",
            "licence_summary", "ai_generated_labels", "warnings",
        ]
        for field in required_fields:
            assert field in manifest, f"Missing field: {field}"

    def test_manifest_engine_info(self):
        """Engine section should have name and version."""
        manifest = self.builder.build_manifest(
            job_id="test_002",
            timeline_data=SAMPLE_TIMELINE,
            render_results=SAMPLE_RENDER_RESULTS,
            pipeline_config={},
            timings={},
            warnings=[],
        )

        assert "pipeline_version" in manifest["engine"]
        assert manifest["engine"]["pipeline_version"] == PIPELINE_VERSION

    def test_manifest_json_serializable(self):
        """Manifest must be JSON-serializable."""
        manifest = self.builder.build_manifest(
            job_id="test_003",
            timeline_data=SAMPLE_TIMELINE,
            render_results=SAMPLE_RENDER_RESULTS,
            pipeline_config={"avoid_tags": ["violence"]},
            timings={"stage_7": 1.0},
            warnings=[],
        )

        # Should not raise
        json_str = json.dumps(manifest, default=str)
        assert len(json_str) > 100


class TestCostEstimation:
    """Tests for cost estimation logic."""

    def setup_method(self):
        self.builder = ManifestBuilder()

    def test_cost_estimate_structure(self):
        """Cost estimate should have total and breakdown."""
        manifest = self.builder.build_manifest(
            job_id="cost_test",
            timeline_data=SAMPLE_TIMELINE,
            render_results=SAMPLE_RENDER_RESULTS,
            pipeline_config={},
            timings={},
            warnings=[],
        )

        cost = manifest["cost_estimate"]
        assert "total_usd" in cost
        assert "breakdown" in cost
        assert "currency" in cost
        assert cost["currency"] == "USD"

    def test_cost_includes_ai_generation(self):
        """Cost should include AI generation when ai_generated scenes exist."""
        manifest = self.builder.build_manifest(
            job_id="ai_cost",
            timeline_data=SAMPLE_TIMELINE,
            render_results=SAMPLE_RENDER_RESULTS,
            pipeline_config={},
            timings={},
            warnings=[],
        )

        # SAMPLE_TIMELINE has 1 AI scene
        assert manifest["cost_estimate"]["breakdown"]["ai_generation"] > 0

    def test_cost_is_non_negative(self):
        """All cost components should be non-negative."""
        manifest = self.builder.build_manifest(
            job_id="nonneg",
            timeline_data=SAMPLE_TIMELINE,
            render_results=SAMPLE_RENDER_RESULTS,
            pipeline_config={},
            timings={},
            warnings=[],
        )

        for key, val in manifest["cost_estimate"]["breakdown"].items():
            assert val >= 0, f"Cost component '{key}' is negative: {val}"


class TestLicenceSummary:
    """Tests for licence/rights summary."""

    def setup_method(self):
        self.builder = ManifestBuilder()

    def test_licence_summary_all_commercial(self):
        """When all licences are commercial, should flag as true."""
        manifest = self.builder.build_manifest(
            job_id="lic_test",
            timeline_data=SAMPLE_TIMELINE,
            render_results=SAMPLE_RENDER_RESULTS,
            pipeline_config={},
            timings={},
            warnings=[],
        )

        assert manifest["licence_summary"]["all_commercial_use"] is True

    def test_licence_counts(self):
        """Should count unique licences used."""
        manifest = self.builder.build_manifest(
            job_id="lic_count",
            timeline_data=SAMPLE_TIMELINE,
            render_results=SAMPLE_RENDER_RESULTS,
            pipeline_config={},
            timings={},
            warnings=[],
        )

        licences = manifest["licence_summary"]["licences_used"]
        assert len(licences) >= 1
        # SAMPLE_TIMELINE has 2 Pixabay + 1 Generative = 2 unique licences
        assert sum(licences.values()) == 3


class TestAILabels:
    """Tests for AI-generated content labeling."""

    def setup_method(self):
        self.builder = ManifestBuilder()

    def test_ai_labels_detected(self):
        """Should identify AI-generated scenes."""
        manifest = self.builder.build_manifest(
            job_id="ai_test",
            timeline_data=SAMPLE_TIMELINE,
            render_results=SAMPLE_RENDER_RESULTS,
            pipeline_config={},
            timings={},
            warnings=[],
        )

        labels = manifest["ai_generated_labels"]
        assert labels["contains_ai_content"] is True
        assert labels["ai_scene_count"] == 1
        assert labels["total_scene_count"] == 3
        assert "AI-generated" in labels["disclosure"]

    def test_no_ai_content(self):
        """When no AI scenes exist, should report appropriately."""
        no_ai_timeline = {
            **SAMPLE_TIMELINE,
            "scenes": [s for s in SAMPLE_TIMELINE["scenes"] if not s.get("ai_generated")],
        }

        manifest = self.builder.build_manifest(
            job_id="no_ai",
            timeline_data=no_ai_timeline,
            render_results=SAMPLE_RENDER_RESULTS,
            pipeline_config={},
            timings={},
            warnings=[],
        )

        labels = manifest["ai_generated_labels"]
        assert labels["contains_ai_content"] is False
        assert labels["ai_scene_count"] == 0
        assert "No AI-generated" in labels["disclosure"]


class TestTimingFormat:
    """Tests for timing formatting."""

    def setup_method(self):
        self.builder = ManifestBuilder()

    def test_timing_human_readable(self):
        """Timings should have human-readable format."""
        manifest = self.builder.build_manifest(
            job_id="time_test",
            timeline_data=SAMPLE_TIMELINE,
            render_results=SAMPLE_RENDER_RESULTS,
            pipeline_config={},
            timings={"stage_7": 15.5, "stage_8": 125.3},
            warnings=[],
        )

        assert manifest["timings"]["stage_7"]["human"] == "15.5s"
        assert "2m" in manifest["timings"]["stage_8"]["human"]
        assert "total" in manifest["timings"]

    def test_seconds_to_human(self):
        """Time formatting helper edge cases."""
        assert ManifestBuilder._seconds_to_human(0.5) == "0.5s"
        assert ManifestBuilder._seconds_to_human(59.9) == "59.9s"
        assert ManifestBuilder._seconds_to_human(60.0) == "1m 0s"
        assert ManifestBuilder._seconds_to_human(3661.0) == "1h 1m 1s"


class TestManifestPersistence:
    """Tests for writing manifest to disk."""

    def test_save_creates_file(self):
        """save_manifest should create a valid JSON file."""
        builder = ManifestBuilder()
        manifest = builder.build_manifest(
            job_id="save_test",
            timeline_data=SAMPLE_TIMELINE,
            render_results=SAMPLE_RENDER_RESULTS,
            pipeline_config={},
            timings={},
            warnings=[],
        )

        output_dir = tempfile.mkdtemp()
        path = builder.save_manifest(manifest, output_dir, "save_test")

        assert os.path.isfile(path)
        with open(path) as f:
            loaded = json.load(f)
        assert loaded["job_id"] == "save_test"


class TestQualityMetrics:
    """Tests for quality metrics in manifest."""

    def setup_method(self):
        self.builder = ManifestBuilder()

    def test_avg_relevance_calculated(self):
        """Average relevance should be computed from all scenes."""
        manifest = self.builder.build_manifest(
            job_id="qm_test",
            timeline_data=SAMPLE_TIMELINE,
            render_results=SAMPLE_RENDER_RESULTS,
            pipeline_config={},
            timings={},
            warnings=[],
        )

        qm = manifest["quality_metrics"]
        # (0.65 + 0.52 + 0.72) / 3 = 0.63
        assert 0.62 <= qm["avg_relevance_score"] <= 0.64

    def test_repeat_clip_rate_zero(self):
        """Repeat clip rate should always be 0 (enforced by stage 6)."""
        manifest = self.builder.build_manifest(
            job_id="repeat_test",
            timeline_data=SAMPLE_TIMELINE,
            render_results=SAMPLE_RENDER_RESULTS,
            pipeline_config={},
            timings={},
            warnings=[],
        )

        assert manifest["quality_metrics"]["repeat_clip_rate"] == 0.0

    def test_narration_coverage_full(self):
        """Narration coverage should be 1.0 (enforced by stage 3)."""
        manifest = self.builder.build_manifest(
            job_id="cov_test",
            timeline_data=SAMPLE_TIMELINE,
            render_results=SAMPLE_RENDER_RESULTS,
            pipeline_config={},
            timings={},
            warnings=[],
        )

        assert manifest["quality_metrics"]["narration_coverage"] == 1.0
