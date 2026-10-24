"""
Named Entity & Brand Safety Detector
------------------------------------
Detects protected individuals (celebrities, public figures) and commercial brand trademarks.
Ensures context-sensitive disambiguation so common words do not falsely trigger brand substitutions:
  - "apple on a tree" -> Real fruit, NOT the tech brand Apple.
  - "python code on screen" -> Software development, NOT a snake or brand substitution.
"""

import re
from typing import Dict, Any, List, Optional, Tuple

class NamedEntityDetector:
    # Public figures / celebrities (never show face or attempt synthetic biometrics)
    CELEBRITY_ENTITIES = {
        "elon musk": "executive tech entrepreneur speaking at modern conference",
        "steve jobs": "charismatic tech innovator presenting product on stage",
        "bill gates": "philanthropist and executive in modern office discussion",
        "mark zuckerberg": "tech executive working in modern open-plan office",
        "jeff bezos": "business corporate leader walking through modern warehouse facility",
        "sam altman": "artificial intelligence researcher in high-tech laboratory",
        "tim cook": "corporate executive speaking at tech keynote event",
        "sundar pichai": "technology leader reviewing cloud infrastructure on screen",
    }

    # Brand names with contextual exclusions
    BRAND_CONTEXT_RULES = {
        "apple": {
            "fruit_indicators": [
                "tree", "orchard", "fruit", "pie", "eat", "eating", "bite", "red", "green",
                "cider", "juice", "fresh", "branch", "harvest", "crisp", "basket", "seed"
            ],
            "brand_indicators": [
                "inc", "corp", "iphone", "mac", "ipad", "store", "stock", "shares", "tim cook",
                "steve jobs", "cupertino", "silicon valley", "tech giant", "gadget", "device"
            ],
            "brand_replacement": "modern corporate tech headquarters glass architecture employees",
            "fruit_query": "ripe fresh organic apples hanging on tree branch in orchard",
        },
        "python": {
            "code_indicators": [
                "code", "coding", "script", "program", "programming", "developer", "ide",
                "software", "screen", "terminal", "algorithm", "syntax", "editor", "backend", "api"
            ],
            "animal_indicators": [
                "snake", "reptile", "slithering", "rainforest", "jungle", "zoo", "wild", "forest"
            ],
            "code_query": "programmer typing python code in dark modern ide screen close up",
            "animal_query": "python snake moving slowly through lush green tropical grass",
        },
        "tesla": {
            "coil_indicators": ["coil", "nikola", "electricity", "lightning", "physics"],
            "brand_replacement": "modern electric vehicle driving on scenic highway clean energy",
        },
        "google": {
            "brand_replacement": "modern colorful technology campus office employees collaborating",
        },
        "microsoft": {
            "brand_replacement": "sleek glass corporate technology headquarters and data systems",
        },
        "nike": {
            "brand_replacement": "athletic runner jogging in sunrise morning athletic sportswear shoes",
        },
        "coca-cola": {
            "brand_replacement": "refreshing cold sparkling beverage with ice cubes and splash",
        },
    }

    def detect_and_resolve(self, text: str) -> Dict[str, Any]:
        """
        Analyzes text for protected entities, celebrities, and commercial brands.
        Returns:
            {
                "is_protected": bool,
                "entity_name": Optional[str],
                "replacement_query": Optional[str],
                "safety_warning": Optional[str],
                "is_fruit": bool,
                "is_code": bool,
            }
        """
        text_lower = text.lower()
        words = set(re.findall(r"\b[a-z0-9_-]+\b", text_lower))

        # 1. Celebrity / Public Figure check
        for celeb, replacement in self.CELEBRITY_ENTITIES.items():
            if celeb in text_lower:
                return {
                    "is_protected": True,
                    "entity_name": celeb,
                    "replacement_query": replacement,
                    "safety_warning": f"Mentioned protected entity '{celeb}'. Broll Studio Safety: Biometric face generation blocked; selecting generic industry leadership footage.",
                    "is_fruit": False,
                    "is_code": False,
                }

        # 2. Context-Sensitive Brand Checks
        # Special check: "apple"
        if "apple" in words or "apples" in words:
            fruit_clues = any(w in words for w in self.BRAND_CONTEXT_RULES["apple"]["fruit_indicators"])
            brand_clues = any(w in words for w in self.BRAND_CONTEXT_RULES["apple"]["brand_indicators"])

            if fruit_clues and not brand_clues:
                # Definite fruit, NOT the brand!
                return {
                    "is_protected": False,
                    "entity_name": None,
                    "replacement_query": self.BRAND_CONTEXT_RULES["apple"]["fruit_query"],
                    "safety_warning": None,
                    "is_fruit": True,
                    "is_code": False,
                }
            elif brand_clues:
                # Definite brand
                return {
                    "is_protected": True,
                    "entity_name": "apple",
                    "replacement_query": self.BRAND_CONTEXT_RULES["apple"]["brand_replacement"],
                    "safety_warning": "Mentioned commercial brand 'Apple'. Broll Studio Compliance: Trademark generation blocked; selecting generic corporate technology footage.",
                    "is_fruit": False,
                    "is_code": False,
                }
            else:
                # Standalone "apple": check if prompt implies technology or generic
                return {
                    "is_protected": True,
                    "entity_name": "apple",
                    "replacement_query": self.BRAND_CONTEXT_RULES["apple"]["brand_replacement"],
                    "safety_warning": "Mentioned commercial brand 'Apple'. Broll Studio Compliance: Trademark generation blocked; selecting generic corporate technology footage.",
                    "is_fruit": False,
                    "is_code": False,
                }

        # Special check: "python"
        if "python" in words:
            code_clues = any(w in words for w in self.BRAND_CONTEXT_RULES["python"]["code_indicators"])
            animal_clues = any(w in words for w in self.BRAND_CONTEXT_RULES["python"]["animal_indicators"])

            if code_clues or not animal_clues:
                # Code on screen
                return {
                    "is_protected": False,
                    "entity_name": None,
                    "replacement_query": self.BRAND_CONTEXT_RULES["python"]["code_query"],
                    "safety_warning": None,
                    "is_fruit": False,
                    "is_code": True,
                }
            else:
                # Snake
                return {
                    "is_protected": False,
                    "entity_name": None,
                    "replacement_query": self.BRAND_CONTEXT_RULES["python"]["animal_query"],
                    "safety_warning": None,
                    "is_fruit": False,
                    "is_code": False,
                }

        # Check other brands
        for brand, rule in self.BRAND_CONTEXT_RULES.items():
            if brand in ["apple", "python"]:
                continue
            if brand in text_lower:
                return {
                    "is_protected": True,
                    "entity_name": brand,
                    "replacement_query": rule.get("brand_replacement"),
                    "safety_warning": f"Mentioned commercial brand '{brand}'. Broll Studio Compliance: Trademark generation blocked; selecting generic clean footage.",
                    "is_fruit": False,
                    "is_code": False,
                }

        return {
            "is_protected": False,
            "entity_name": None,
            "replacement_query": None,
            "safety_warning": None,
            "is_fruit": False,
            "is_code": False,
        }

named_entity_detector = NamedEntityDetector()
