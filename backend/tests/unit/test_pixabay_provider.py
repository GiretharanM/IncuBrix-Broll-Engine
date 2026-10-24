import os
import pytest
import httpx
from unittest.mock import patch, MagicMock
from app.adapters.footage.pixabay_adapter import PixabayProvider

SAMPLE_PIXABAY_HIT = {
    "id": 123456,
    "pageURL": "https://pixabay.com/videos/id-123456/",
    "type": "film",
    "tags": "ocean, waves, water, sea",
    "duration": 14,
    "user": "OceanCreator",
    "videos": {
        "large": {
            "url": "https://cdn.pixabay.com/video/2026/ocean_large.mp4",
            "width": 1920,
            "height": 1080,
            "size": 25000000,
        },
        "medium": {
            "url": "https://cdn.pixabay.com/video/2026/ocean_medium.mp4",
            "width": 1280,
            "height": 720,
            "size": 12000000,
        },
    },
}

@pytest.mark.asyncio
async def test_pixabay_provider_search_success_mocked():
    """Unit test: Pixabay search returns structured candidate metadata on 200 OK."""
    provider = PixabayProvider(api_key="valid_dummy_key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"hits": [SAMPLE_PIXABAY_HIT]}

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        candidates = await provider.search_footage_async("ocean waves", count=1)

    assert len(candidates) == 1
    c = candidates[0]
    assert c["id"] == "pixabay_123456"
    assert c["provider"] == "pixabay"
    assert c["uploader"] == "OceanCreator"
    assert c["pageURL"] == "https://pixabay.com/videos/id-123456/"
    assert c["width"] == 1920
    assert c["height"] == 1080
    assert "Pixabay Content License" in c["licence"]

@pytest.mark.asyncio
async def test_pixabay_provider_handles_429_backoff():
    """Unit test: Pixabay provider backs off and retries on HTTP 429."""
    provider = PixabayProvider(api_key="valid_dummy_key")

    mock_429 = MagicMock()
    mock_429.status_code = 429

    mock_200 = MagicMock()
    mock_200.status_code = 200
    mock_200.json.return_value = {"hits": [SAMPLE_PIXABAY_HIT]}

    # First call returns 429, second returns 200
    with patch("httpx.AsyncClient.get", side_effect=[mock_429, mock_200]), \
         patch("asyncio.sleep", return_value=None):
        candidates = await provider.search_footage_async("ocean waves", count=1)

    assert len(candidates) == 1
    assert candidates[0]["id"] == "pixabay_123456"

@pytest.mark.asyncio
async def test_pixabay_provider_handles_invalid_key_auth_failed():
    """Unit test: 400/401 invalid key triggers PROVIDER_AUTH_FAILED and graceful fallback."""
    provider = PixabayProvider(api_key="invalid_bad_key")

    mock_400 = MagicMock()
    mock_400.status_code = 400

    warnings = []
    with patch("httpx.AsyncClient.get", return_value=mock_400):
        candidates = await provider.search_footage_async("ocean waves", count=1, warnings_out=warnings)

    assert candidates == []
    assert any("PROVIDER_AUTH_FAILED" in w for w in warnings)

@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("PIXABAY_API_KEY") or os.getenv("PIXABAY_API_KEY", "").startswith("mock"),
    reason="PIXABAY_API_KEY not configured or set to mock. Skipping live network test.",
)
async def test_pixabay_provider_live_ocean_waves():
    """Opt-in live network test against real Pixabay API searching 'ocean waves'."""
    provider = PixabayProvider()
    candidates = await provider.search_footage_async("ocean waves", count=2)

    assert len(candidates) > 0, "Real Pixabay API should return hits for 'ocean waves'"
    cand = candidates[0]
    assert cand["provider"] == "pixabay"
    assert cand["id"].startswith("pixabay_")
    assert cand["download_url"].startswith("http")
    assert cand["uploader"]
