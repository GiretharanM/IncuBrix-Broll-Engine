from typing import Dict, Any, Optional
from app.adapters.base import BaseVisionScorer

class MockVisionScorer(BaseVisionScorer):
    def score_relevance(self, candidate_meta: Dict[str, Any], scene_text: str, visual_hint: Optional[str] = None) -> float:
        """
        Deterministic mock semantic scoring simulating CLIP / SigLIP cosine similarity.
        Base cosine score + bonus for keyword alignment.
        """
        text_tokens = set(scene_text.lower().split())
        if visual_hint:
            text_tokens.update(visual_hint.lower().split())

        tags = set(candidate_meta.get("tags", []))
        title_tokens = set(candidate_meta.get("title", "").lower().split())

        overlap = len(text_tokens.intersection(tags.union(title_tokens)))
        # Base realistic CLIP score between 0.22 and 0.88
        base_score = 0.25 + (0.12 * overlap)
        return min(0.92, round(base_score, 3))
