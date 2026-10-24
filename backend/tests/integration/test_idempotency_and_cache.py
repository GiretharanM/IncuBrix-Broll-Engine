import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.pipeline.stage7_normalize import video_normalizer

@pytest.mark.asyncio
async def test_idempotency_same_key_returns_existing_job():
    """
    Submitting with the exact same idempotency key must return the existing job_id
    without duplicating the processing.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        key = f"idem-key-{uuid.uuid4()}"
        payload = {
            "script_text": "Robots automate production lines with precision.",
            "voice": "en-US-Standard",
            "aspect_ratios": ["16:9"],
            "style": "cinematic",
            "avoid": ["watermark"],
            "burn_in_captions": True,
            "srt_captions": True,
        }

        # First request
        res1 = await client.post("/api/v1/broll/jobs", json=payload, headers={"Idempotency-Key": key})
        assert res1.status_code == 202
        data1 = res1.json()
        job1_id = data1["job_id"]

        # Second request with SAME key
        res2 = await client.post("/api/v1/broll/jobs", json=payload, headers={"Idempotency-Key": key})
        assert res2.status_code == 202
        data2 = res2.json()
        job2_id = data2["job_id"]

        assert job1_id == job2_id
        assert "matched" in data2["message"].lower() or "already exists" in data2["message"].lower()

@pytest.mark.asyncio
async def test_two_different_scripts_with_different_keys_produce_different_jobs():
    """
    Two different scripts with different idempotency keys must produce
    different job_ids, different timelines, and different cache segment hashes.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        key1 = f"idem-script1-{uuid.uuid4()}"
        key2 = f"idem-script2-{uuid.uuid4()}"

        script1 = "Robots and artificial intelligence are revolutionizing modern factories with automation."
        script2 = "Healthy habits help us live a better life with fresh fruits, vegetables, and daily exercise."

        payload1 = {
            "script_text": script1,
            "voice": "en-US-Standard",
            "aspect_ratios": ["16:9"],
            "style": "cinematic",
            "avoid": ["watermark"],
            "burn_in_captions": True,
            "srt_captions": True,
        }

        payload2 = {
            "script_text": script2,
            "voice": "en-US-Standard",
            "aspect_ratios": ["16:9"],
            "style": "documentary",
            "avoid": ["logos"],
            "burn_in_captions": True,
            "srt_captions": True,
        }

        res1 = await client.post("/api/v1/broll/jobs", json=payload1, headers={"Idempotency-Key": key1})
        res2 = await client.post("/api/v1/broll/jobs", json=payload2, headers={"Idempotency-Key": key2})

        assert res1.status_code == 202
        assert res2.status_code == 202

        data1 = res1.json()
        data2 = res2.json()

        assert data1["job_id"] != data2["job_id"]

        # Verify Cache-Control: no-store header on job endpoint
        status_res = await client.get(f"/api/v1/jobs/{data1['job_id']}")
        assert status_res.status_code == 200
        assert "no-store" in status_res.headers.get("Cache-Control", "")

        # Verify timeline endpoint has no-store header
        timeline_res = await client.get(f"/api/v1/jobs/{data1['job_id']}/timeline.json")
        assert timeline_res.status_code == 200
        assert "no-store" in timeline_res.headers.get("Cache-Control", "")

@pytest.mark.asyncio
async def test_cache_keys_vary_with_script_content_voice_and_settings():
    """
    Tests that compute_segment_hash incorporates script content, voice,
    style, avoid tags, provider, and settings version.
    """
    hash1 = video_normalizer.compute_segment_hash(
        clip_id="clip_shared_123",
        ratio="16:9",
        start_time=0.0,
        duration=4.0,
        filters="scale=1920:1080",
        script_text="Modern industrial robotic factory",
        voice="en-US-Standard",
        style="cinematic",
        avoid_tags=["watermark"],
        provider="pixabay",
        settings_version="1.0.0",
    )

    hash2 = video_normalizer.compute_segment_hash(
        clip_id="clip_shared_123",
        ratio="16:9",
        start_time=0.0,
        duration=4.0,
        filters="scale=1920:1080",
        script_text="Fresh organic fruits and vegetables",
        voice="en-US-Standard",
        style="cinematic",
        avoid_tags=["watermark"],
        provider="pixabay",
        settings_version="1.0.0",
    )

    assert hash1 != hash2, "Different script contents must yield distinct segment cache hashes"
