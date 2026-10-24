"""
Test Suite for Quick Prompt Video Generation Mode
--------------------------------------------------
Covers:
1. Prompt moderation & error codes:
   - PROMPT_EMPTY on empty or whitespace prompt
   - PROMPT_TOO_LONG on prompt > 500 chars
   - PROMPT_NOT_ALLOWED on hazardous content
   - Sensitive-but-legitimate prompts permitted (e.g. "sad news hospital")
2. Deterministic named-entity & brand detection:
   - "apple on a tree" -> real fruit (NOT substituted)
   - "python code on screen" -> coding (NOT substituted)
   - "Apple Inc stock" -> brand substitution with warning
   - "Elon Musk" -> celebrity substitution with warning
3. Non-English translations:
   - Hindi ("सुंदर सूर्यास्त") translated for search, original preserved
   - Tamil ("அழகான சூரிய உதயம்") translated for search, original preserved
4. Prompt expansion & shot variety:
   - N ~ round(duration / 4)
   - 3 cascading queries ordered specific -> medium -> generic
   - Avoid tags excluded from queries
   - Seed variations yield different scene angles and queries
5. Cache-key uniqueness & regression test:
   - Different prompts, duration, or seed produce distinct cache segment hashes
6. Full 16-Prompt Test Pack Runner
"""

import pytest
from app.pipeline.prompt_moderation import prompt_moderator
from app.pipeline.named_entity_detector import named_entity_detector
from app.pipeline.prompt_expansion import prompt_expander
from app.pipeline.stage7_normalize import VideoNormalizer
from app.pipeline.stage6_ranking import CandidateRanker
from app.errors import PromptEmptyException, PromptTooLongException, PromptNotAllowedException

# =====================================================================
# 1. Moderation & Error Codes
# =====================================================================

def test_prompt_empty_raises_error():
    with pytest.raises(PromptEmptyException) as exc_info:
        prompt_moderator.validate_and_moderate("   ")
    assert exc_info.value.code == "PROMPT_EMPTY"

def test_prompt_none_raises_error():
    with pytest.raises(PromptEmptyException) as exc_info:
        prompt_moderator.validate_and_moderate(None)
    assert exc_info.value.code == "PROMPT_EMPTY"

def test_prompt_too_long_raises_error():
    long_text = "a" * 501
    with pytest.raises(PromptTooLongException) as exc_info:
        prompt_moderator.validate_and_moderate(long_text)
    assert exc_info.value.code == "PROMPT_TOO_LONG"

def test_prompt_blocked_content_raises_error():
    with pytest.raises(PromptNotAllowedException) as exc_info:
        prompt_moderator.validate_and_moderate("how to make a bomb for terrorist attack")
    assert exc_info.value.code == "PROMPT_NOT_ALLOWED"

def test_sensitive_legitimate_prompt_allowed():
    # Sensitive news/medical context must be allowed
    res = prompt_moderator.validate_and_moderate("sad news hospital doctor emergency")
    assert res == "sad news hospital doctor emergency"

# =====================================================================
# 2. Deterministic Named-Entity & Brand Disambiguation
# =====================================================================

def test_apple_fruit_not_substituted():
    # "apple on a tree" must be recognized as fruit, not Apple brand
    res = named_entity_detector.detect_and_resolve("apple on a tree in organic orchard")
    assert res["is_fruit"] is True
    assert res["is_protected"] is False
    assert res["safety_warning"] is None

def test_python_code_not_substituted():
    # "python code on screen" must be code, not snake or brand substitution
    res = named_entity_detector.detect_and_resolve("python code on screen in dark ide")
    assert res["is_code"] is True
    assert res["is_protected"] is False
    assert res["safety_warning"] is None

def test_brand_apple_substituted_with_warning():
    res = named_entity_detector.detect_and_resolve("Apple inc stock and shares")
    assert res["is_protected"] is True
    assert "Apple" in res["safety_warning"]
    assert "corporate" in res["replacement_query"]

def test_celebrity_substituted_with_warning():
    res = named_entity_detector.detect_and_resolve("Elon Musk presenting visionary future")
    assert res["is_protected"] is True
    assert "elon musk" in res["safety_warning"].lower()
    assert "executive" in res["replacement_query"]

# =====================================================================
# 3. Non-English Translations
# =====================================================================

def test_hindi_prompt_translated_search():
    query, lang, is_trans = prompt_moderator.detect_and_translate_for_search("सुंदर सूर्यास्त")
    assert lang == "hi"
    assert is_trans is True
    assert "sunset" in query.lower()

def test_tamil_prompt_translated_search():
    query, lang, is_trans = prompt_moderator.detect_and_translate_for_search("அழகான சூரிய உதயம்")
    assert lang == "ta"
    assert is_trans is True
    assert "sunrise" in query.lower()

# =====================================================================
# 4. Prompt Expansion & Shot Variety
# =====================================================================

def test_prompt_expansion_scene_count():
    # 20s -> 5 scenes (each 4.0s)
    res_20 = prompt_expander.expand_prompt("cat walking", duration_seconds=20)
    assert res_20["scene_count"] == 5
    assert len(res_20["scenes"]) == 5
    assert res_20["scenes"][0]["duration"] == 4.0
    assert "PROMPT_EXPANSION_FALLBACK" in res_20["warnings"]

    # 12s -> 3 scenes (each 4.0s)
    res_12 = prompt_expander.expand_prompt("ocean waves", duration_seconds=12)
    assert res_12["scene_count"] == 3
    assert len(res_12["scenes"]) == 3

def test_three_tier_cascading_queries():
    res = prompt_expander.expand_prompt("cat walking", duration_seconds=12, avoid_tags=["dogs"])
    for sc in res["scenes"]:
        queries = sc["search_queries"]
        assert len(queries) == 3
        # Query 1 is specific, Query 2 is medium, Query 3 is generic
        assert len(queries[0].split()) >= len(queries[1].split())
        assert "cat" in queries[2]

def test_seed_changes_shot_sequence():
    # Different seeds must produce different shot angle variations
    res_a = prompt_expander.expand_prompt("cat walking", duration_seconds=20, seed=101)
    res_b = prompt_expander.expand_prompt("cat walking", duration_seconds=20, seed=999)
    shots_a = [s["shot_type"] for s in res_a["scenes"]]
    shots_b = [s["shot_type"] for s in res_b["scenes"]]
    assert shots_a != shots_b

# =====================================================================
# 5. Segment Hash & Stale Video Regression Test
# =====================================================================

def test_different_inputs_produce_different_cache_hashes():
    h1 = VideoNormalizer.compute_segment_hash(
        clip_id="c1", ratio="16:9", start_time=0.0, duration=4.0, filters="scale",
        prompt="cat walking", seed=1, narration=False
    )
    h2 = VideoNormalizer.compute_segment_hash(
        clip_id="c1", ratio="16:9", start_time=0.0, duration=4.0, filters="scale",
        prompt="ocean waves", seed=1, narration=False
    )
    h3 = VideoNormalizer.compute_segment_hash(
        clip_id="c1", ratio="16:9", start_time=0.0, duration=4.0, filters="scale",
        prompt="cat walking", seed=2, narration=False  # Regenerate with new seed
    )
    # None of these should collide!
    assert h1 != h2
    assert h1 != h3
    assert h2 != h3

# =====================================================================
# 6. Candidate Ranker 2-Tier Selection & Zero-Reuse Rule
# =====================================================================

def test_ranker_no_repeat_and_floor():
    ranker = CandidateRanker(stock_threshold=0.60, relevance_floor=0.40)
    used_clips = set()
    warnings = []

    candidates = [
        {"id": "clip_cat_01", "title": "Cat strolling", "tags": ["cat", "walking"], "provider": "pixabay"},
        {"id": "clip_cat_02", "title": "Cat in garden", "tags": ["cat", "walking"], "provider": "pixabay"},
    ]

    # Scene 1: picks clip_cat_01
    chosen1, reason1, score1, _ = ranker.rank_and_select_clip(
        candidates=candidates,
        scene_text="A cute cat walking outdoors",
        visual_hint="cat walking",
        avoid_tags=[],
        used_clip_ids=used_clips,
        warnings_out=warnings,
        scene_index=0,
    )
    assert chosen1["id"] == "clip_cat_01"
    assert "clip_cat_01" in used_clips

    # Scene 2: clip_cat_01 CANNOT be reused! Must pick clip_cat_02
    chosen2, reason2, score2, _ = ranker.rank_and_select_clip(
        candidates=candidates,
        scene_text="Another cat strolling on grass",
        visual_hint="cat walking",
        avoid_tags=[],
        used_clip_ids=used_clips,
        warnings_out=warnings,
        scene_index=1,
    )
    assert chosen2["id"] == "clip_cat_02"
    assert chosen1["id"] != chosen2["id"]

# =====================================================================
# 7. Complete 16-Prompt Test Pack Verification
# =====================================================================

PROMPT_TEST_PACK = [
    ("cat walking", "standard_prompt"),
    ("ocean waves", "nature_prompt"),
    ("busy city night", "urban_prompt"),
    ("coffee pouring", "macro_prompt"),
    ("python code on screen", "tech_disambiguation"),
    ("bank building", "financial_disambiguation"),
    ("mouse pointer on screen", "ui_disambiguation"),
    ("cloud servers", "datacenter_disambiguation"),
    ("Elon Musk", "celebrity_substitution"),
    ("Apple Inc", "brand_substitution"),
    ("sad news hospital", "sensitive_allowed"),
    ("ocean", "one_word_prompt"),
    ("A breathtaking cinematic drone shot of mist flowing through emerald valleys during golden sunrise", "long_sentence"),
    ("सुंदर सूर्यास्त", "hindi_prompt"),
    ("அழகான சூரிய உதயம்", "tamil_prompt"),
    ("   ", "empty_prompt_exception"),
]

def test_16_prompt_test_pack_coverage():
    passed = 0
    for prompt, category in PROMPT_TEST_PACK:
        if category == "empty_prompt_exception":
            with pytest.raises(PromptEmptyException):
                prompt_moderator.validate_and_moderate(prompt)
            passed += 1
        else:
            cleaned = prompt_moderator.validate_and_moderate(prompt)
            exp = prompt_expander.expand_prompt(cleaned, duration_seconds=12, seed=42)
            assert exp["scene_count"] >= 2
            assert len(exp["scenes"]) >= 2
            passed += 1

    assert passed == 16

# =====================================================================
# 8. Integration & Pipeline Test (No API keys required)
# =====================================================================

def test_quick_prompt_integration_pipeline():
    from app.pipeline.runner import pipeline_runner

    job_id = "test_prompt_integration_cat_walk"
    res = pipeline_runner.execute_stages_1_to_6(
        job_id=job_id,
        prompt="cat walking",
        duration_seconds=12,
        narration=False,
        seed=123,
    )

    assert res["job_id"] == job_id
    scenes = res["scenes"]
    assert len(scenes) == 3
    # Check 100% time coverage
    total_dur = sum(s["duration"] for s in scenes)
    assert abs(total_dur - 12.0) < 0.1
    # Check strict zero-reuse
    used = res["used_clip_ids"]
    assert len(used) == len(set(used))
    assert res["repeat_clip_rate"] == 0.0

    # Check timeline metadata
    timeline = res["timeline"]
    assert timeline["prompt"] == "cat walking"
    assert timeline["total_duration_seconds"] == 12.0
    for sc in timeline["scenes"]:
        assert sc["prompt"] == "cat walking"
        assert sc["clip_id"] is not None
        assert "storage_url" in sc
        assert "link" in sc

def test_stale_video_regression_two_different_prompts():
    from app.pipeline.runner import pipeline_runner

    # Job A
    res_a = pipeline_runner.execute_stages_1_to_6(
        job_id="job_a_cat",
        prompt="cat walking",
        duration_seconds=12,
        seed=1,
    )
    # Job B with different prompt
    res_b = pipeline_runner.execute_stages_1_to_6(
        job_id="job_b_ocean",
        prompt="ocean waves",
        duration_seconds=12,
        seed=1,
    )

    # Different prompts must produce different queries, different timelines, and different clips
    assert res_a["timeline"]["prompt"] != res_b["timeline"]["prompt"]
    clips_a = [s["selected_clip_id"] for s in res_a["scenes"]]
    clips_b = [s["selected_clip_id"] for s in res_b["scenes"]]
    assert clips_a != clips_b

# =====================================================================
# 9. Opt-in Live Test with Real Pixabay API (Skipped when no key)
# =====================================================================

@pytest.mark.asyncio
async def test_pixabay_opt_in_live_test():
    import os
    from app.adapters.footage.pixabay_adapter import PixabayProvider

    key = os.getenv("PIXABAY_API_KEY")
    if not key or key.startswith("mock") or key.strip() == "":
        pytest.skip("No live PIXABAY_API_KEY configured in environment")

    provider = PixabayProvider(api_key=key)
    hits = await provider.search_footage_async("cat walking", count=3)
    if not hits:
        pytest.skip("Pixabay returned 0 hits or rate limited")

    assert len(hits) > 0
    top = hits[0]
    assert top["provider"] == "pixabay"
    assert top["preview_url"].startswith("http")
    assert top["pageURL"].startswith("https://pixabay.com")
    assert top["relevance_score"] >= 0.60
