import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "X-Correlation-Id" in response.headers

@pytest.mark.asyncio
async def test_readiness_check(client: AsyncClient):
    response = await client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "postgres" in data
    assert "redis" in data
    assert "minio" in data

@pytest.mark.asyncio
async def test_create_job_and_idempotency(client: AsyncClient):
    payload = {
        "script_text": "IncuBrix turns voiceovers into cinematic B-roll automatically.",
        "voice": "en-US-Standard",
        "aspect_ratios": ["16:9", "9:16"],
        "style": "cinematic",
        "avoid": ["watermark"],
        "burn_in_captions": True,
        "srt_captions": True,
    }
    headers = {"Idempotency-Key": "test-idem-key-001"}

    # First request
    response1 = await client.post("/api/v1/broll/jobs", json=payload, headers=headers)
    assert response1.status_code == 202
    data1 = response1.json()
    assert "job_id" in data1
    assert data1["status"] == "queued"
    job_id = data1["job_id"]

    # Repeated request with same Idempotency-Key
    response2 = await client.post("/api/v1/broll/jobs", json=payload, headers=headers)
    assert response2.status_code == 202
    data2 = response2.json()
    assert data2["job_id"] == job_id
    assert "idempotency key matched" in data2["message"]

@pytest.mark.asyncio
async def test_get_job_status(client: AsyncClient):
    # Create job
    payload = {"script_text": "A brief sentence for testing status retrieval."}
    create_res = await client.post("/api/v1/broll/jobs", json=payload)
    assert create_res.status_code == 202
    job_id = create_res.json()["job_id"]

    # Query status
    status_res = await client.get(f"/api/v1/jobs/{job_id}")
    assert status_res.status_code == 200
    data = status_res.json()
    assert data["job_id"] == job_id
    assert data["status"] in ["queued", "running", "succeeded"]
    assert "progress" in data
    assert "aspect_ratios" in data

@pytest.mark.asyncio
async def test_empty_script_validation_error(client: AsyncClient):
    payload = {}  # No audio, no script, no scenes
    response = await client.post("/api/v1/broll/jobs", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "EMPTY_SCRIPT"
    assert data["error"]["retryable"] is False

@pytest.mark.asyncio
async def test_non_existent_job_error(client: AsyncClient):
    response = await client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "JOB_NOT_FOUND"
