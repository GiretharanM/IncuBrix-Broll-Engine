import pytest
import os
import json
import subprocess
import tempfile
import asyncio
from app.pipeline.stage7_normalize import VideoNormalizer, find_ffmpeg_binary, RESOLUTION_MAP
from app.pipeline.stage8_render import VideoRenderer
from app.pipeline.qa_checks import OutputQAChecker, QAReport, QAResult
from app.pipeline.runner import pipeline_runner

@pytest.fixture
def normalizer():
    return VideoNormalizer()

@pytest.fixture
def ffprobe():
    return find_ffmpeg_binary("ffprobe")

def test_bug3_fallback_duration_matches_scene_within_100ms(normalizer, ffprobe):
    """
    BUG 3 Regression Test:
    Fallback segments must use the scene's actual duration, never a fixed default.
    The segment duration must equal the requested duration within 100 ms.
    """
    requested_duration = 3.5
    clip = normalizer._generate_fallback_card(
        scene_id="test_scene_dur",
        scene_index=0,
        ratio="16:9",
        duration=requested_duration,
        text="Testing Exact Duration",
    )
    assert os.path.isfile(clip.output_path), f"Fallback clip was not created at {clip.output_path}"
    assert abs(clip.duration - requested_duration) <= 0.05, f"Clip metadata duration {clip.duration} drifted from {requested_duration}"

    # Probe actual output file using ffprobe
    cmd = [
        ffprobe,
        "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "json",
        clip.output_path,
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert res.returncode == 0, f"ffprobe failed: {res.stderr}"
    data = json.loads(res.stdout)
    actual_duration = float(data["format"]["duration"])

    # Must be within 100ms (0.100 s)
    drift = abs(actual_duration - requested_duration)
    assert drift <= 0.10, f"Audio/video drift {drift:.3f}s exceeds 100ms tolerance! Actual: {actual_duration}, Expected: {requested_duration}"

def test_bug4_aspect_ratios_and_codecs(normalizer, ffprobe):
    """
    BUG 4 Regression Test:
    Every requested ratio (16:9, 9:16, 1:1) must produce the exact target dimensions:
    - 16:9 -> 1920x1080
    - 9:16 -> 1080x1920
    - 1:1  -> 1080x1080
    And browser-playable codec:
    - Codec: h264
    - Profile: High or Main
    - Pixel format: yuv420p
    """
    targets = {
        "16:9": (1920, 1080),
        "9:16": (1080, 1920),
        "1:1": (1080, 1080),
    }

    for ratio, (exp_w, exp_h) in targets.items():
        clip = normalizer._generate_fallback_card(
            scene_id=f"test_ratio_{ratio.replace(':', '_')}",
            scene_index=0,
            ratio=ratio,
            duration=2.0,
            text=f"Testing {ratio}",
        )
        assert os.path.isfile(clip.output_path)
        assert clip.width == exp_w
        assert clip.height == exp_h

        # Probe with ffprobe
        cmd = [
            ffprobe,
            "-v", "quiet",
            "-show_entries", "stream=width,height,codec_name,profile,pix_fmt",
            "-of", "json",
            clip.output_path,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert res.returncode == 0
        data = json.loads(res.stdout)
        stream = data["streams"][0]

        assert stream["width"] == exp_w, f"Ratio {ratio} width {stream['width']} != expected {exp_w}"
        assert stream["height"] == exp_h, f"Ratio {ratio} height {stream['height']} != expected {exp_h}"
        assert stream["codec_name"] == "h264", f"Ratio {ratio} codec {stream['codec_name']} != h264"
        assert stream["pix_fmt"] == "yuv420p", f"Ratio {ratio} pix_fmt {stream['pix_fmt']} != yuv420p"
        assert stream["profile"].lower() in ("high", "main"), f"Profile {stream['profile']} not High/Main"

def test_bug1_qa_inspector_enforces_100ms_audio_drift(normalizer):
    """
    BUG 1 & 3: OutputQAChecker enforces strict 100ms max drift between video duration and narration duration.
    """
    qa = OutputQAChecker()
    # Create a 3.0s test clip
    clip = normalizer._generate_fallback_card(
        scene_id="test_qa_drift",
        scene_index=0,
        ratio="16:9",
        duration=3.0,
        text="QA Drift Test",
    )
    # Test with 3.15s narration (drift 150ms > 100ms -> fail)
    report_fail = QAReport(job_id="test_fail", ratio="16:9", video_path=clip.output_path)
    qa._check_audio_drift(report_fail, clip.output_path, narration_duration=3.15)
    drift_check = [c for c in report_fail.checks if c.check_name == "audio_drift"][0]
    assert not drift_check.passed, "Drift of 150ms should fail audio_drift check"

    # Test with 3.05s narration (drift 50ms <= 100ms -> pass)
    report_pass = QAReport(job_id="test_pass", ratio="16:9", video_path=clip.output_path)
    qa._check_audio_drift(report_pass, clip.output_path, narration_duration=3.05)
    drift_check_pass = [c for c in report_pass.checks if c.check_name == "audio_drift"][0]
    assert drift_check_pass.passed, "Drift of 50ms should pass audio_drift check"

def test_download_endpoint_range_and_mime_type(normalizer):
    """
    BUG 1 Regression Test:
    Download/streaming endpoint must return Content-Type: video/mp4, Accept-Ranges: bytes,
    and support Range requests (HTTP 206 Partial Content).
    """
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import settings

    # Create dummy output file in cache
    test_job_id = "test_download_job"
    out_dir = os.path.join(settings.CACHE_DIR, "output", test_job_id)
    os.makedirs(out_dir, exist_ok=True)
    video_file = os.path.join(out_dir, "video_16x9.mp4")

    # Generate small valid mp4 file
    clip = normalizer._generate_fallback_card(
        scene_id="stream_test",
        scene_index=0,
        ratio="16:9",
        duration=1.0,
        text="Stream test",
    )
    import shutil
    shutil.copyfile(clip.output_path, video_file)

    client = TestClient(app)

    # 1. Full GET request
    resp = client.get(f"/api/v1/jobs/{test_job_id}/download/video_16x9.mp4")
    assert resp.status_code == 200
    assert resp.headers.get("content-type") == "video/mp4"
    assert resp.headers.get("accept-ranges") == "bytes"
    total_len = len(resp.content)
    assert total_len > 1000

    # 2. Range request (first 500 bytes)
    range_resp = client.get(
        f"/api/v1/jobs/{test_job_id}/download/video_16x9.mp4",
        headers={"Range": "bytes=0-499"},
    )
    assert range_resp.status_code == 206, f"Expected 206 Partial Content, got {range_resp.status_code}"
    assert len(range_resp.content) == 500
    assert "bytes 0-499/" in range_resp.headers.get("content-range", "")

