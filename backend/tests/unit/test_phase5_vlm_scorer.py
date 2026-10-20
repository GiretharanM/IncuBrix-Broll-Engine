import pytest
from app.adapters.vision.vlm_scorer import VLMVisionScorer
from app.adapters.footage.generative_adapter import GenerativeFootageAdapter
from app.pipeline.stage6_ranking import CandidateRanker

class TestVLMVisionScorer:
    def setup_method(self):
        self.scorer = VLMVisionScorer()

    def test_direct_lexical_alignment(self):
        candidate = {
            "title": "Business partners shaking hands in boardroom",
            "tags": ["business", "handshake", "agreement", "corporate"],
            "width": 1920,
            "height": 1080,
        }
        score = self.scorer.score_relevance(
            candidate_meta=candidate,
            scene_text="Trust and integrity in corporate agreements",
            visual_hint="business handshake",
        )
        assert score >= 0.70

    def test_conceptual_metaphor_boost(self):
        # Candidate with visual metaphor symbols (handshake for trust)
        candidate_metaphor = {
            "title": "Two people shaking hands warmly",
            "tags": ["handshake", "partnership", "agreement"],
            "width": 1920,
            "height": 1080,
        }
        # Irrelevant candidate
        candidate_irrelevant = {
            "title": "Street cars speeding on rainy highway",
            "tags": ["traffic", "cars", "asphalt"],
            "width": 1920,
            "height": 1080,
        }

        score_metaphor = self.scorer.score_relevance(
            candidate_meta=candidate_metaphor,
            scene_text="Trust is earned slowly over time.",
        )
        score_irrelevant = self.scorer.score_relevance(
            candidate_meta=candidate_irrelevant,
            scene_text="Trust is earned slowly over time.",
        )

        assert score_metaphor > score_irrelevant
        assert score_metaphor >= 0.45

    def test_generative_ai_candidate_scoring(self):
        gen_clip = {
            "title": "Generative Ken-Burns motion across futuristic grid",
            "tags": ["generative", "ai", "kenburns"],
            "ai_generated": True,
            "width": 1920,
            "height": 1080,
        }
        score = self.scorer.score_relevance(
            candidate_meta=gen_clip,
            scene_text="Future neural quantum network.",
        )
        assert score >= 0.42

class TestGenerativeSelectionRule:
    def test_stock_selected_when_relevance_above_threshold(self):
        ranker = CandidateRanker(stock_threshold=0.28)
        candidates = [{
            "id": "stock_01",
            "provider": "pexels",
            "title": "Software engineers analyzing terminal code",
            "tags": ["code", "software", "terminal"],
            "width": 1920,
            "height": 1080,
        }]

        chosen, reason, score, source_choice = ranker.rank_and_select_clip(
            candidates=candidates,
            scene_text="Software developers writing robust code",
            visual_hint="coding terminal",
            avoid_tags=[],
            used_clip_ids=set(),
        )

        assert chosen["id"] == "stock_01"
        assert score >= 0.28
        assert "Stock footage chosen" in source_choice
        assert chosen.get("ai_generated") is not True

    def test_generative_selected_when_candidates_below_threshold(self):
        ranker = CandidateRanker(stock_threshold=0.85)  # Artificially high threshold
        candidates = [{
            "id": "low_stock_01",
            "provider": "pixabay",
            "title": "Random blurry object in distant sky",
            "tags": ["blur", "sky"],
            "width": 1280,
            "height": 720,
        }]

        chosen, reason, score, source_choice = ranker.rank_and_select_clip(
            candidates=candidates,
            scene_text="Deep ocean submarine expedition exploration",
            visual_hint="submersible deep water",
            avoid_tags=[],
            used_clip_ids=set(),
        )

        assert chosen["ai_generated"] is True
        assert chosen["provider"] == "generative"
        assert "Generative AI fallback" in source_choice
