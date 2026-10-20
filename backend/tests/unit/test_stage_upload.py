"""
Tests for Stage Upload: S3/MinIO Upload Orchestration
-------------------------------------------------------
Tests upload of videos, SRTs, timeline, and manifest to MinIO
with presigned URL generation.
"""

import json
import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from app.pipeline.stage_upload import OutputUploader


class TestOutputUploader:
    """Tests for MinIO upload orchestration."""

    def setup_method(self):
        self.uploader = OutputUploader()

    def test_upload_structure(self):
        """Upload result should have videos, captions, timeline, manifest keys."""
        # Mock the storage client
        self.uploader.storage = MagicMock()
        self.uploader.storage.upload_file.return_value = "http://minio/file"
        self.uploader.storage.upload_bytes.return_value = "http://minio/bytes"

        # Create temp video and srt files
        tmpdir = tempfile.mkdtemp()
        video_path = os.path.join(tmpdir, "video_16x9.mp4")
        srt_path = os.path.join(tmpdir, "captions_16x9.srt")
        with open(video_path, "w") as f:
            f.write("fake video")
        with open(srt_path, "w") as f:
            f.write("1\n00:00:00,000 --> 00:00:03,000\nTest\n")

        render_results = {
            "16:9": {
                "video_path": video_path,
                "srt_path": srt_path,
                "duration": 10.0,
                "ratio": "16:9",
                "warnings": [],
            },
        }

        result = self.uploader.upload_job_outputs(
            job_id="test_job",
            render_results=render_results,
            timeline_data={"job_id": "test_job", "scenes": []},
            manifest_data={"job_id": "test_job"},
        )

        assert "videos" in result
        assert "captions_srt" in result
        assert "timeline_json" in result
        assert "manifest_json" in result
        assert "16:9" in result["videos"]

    def test_missing_video_produces_warning(self):
        """Missing video files should produce a warning, not crash."""
        self.uploader.storage = MagicMock()
        self.uploader.storage.upload_bytes.return_value = "http://minio/bytes"

        render_results = {
            "16:9": {
                "video_path": "/nonexistent/video.mp4",
                "srt_path": None,
                "ratio": "16:9",
                "warnings": [],
            },
        }

        result = self.uploader.upload_job_outputs(
            job_id="test_job",
            render_results=render_results,
            timeline_data={},
            manifest_data={},
        )

        assert len(result["warnings"]) > 0
        assert "missing" in result["warnings"][0].lower()

    def test_upload_json_from_dict(self):
        """Should upload JSON directly from dict when no file path given."""
        self.uploader.storage = MagicMock()
        self.uploader.storage.upload_bytes.return_value = "http://minio/timeline.json"

        url = self.uploader._upload_json(
            job_id="j1",
            filename="timeline.json",
            data={"scenes": [], "version": "1.0.0"},
        )

        assert url == "http://minio/timeline.json"
        self.uploader.storage.upload_bytes.assert_called_once()
        call_args = self.uploader.storage.upload_bytes.call_args
        assert call_args.kwargs.get("content_type") == "application/json" or \
               "application/json" in str(call_args)

    def test_upload_json_from_file(self):
        """Should upload JSON from existing file when path is provided."""
        self.uploader.storage = MagicMock()
        self.uploader.storage.upload_file.return_value = "http://minio/manifest.json"

        tmpdir = tempfile.mkdtemp()
        manifest_path = os.path.join(tmpdir, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump({"job_id": "j1"}, f)

        url = self.uploader._upload_json(
            job_id="j1",
            filename="manifest.json",
            data={},
            existing_path=manifest_path,
        )

        assert url == "http://minio/manifest.json"
        self.uploader.storage.upload_file.assert_called_once()

    def test_multi_ratio_upload(self):
        """Should upload videos for all ratios."""
        self.uploader.storage = MagicMock()
        self.uploader.storage.upload_file.return_value = "http://minio/file"
        self.uploader.storage.upload_bytes.return_value = "http://minio/bytes"

        tmpdir = tempfile.mkdtemp()
        render_results = {}
        for ratio in ["16:9", "9:16", "1:1"]:
            label = ratio.replace(":", "x")
            vpath = os.path.join(tmpdir, f"video_{label}.mp4")
            with open(vpath, "w") as f:
                f.write("fake")
            render_results[ratio] = {
                "video_path": vpath,
                "srt_path": None,
                "ratio": ratio,
                "warnings": [],
            }

        result = self.uploader.upload_job_outputs(
            job_id="j_multi",
            render_results=render_results,
            timeline_data={},
            manifest_data={},
        )

        assert len(result["videos"]) == 3
        assert "16:9" in result["videos"]
        assert "9:16" in result["videos"]
        assert "1:1" in result["videos"]
