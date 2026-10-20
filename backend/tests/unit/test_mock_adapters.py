import os
import wave
import pytest
from app.adapters.stt.mock_stt import MockSTTAdapter
from app.adapters.tts.mock_tts import MockTTSAdapter
from app.adapters.llm.mock_llm import MockLLMAdapter
from app.adapters.footage.mock_footage import MockFootageProvider
from app.adapters.vision.mock_vision import MockVisionScorer

def test_mock_stt_adapter():
    stt = MockSTTAdapter()
    result = stt.transcribe("sample_assets/audio/clean_voice.mp3")
    assert "words" in result
    assert len(result["words"]) > 0
    assert result["words"][0]["start"] >= 0
    assert result["words"][0]["end"] > result["words"][0]["start"]
    assert result["duration"] > 0

def test_mock_tts_adapter(tmp_path):
    tts = MockTTSAdapter(output_dir=str(tmp_path))
    wav_path = tts.synthesize("Trust is earned slowly and lost quickly.", voice="en-US-Standard")
    assert os.path.exists(wav_path)

    # Verify standard WAV headers
    with wave.open(wav_path, "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000
        frames = wf.getnframes()
        assert frames > 0

def test_mock_llm_disambiguation():
    llm = MockLLMAdapter()

    # Ambiguity: python
    res_python = llm.understand_scene("We built our entire backend using python.")
    assert "software" in res_python["search_query"].lower() or "programming" in res_python["search_query"].lower()

    # Ambiguity: bank
    res_bank = llm.understand_scene("The money was transferred directly to the bank.")
    assert "finance" in res_bank["search_query"].lower() or "financial" in res_bank["search_query"].lower()

    # Ambiguity: cloud
    res_cloud = llm.understand_scene("All customer files are backed up safely to the cloud.")
    assert "server" in res_cloud["search_query"].lower() or "computing" in res_cloud["search_query"].lower()

def test_mock_llm_metaphor_and_stats():
    llm = MockLLMAdapter()

    # Metaphor: trust
    res_trust = llm.understand_scene("In business, trust is earned slowly.")
    assert "hands" in res_trust["search_query"].lower() or "partnership" in res_trust["search_query"].lower()
    assert len(res_trust["metaphors"]) > 0

    # Statistics detection
    res_stat = llm.understand_scene("Over 78% of customers returned within thirty days.")
    assert res_stat["is_statistic"] is True
    assert "graph" in res_stat["search_query"].lower() or "analytics" in res_stat["search_query"].lower()

def test_mock_llm_entity_safety():
    llm = MockLLMAdapter()

    # Named Person: Elon Musk
    res_elon = llm.understand_scene("Elon Musk announced a new rocket design today.")
    assert res_elon["contains_brand_or_person"] is True
    assert res_elon["safety_warning"] is not None
    assert "Policy" in res_elon["safety_warning"]

    # Brand: Apple
    res_apple = llm.understand_scene("Apple launched its flagship store in Mumbai.")
    assert res_apple["contains_brand_or_person"] is True
    assert res_apple["safety_warning"] is not None

def test_mock_footage_provider_and_avoid_tags():
    provider = MockFootageProvider()

    # Normal search
    candidates = provider.search_footage("server cloud data", count=3)
    assert len(candidates) > 0
    assert candidates[0]["relevance_score"] > 0
    assert candidates[0]["licence_name"] is not None

    # Avoid tag test
    candidates_avoid = provider.search_footage("technology", count=5, avoid=["coding", "typing"])
    for c in candidates_avoid:
        assert "clip_workspace_01" != c["id"]

def test_mock_vision_scorer():
    scorer = MockVisionScorer()
    candidate = {"title": "Business handshake in modern office", "tags": ["business", "handshake", "trust"]}
    score = scorer.score_relevance(candidate, "Trust is earned slowly", visual_hint="business handshake")
    assert 0.0 <= score <= 1.0
    assert score >= 0.35  # Strong overlap
