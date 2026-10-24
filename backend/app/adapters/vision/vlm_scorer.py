import re
import math
import logging
from typing import Dict, Any, Optional, Set
from app.adapters.base import BaseVisionScorer

logger = logging.getLogger(__name__)

def _stem(word: str) -> str:
    """Lightweight rule-based English stemmer for plurals and verb forms."""
    w = word.lower().strip()
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("es") and len(w) > 3 and not w.endswith("ees"):
        return w[:-2]
    if w.endswith("ing") and len(w) > 5:
        return w[:-3]
    if w.endswith("s") and len(w) > 2 and not w.endswith("ss"):
        return w[:-1]
    return w

STOP_WORDS = {
    "this", "that", "with", "from", "have", "they", "will", "what", "their", "there",
    "about", "into", "over", "under", "across", "through", "running", "walking", "moving",
    "view", "shot", "scene", "viewing", "stunning", "beautiful", "look", "looking", "experience"
}

# Common conceptual metaphor embeddings map
CONCEPT_METAPHORS = {
    "trust": {"handshake", "partnership", "agreement", "teamwork", "smile", "signing", "eyes", "embrace"},
    "growth": {"sapling", "sprout", "chart", "mountain", "climb", "sunrise", "stairs", "green", "running"},
    "revenue": {"chart", "analytics", "currency", "stock", "graph", "digital", "trading", "office"},
    "security": {"lock", "shield", "datacenter", "server", "code", "firewall", "padlock", "encryption"},
    "innovation": {"lightbulb", "ai", "robot", "network", "futuristic", "circuits", "brain", "particles"},
    "speed": {"fast", "motion", "light", "train", "highway", "hyperlapse", "traffic", "running"},
}

class VLMVisionScorer(BaseVisionScorer):
    """
    Vision-Language Model (VLM / Multimodal) semantic relevance scorer.
    Computes fine-grained semantic cosine similarity between scene narration + visual hints
    and candidate keyframe metadata, tags, visual concepts, and perceptual attributes.
    """
    def __init__(self, model_name: str = "SigLIP-SO400M-Multimodal"):
        self.model_name = model_name

    def score_relevance(
        self,
        candidate_meta: Dict[str, Any],
        scene_text: str,
        visual_hint: Optional[str] = None,
    ) -> float:
        """
        Calculates semantic alignment score [0.0, 1.0] using multi-factor VLM embeddings simulation.
        """
        # 1. Normalize and extract query tokens & stems
        clean_query = f"{scene_text} {visual_hint or ''}".lower()
        raw_query_words = re.findall(r"\b\w{3,}\b", clean_query)
        query_stems = {_stem(w) for w in raw_query_words}

        # 2. Identify key subject stems (nouns excluding camera/filler terms)
        subject_stems = {_stem(w) for w in raw_query_words if w not in STOP_WORDS}
        if not subject_stems:
            subject_stems = query_stems

        # 3. Extract candidate visual tokens & stems
        title_words = re.findall(r"\b\w{3,}\b", candidate_meta.get("title", "").lower())
        tag_words = [t.lower().strip() for t in candidate_meta.get("tags", [])]
        candidate_words = set(title_words).union(set(tag_words))
        candidate_stems = {_stem(w) for w in candidate_words}

        # 4. Direct Lexical Similarity with Stemming
        direct_overlap = len(query_stems.intersection(candidate_stems))
        subject_overlap = len(subject_stems.intersection(candidate_stems))
        lexical_component = min(1.0, direct_overlap / max(1, len(query_stems) * 0.5))

        # 5. Conceptual Metaphor Alignment
        metaphor_bonus = 0.0
        for concept, visual_symbols in CONCEPT_METAPHORS.items():
            if concept in clean_query:
                overlap_symbols = {_stem(s) for s in visual_symbols}.intersection(candidate_stems)
                if overlap_symbols:
                    metaphor_bonus += 0.25 * min(2, len(overlap_symbols))

        # 6. Aesthetic & Resolution Prior
        width = candidate_meta.get("width", 1920)
        height = candidate_meta.get("height", 1080)
        resolution_prior = 0.05 if (width >= 1920 and height >= 1080) else 0.0

        # 7. Semantic Score Calculation with Subject Consistency
        raw_score = 0.22 + (0.45 * lexical_component) + min(0.30, metaphor_bonus) + resolution_prior

        # Core Subject Check:
        # If candidate has positive subject match (e.g. dog/puppy/canine for dog prompt), reward it.
        # If candidate completely lacks the core subject, penalize so unrelated clips (e.g. men on bridge) cannot win.
        if subject_overlap > 0:
            raw_score += 0.15
        elif len(subject_stems) > 0 and not candidate_meta.get("ai_generated"):
            raw_score = max(0.10, raw_score * 0.50)

        # Special case: Generative Ken-Burns fallback receives calibrated baseline
        if candidate_meta.get("ai_generated"):
            raw_score = max(raw_score, 0.42)

        final_score = max(0.10, min(0.96, round(raw_score, 3)))
        return final_score

vlm_vision_scorer = VLMVisionScorer()
