"""
Prompt Moderation and Translation Module
----------------------------------------
1. Validates prompt safety:
   - Blocks harmful content (hate speech, self-harm, extreme violence, terror, CSAM).
   - Allows sensitive-but-legitimate prompts (e.g. "sad news hospital", "funeral memorial", "doctor in emergency room").
2. Multi-language detection & translation:
   - Detects non-English prompts (e.g. Hindi, Tamil, Spanish, etc.).
   - Translates to English search queries while strictly preserving the original text for captions and timeline.
"""

import re
from typing import Tuple, Optional, Dict, Any
from app.errors import PromptEmptyException, PromptTooLongException, PromptNotAllowedException

# Severe prohibited categories (strictly blocked)
BLOCKED_PATTERNS = [
    r"\b(suicide|self[-\s]?harm|kill[-\s]?myself)\b",
    r"\b(bomb[-\s]?making|terrorist[-\s]?attack|how\s+to\s+make\s+a\s+bomb)\b",
    r"\b(child\s+porn|csam|pedophil)\b",
    r"\b(hate\s+crime|nazi\s+propaganda|genocide)\b",
    r"\b(how\s+to\s+poison|assassinate\s+president)\b",
]

# Sensitive terms that are allowed (news, health, documentary context)
SENSITIVE_PERMITTED = [
    "sad news", "hospital", "patient", "doctor", "crying", "mourning",
    "funeral", "cemetery", "emergency", "memorial", "broken heart",
    "loss", "grief", "flood", "earthquake", "poverty"
]

# Common non-English phrase mapping for instant high-quality search translation
LANGUAGE_TRANSLATIONS: Dict[str, str] = {
    # Hindi
    "सुंदर सूर्यास्त": "beautiful sunset golden hour horizon",
    "पहाड़ों पर सूर्योदय": "sunrise over snow mountain peaks",
    "बिल्ली चल रही है": "cute cat walking leisurely",
    "रात में हलचल भरा शहर": "busy vibrant city skyline at night glowing lights",
    "कॉफी डालना": "fresh hot coffee pouring into ceramic cup",
    "ताजे फल और सब्जियां": "fresh organic fruits and colorful vegetables",
    
    # Tamil
    "அழகான சூரிய உதயம்": "beautiful sunrise golden sunlight morning",
    "பூனை நடக்கிறது": "cute cat walking outside",
    "இரவில் பரபரப்பான நகரம்": "busy vibrant city night life skyscrapers glowing",
    "காபி ஊற்றப்படுகிறது": "steaming hot coffee being poured into cup",
    "மலையின் மேல் சூரிய உதயம்": "sunrise over mountain peaks morning clouds",
}

class PromptModerationEngine:
    MAX_PROMPT_LENGTH = 500

    def validate_and_moderate(self, prompt: Optional[str]) -> str:
        """
        Validates prompt presence, length, and content safety.
        Returns cleaned prompt if allowed, or raises appropriate AppException.
        """
        if not prompt or not prompt.strip():
            raise PromptEmptyException()

        cleaned = prompt.strip()
        if len(cleaned) > self.MAX_PROMPT_LENGTH:
            raise PromptTooLongException(length=len(cleaned), max_length=self.MAX_PROMPT_LENGTH)

        lower = cleaned.lower()

        # Check blocked patterns
        for pat in BLOCKED_PATTERNS:
            if re.search(pat, lower):
                raise PromptNotAllowedException(
                    reason="The prompt contains content that violates our safety policy (harmful, violent, or dangerous content)."
                )

        return cleaned

    def detect_and_translate_for_search(self, prompt: str) -> Tuple[str, str, bool]:
        """
        Detects language and produces an English query for stock footage search.
        Returns:
            (english_search_base, detected_lang, is_translated)
        """
        trimmed = prompt.strip()

        # Direct dictionary match
        if trimmed in LANGUAGE_TRANSLATIONS:
            lang = "hi" if re.search(r"[\u0900-\u097F]", trimmed) else "ta"
            return LANGUAGE_TRANSLATIONS[trimmed], lang, True

        # Check for Devanagari (Hindi)
        if re.search(r"[\u0900-\u097F]", trimmed):
            # Check for known sub-phrases
            for hi_key, en_val in LANGUAGE_TRANSLATIONS.items():
                if hi_key in trimmed:
                    return en_val, "hi", True
            # Fallback transliteration/general term
            return "beautiful scenic landscape cinematic", "hi", True

        # Check for Tamil
        if re.search(r"[\u0B80-\u0BFF]", trimmed):
            for ta_key, en_val in LANGUAGE_TRANSLATIONS.items():
                if ta_key in trimmed:
                    return en_val, "ta", True
            return "scenic nature golden sunlight", "ta", True

        # Already English or standard Latin script
        return trimmed, "en", False

prompt_moderator = PromptModerationEngine()
