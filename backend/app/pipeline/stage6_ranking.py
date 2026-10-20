import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from app.adapters.vision.mock_vision import MockVisionScorer
from app.adapters.footage.generative_adapter import GenerativeFootageAdapter
from app.config import settings

logger = logging.getLogger(__name__)

WATERMARK_KEYWORDS = {"watermark", "watermarked", "preview", "shutterstock", "getty", "pond5", "istock"}

class CandidateRanker:
    def __init__(
        self,
        stock_threshold: float = 0.28,
        vision_scorer=None,
    ):
        self.stock_threshold = stock_threshold
        self.vision_scorer = vision_scorer or MockVisionScorer()
        self.generative_fallback = GenerativeFootageAdapter()

    def rank_and_select_clip(
        self,
        candidates: List[Dict[str, Any]],
        scene_text: str,
        visual_hint: Optional[str],
        avoid_tags: Optional[List[str]],
        used_clip_ids: Set[str],
    ) -> Tuple[Dict[str, Any], str, float, str]:
        """
        Ranks candidates by semantic relevance, rejects watermarks/avoid tags,
        strictly enforces ZERO CLIP REUSE across all scenes in a video,
        applies the measurable selection threshold (>= 0.28 use stock, else generate),
        and records written reasoning.

        Returns:
            (selected_candidate, selection_reason, relevance_score, source_choice_reason)
        """
        avoid_set = {a.lower().strip() for a in (avoid_tags or [])}

        valid_scored_candidates = []
        for c in candidates:
            clip_id = c.get("id") or c.get("external_id")
            title_lower = c.get("title", "").lower()
            tags_lower = {t.lower() for t in c.get("tags", [])}

            # 1. Enforce STRICT NO-REPEAT rule: never reuse a clip
            if clip_id in used_clip_ids:
                logger.debug(f"Candidate {clip_id} rejected: already used in earlier scene (strict 0 reuse)")
                continue

            # 2. Reject Watermarked footage
            if any(wm in title_lower or wm in tags_lower for wm in WATERMARK_KEYWORDS):
                logger.debug(f"Candidate {clip_id} rejected: watermarked content detected")
                continue

            # 3. Enforce avoid rules
            if avoid_set and any(a in title_lower or a in tags_lower for a in avoid_set):
                logger.debug(f"Candidate {clip_id} rejected: matches avoid list '{avoid_set}'")
                continue

            # 4. Compute semantic relevance score (CLIP/SigLIP vision similarity)
            score = self.vision_scorer.score_relevance(
                candidate_meta=c,
                scene_text=scene_text,
                visual_hint=visual_hint,
            )
            c_copy = dict(c)
            c_copy["relevance_score"] = score
            valid_scored_candidates.append(c_copy)

        # Sort descending by relevance score
        valid_scored_candidates.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Apply measurable selection rule:
        # If best candidate relevance >= threshold, choose stock; else fall back to generative
        if valid_scored_candidates and valid_scored_candidates[0]["relevance_score"] >= self.stock_threshold:
            chosen = valid_scored_candidates[0]
            score = chosen["relevance_score"]
            clip_id = chosen.get("id") or chosen.get("external_id")
            used_clip_ids.add(clip_id)

            selection_reason = (
                f"Selected top candidate '{chosen.get('title')}' from provider '{chosen.get('provider')}' "
                f"with high semantic alignment (score: {score:.3f})."
            )
            source_choice_reason = (
                f"Stock footage chosen: highest semantic relevance ({score:.3f}) exceeds threshold ({self.stock_threshold})."
            )
            return chosen, selection_reason, score, source_choice_reason

        # Fallback to generative synthesis
        logger.info(f"Top candidate relevance below {self.stock_threshold}. Triggering generative fallback.")
        gen_candidates = self.generative_fallback.search_footage(query=scene_text[:30], count=1)
        gen_clip = gen_candidates[0]
        gen_clip["relevance_score"] = self.stock_threshold  # baseline
        clip_id = gen_clip["id"]
        used_clip_ids.add(clip_id)

        top_score = valid_scored_candidates[0]["relevance_score"] if valid_scored_candidates else 0.0
        selection_reason = (
            f"Generated custom AI visual motion card. Top stock candidate score ({top_score:.3f}) was below required threshold."
        )
        source_choice_reason = (
            f"Generative AI fallback chosen: stock footage relevance ({top_score:.3f}) was below threshold ({self.stock_threshold})."
        )
        return gen_clip, selection_reason, self.stock_threshold, source_choice_reason

candidate_ranker = CandidateRanker(
    stock_threshold=settings.STOCK_SELECTION_THRESHOLD
)
