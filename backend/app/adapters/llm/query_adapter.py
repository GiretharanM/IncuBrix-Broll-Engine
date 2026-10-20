import re
import logging
from typing import Dict, Any, Optional, List
from app.adapters.base import BaseLLMAdapter
from app.config import settings

logger = logging.getLogger(__name__)

class QueryUnderstandingAdapter(BaseLLMAdapter):
    # Context-aware disambiguation dictionary
    POLYSEMOUS_DISAMBIGUATION = {
        "bank": {
            "financial_keywords": ["money", "account", "finance", "deposit", "loan", "investment", "cash", "interest"],
            "financial_query": "modern banking counter financial transaction money",
            "river_query": "natural river bank flowing clear water green landscape",
        },
        "cloud": {
            "tech_keywords": ["server", "storage", "computing", "software", "aws", "data", "deploy", "sync", "backup"],
            "tech_query": "data center server room glowing blue lights digital infrastructure",
            "weather_query": "cinematic timelapse white clouds moving across blue sky",
        },
        "python": {
            "tech_keywords": ["code", "software", "program", "developer", "script", "backend", "api", "data science"],
            "tech_query": "programmer writing clean code in dark modern IDE workspace",
            "animal_query": "wild snake crawling through tropical green rainforest",
        },
        "mouse": {
            "tech_keywords": ["click", "computer", "desk", "screen", "keyboard", "pointer", "ui"],
            "tech_query": "hand using ergonomic computer mouse on modern clean desk",
            "animal_query": "small field mouse in nature grass",
        },
        "value": {
            "business_keywords": ["shareholder", "company", "stock", "growth", "revenue", "worth", "enterprise"],
            "business_query": "financial growth chart stock market trends arrow rising",
            "general_query": "high quality craftsmanship premium precision details",
        },
    }

    # Metaphors for abstract, non-literal sentiments
    ABSTRACT_METAPHORS = {
        r"\btrust\b": "two business partners shaking hands in sunny corporate boardroom",
        r"\bhard work\b|\beffort\b": "dedicated craftsman shaping wood in workshop close up",
        r"\btransparency\b": "clean crystal clear water flowing over pebbles morning light",
        r"\btime flies\b|\bpassage of time\b": "golden sand flowing through antique glass hourglass",
        r"\bfuture\b|\binnovation\b": "modern smart city architecture with glowing light trails at dusk",
        r"\bgrowth\b|\bprogress\b": "small green sprout growing out of rich dark earth timelapse",
        r"\bslowly\b": "timelapse sunrise over calm mountain horizon",
        r"\bspeed\b|\bfast\b": "high speed train speeding through city lights at night",
    }

    # Protected entities: Celebrities, public figures, commercial brand trademarks
    PROTECTED_ENTITIES = [
        "elon musk", "steve jobs", "bill gates", "mark zuckerberg", "satya nadella",
        "jeff bezos", "sam altman", "tim cook", "sundar pichai",
        "apple", "google", "microsoft", "tesla", "amazon", "meta", "nvidia",
        "intel", "coca-cola", "nike", "disney", "netflix"
    ]

    def understand_scene(self, scene_text: str, visual_hint: Optional[str] = None) -> Dict[str, Any]:
        text_lower = scene_text.lower()
        warnings: List[str] = []
        metaphors_found: List[str] = []
        is_statistic = False
        contains_protected = False

        # 1. Protected Entity & Brand Trademark Check
        # Rule: NEVER generate face/logo. Use generic alternative footage and issue warning.
        generic_entity_replacement = None
        for entity in self.PROTECTED_ENTITIES:
            if entity in text_lower:
                contains_protected = True
                warnings.append(
                    f"Mentioned protected entity '{entity}'. IncuBrix Compliance: Biometric and trademark generation blocked; selecting generic industry footage."
                )
                if entity in ["apple", "google", "microsoft", "meta", "amazon"]:
                    generic_entity_replacement = "modern corporate tech headquarters glass facade employees"
                elif entity in ["tesla", "elon musk"]:
                    generic_entity_replacement = "electric vehicle charging modern clean transportation technology"
                elif entity in ["nvidia", "intel"]:
                    generic_entity_replacement = "computer silicon microchip processor circuit board glowing"
                else:
                    generic_entity_replacement = "executive business leader presenting in conference room"

        # 2. Number and Statistic Detection
        stat_patterns = [
            r"\b\d+([.,]\d+)?\s*%",
            r"\b\d+([.,]\d+)?\s*(percent|billion|million|trillion|thousand)",
            r"\$\s*\d+([.,]\d+)?",
            r"\b(ratio|percentage|statistic|survey|metrics)\b",
        ]
        if any(re.search(pat, text_lower) for pat in stat_patterns):
            is_statistic = True

        # 3. Contextual Ambiguity Resolution (bank, cloud, mouse, python, value)
        disambiguated_query = None
        for term, mapping in self.POLYSEMOUS_DISAMBIGUATION.items():
            pattern = rf"\b{term}s?\b" if term != "mouse" else r"\b(mouse|mice)\b"
            if re.search(pattern, text_lower):
                # Look for context clues
                context_match = False
                for key_term in mapping.get("tech_keywords", []) + mapping.get("financial_keywords", []) + mapping.get("business_keywords", []):
                    if key_term in text_lower:
                        context_match = True
                        break

                if "tech_query" in mapping:
                    disambiguated_query = mapping["tech_query"] if context_match else mapping.get("weather_query") or mapping.get("animal_query")
                elif "financial_query" in mapping:
                    disambiguated_query = mapping["financial_query"] if context_match else mapping["river_query"]
                elif "business_query" in mapping:
                    disambiguated_query = mapping["business_query"] if context_match else mapping["general_query"]
                break

        # 4. Abstract Metaphor Resolution
        for pattern, metaphor in self.ABSTRACT_METAPHORS.items():
            if re.search(pattern, text_lower):
                metaphors_found.append(metaphor)

        # 5. Build Final Visual Query
        if visual_hint:
            final_query = f"{visual_hint} {scene_text[:40]}"
        elif contains_protected and generic_entity_replacement:
            final_query = generic_entity_replacement
        elif is_statistic:
            final_query = "digital data analytics screen glowing motion charts graphs"
        elif disambiguated_query:
            final_query = disambiguated_query
        elif metaphors_found:
            final_query = metaphors_found[0]
        else:
            # Clean descriptive keywords
            cleaned_words = [
                w for w in re.findall(r"\b[a-zA-Z]{4,}\b", text_lower)
                if w not in {"this", "that", "with", "from", "have", "they", "will", "what", "their", "there", "about"}
            ]
            final_query = " ".join(cleaned_words[:4]) or "modern creative workspace technology"

        return {
            "search_query": final_query.strip(),
            "metaphors": metaphors_found,
            "contains_brand_or_person": contains_protected,
            "is_statistic": is_statistic,
            "safety_warning": "; ".join(warnings) if warnings else None,
        }

query_understanding_adapter = QueryUnderstandingAdapter()
