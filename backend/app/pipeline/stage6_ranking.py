import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from app.adapters.vision.vlm_scorer import VLMVisionScorer
from app.adapters.footage.generative_adapter import GenerativeFootageAdapter
from app.config import settings

logger = logging.getLogger(__name__)

WATERMARK_KEYWORDS = {"watermark", "watermarked", "preview", "shutterstock", "getty", "pond5", "istock"}

class CandidateRanker:
    def __init__(
        self,
        stock_threshold: float = 0.60,
        relevance_floor: float = 0.40,
        vision_scorer=None,
    ):
        self.stock_threshold = stock_threshold
        self.relevance_floor = relevance_floor
        self.vision_scorer = vision_scorer or VLMVisionScorer()
        self.generative_fallback = GenerativeFootageAdapter()

    def rank_and_select_clip(
        self,
        candidates: List[Dict[str, Any]],
        scene_text: str,
        visual_hint: Optional[str],
        avoid_tags: Optional[List[str]],
        used_clip_ids: Set[str],
        warnings_out: Optional[List[str]] = None,
        scene_index: int = 0,
        queries_tried: Optional[List[str]] = None,
    ) -> Tuple[Dict[str, Any], str, float, str]:
        """
        Ranks candidates by semantic relevance, rejects watermarks/avoid tags,
        strictly enforces ZERO CLIP REUSE across all scenes in a video,
        and applies the 2-tier selection rule:
          1. score >= stock_threshold: High confidence stock clip chosen.
          2. relevance_floor <= score < stock_threshold: Chosen as best effort with warning.
          3. score < relevance_floor or empty: Neutral fallback card deployed with warning naming queries tried.
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

        # Tier 1: Candidate clears primary stock threshold
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

        # Tier 2: Candidate clears lower relevance floor (best-effort with warning)
        if valid_scored_candidates and valid_scored_candidates[0]["relevance_score"] >= self.relevance_floor:
            chosen = valid_scored_candidates[0]
            score = chosen["relevance_score"]
            clip_id = chosen.get("id") or chosen.get("external_id")
            used_clip_ids.add(clip_id)

            warn_msg = (
                f"BELOW_THRESHOLD_BEST_EFFORT: Scene {scene_index + 1} chosen candidate '{chosen.get('title')}' "
                f"(score {score:.3f}) is below standard threshold {self.stock_threshold:.2f}."
            )
            if warnings_out is not None:
                warnings_out.append(warn_msg)

            selection_reason = (
                f"Selected best-effort candidate '{chosen.get('title')}' clearing minimum relevance floor (score: {score:.3f})."
            )
            source_choice_reason = (
                f"Best-effort stock footage chosen: relevance ({score:.3f}) meets floor ({self.relevance_floor})."
            )
            return chosen, selection_reason, score, source_choice_reason

        # Tier 3: Below floor or no candidates -> Neutral fallback card
        top_score = valid_scored_candidates[0]["relevance_score"] if valid_scored_candidates else 0.0
        queries_str = ", ".join(f"'{q}'" for q in (queries_tried or [scene_text[:30]]))
        fallback_msg = (
            f"NO_RELEVANT_FOOTAGE_FALLBACK: Scene {scene_index + 1} could not find relevant footage exceeding floor "
            f"{self.relevance_floor:.2f} across queries [{queries_str}]. Using neutral fallback card."
        )
        if warnings_out is not None:
            warnings_out.append(fallback_msg)

        logger.info(fallback_msg)
        gen_candidates = self.generative_fallback.search_footage(query=scene_text[:30], count=1)
        gen_clip = gen_candidates[0]
        gen_clip["relevance_score"] = self.relevance_floor
        clip_id = gen_clip["id"]
        used_clip_ids.add(clip_id)

        selection_reason = (
            f"Neutral visual fallback card deployed. Top candidate score ({top_score:.3f}) failed minimum relevance floor ({self.relevance_floor})."
        )
        source_choice_reason = (
            f"Neutral fallback deployed: no footage cleared relevance floor ({self.relevance_floor}) for queries [{queries_str}]."
        )
        return gen_clip, selection_reason, self.relevance_floor, source_choice_reason

candidate_ranker = CandidateRanker(
    stock_threshold=settings.STOCK_SELECTION_THRESHOLD,
    relevance_floor=0.40,
)
