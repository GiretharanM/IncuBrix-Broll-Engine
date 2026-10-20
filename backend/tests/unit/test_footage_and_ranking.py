import pytest
from app.pipeline.stage5_retrieval import FootageRetrievalEngine
from app.pipeline.stage6_ranking import CandidateRanker
from app.adapters.vision.mock_vision import MockVisionScorer

def test_footage_retrieval_cascading():
    engine = FootageRetrievalEngine()
    warnings = []

    # Should successfully retrieve candidates from mock catalog
    candidates = engine.retrieve_candidates_for_scene(
        query="data center server rack",
        avoid=[],
        count=3,
        warnings_out=warnings,
    )
    assert len(candidates) > 0
    assert candidates[0]["licence_name"] is not None

def test_watermark_rejection():
    ranker = CandidateRanker(stock_threshold=0.28)
    used_clips = set()

    candidates = [
        {
            "id": "clip_wm_01",
            "title": "Corporate meeting Shutterstock watermark preview",
            "tags": ["business", "watermark"],
            "provider": "mock",
        },
        {
            "id": "clip_clean_02",
            "title": "Corporate meeting handshake clean license",
            "tags": ["business", "handshake"],
            "provider": "mock",
        }
    ]

    selected, reason, score, src_reason = ranker.rank_and_select_clip(
        candidates=candidates,
        scene_text="Business agreement signed",
        visual_hint="business meeting",
        avoid_tags=[],
        used_clip_ids=used_clips,
    )

    # Watermarked clip must be rejected
    assert selected["id"] == "clip_clean_02"
    assert "clip_wm_01" not in used_clips

def test_strict_zero_clip_reuse_across_scenes():
    ranker = CandidateRanker(stock_threshold=0.28)
    used_clips = set()

    # Three identical scenes query the same candidate pool
    candidate_pool = [
        {"id": "clip_A", "title": "Developer typing code terminal", "tags": ["code", "developer", "technology"], "provider": "mock"},
        {"id": "clip_B", "title": "Server rack datacenter", "tags": ["server", "datacenter", "technology"], "provider": "mock"},
        {"id": "clip_C", "title": "Cloud network infrastructure", "tags": ["cloud", "infrastructure", "technology"], "provider": "mock"},
    ]

    selected_ids = []
    for i in range(3):
        selected, reason, score, src_reason = ranker.rank_and_select_clip(
            candidates=candidate_pool,
            scene_text="Technology code and server infrastructure",
            visual_hint=None,
            avoid_tags=[],
            used_clip_ids=used_clips,
        )
        selected_ids.append(selected["id"])

    # Strict rule: NO CLIP REUSED in a video
    assert len(selected_ids) == 3
    assert len(set(selected_ids)) == 3, f"Duplicate clip found in: {selected_ids}"
    assert "clip_A" in selected_ids
    assert "clip_B" in selected_ids
    assert "clip_C" in selected_ids

def test_selection_threshold_stock_vs_generative():
    # Vision scorer that returns a score below 0.28
    class LowScoreVisionScorer:
        def score_relevance(self, candidate_meta, scene_text, visual_hint=None):
            return 0.15  # Below threshold 0.28

    ranker_low = CandidateRanker(stock_threshold=0.28, vision_scorer=LowScoreVisionScorer())
    used_clips = set()

    candidates = [
        {"id": "poor_match_01", "title": "Irrelevant clip of desert sand", "tags": ["desert"], "provider": "mock"}
    ]

    selected, reason, score, src_reason = ranker_low.rank_and_select_clip(
        candidates=candidates,
        scene_text="High performance microchip semiconductor fabrication",
        visual_hint=None,
        avoid_tags=[],
        used_clip_ids=used_clips,
    )

    # Must fall back to generative AI because 0.15 < 0.28
    assert selected["ai_generated"] is True
    assert "Generative AI fallback chosen" in src_reason
    assert "below threshold (0.28)" in src_reason
