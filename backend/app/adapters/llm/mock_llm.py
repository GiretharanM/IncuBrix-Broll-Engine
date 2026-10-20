import re
from typing import Dict, Any, Optional, List
from app.adapters.base import BaseLLMAdapter

class MockLLMAdapter(BaseLLMAdapter):
    # Ambiguous keyword mapping
    AMBIGUOUS_TERMS = {
        "bank": "finance river bank or financial institution",
        "cloud": "cloud computing server rack infrastructure data",
        "mouse": "computer mouse clicking desktop workspace",
        "python": "software programming code terminal screen",
        "value": "business growth stock market chart quality",
        "apple": "technology device smartphone or fresh red orchard apple",
    }

    # Metaphor mapping for abstract expressions
    METAPHORS = {
        "trust": "business partners shaking hands in modern sunlit office",
        "hard work": "craftsman working diligently at workbench timelapse",
        "time flies": "hourglass sand flowing slow motion clock gears",
        "future": "futuristic smart city skyline glowing light trails",
        "growth": "green sapling growing through fertile soil sunrise",
    }

    # Brand and celebrity detection list
    KNOWN_ENTITIES = [
        "elon musk", "steve jobs", "bill gates", "mark zuckerberg", "satya nadella",
        "apple", "google", "microsoft", "tesla", "amazon", "meta", "nvidia"
    ]

    def understand_scene(self, scene_text: str, visual_hint: Optional[str] = None) -> Dict[str, Any]:
        text_lower = scene_text.lower()
        warnings: List[str] = []
        is_stat = bool(re.search(r"\b\d+([.,]\d+)?%?\b|percent|ratio|billion|million", text_lower))
        contains_entity = False

        # 1. Entity and Brand Safety check
        for entity in self.KNOWN_ENTITIES:
            if entity in text_lower:
                contains_entity = True
                warnings.append(
                    f"Mentioned brand or public figure '{entity}'. Policy: generic alternative footage selected; no biometric or trademark reproduction."
                )

        # 2. Metaphor or Abstract mapping
        metaphor_chosen = None
        for key, metaphor in self.METAPHORS.items():
            if key in text_lower:
                metaphor_chosen = metaphor
                break

        # 3. Disambiguation
        disambiguated = None
        for term, replacement in self.AMBIGUOUS_TERMS.items():
            if re.search(rf"\b{term}\b", text_lower):
                disambiguated = replacement
                break

        # 4. Construct Search Query
        if visual_hint:
            query = f"{visual_hint} {scene_text[:50]}"
        elif metaphor_chosen:
            query = metaphor_chosen
        elif is_stat:
            query = "data visualization digital graph analytics screen motion"
        elif disambiguated:
            query = disambiguated
        else:
            # Clean words, take top meaningful nouns
            clean_words = [w for w in re.findall(r"\b[a-zA-Z]{4,}\b", text_lower) if w not in {"this", "that", "with", "from", "have", "they", "will"}]
            query = " ".join(clean_words[:4]) or "modern creative workspace technology"

        return {
            "search_query": query.strip(),
            "metaphors": [metaphor_chosen] if metaphor_chosen else [],
            "contains_brand_or_person": contains_entity,
            "is_statistic": is_stat,
            "safety_warning": "; ".join(warnings) if warnings else None,
        }
