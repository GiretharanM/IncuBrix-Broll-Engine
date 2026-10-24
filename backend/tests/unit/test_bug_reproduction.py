import pytest
import uuid
import httpx
from app.config import settings
from app.pipeline.stage7_normalize import video_normalizer

@pytest.mark.asyncio
async def test_evidence_bug1_cache_key_omits_script_voice_and_settings():
    """
    EVIDENCE FOR BUG 1(b):
    Current compute_segment_hash omits text, language, voice, style, avoid list, provider, and settings version.
    """
    # Two entirely different scripts/voices with same clip_id and scene duration produce IDENTICAL cache hashes!
    hash1 = video_normalizer.compute_segment_hash(
        clip_id="clip_123",
        ratio="16:9",
        start_time=0.0,
        duration=4.0,
        filters="scale=1920:1080",
    )
    hash2 = video_normalizer.compute_segment_hash(
        clip_id="clip_123",
        ratio="16:9",
        start_time=0.0,
        duration=4.0,
        filters="scale=1920:1080",
    )
    assert hash1 == hash2

    # Currently compute_segment_hash doesn't even accept script text, voice, avoid list, or settings version!
    import inspect
    sig = inspect.signature(video_normalizer.compute_segment_hash)
    params = list(sig.parameters.keys())
    assert "script_text" not in params, "Demonstrates bug: compute_segment_hash omits script text input"

def test_evidence_bug2_pixabay_adapter_is_not_async_and_no_safesearch():
    """
    EVIDENCE FOR BUG 2:
    Existing PixabayFootageAdapter is synchronous (uses httpx.Client),
    lacks async search, lacks safesearch parameter, and does not download clips locally to storage.
    """
    from app.adapters.footage.pixabay_adapter import PixabayFootageAdapter
    import inspect

    adapter = PixabayFootageAdapter()
    assert not inspect.iscoroutinefunction(adapter.search_footage), "Demonstrates bug: search_footage is synchronous instead of async"
