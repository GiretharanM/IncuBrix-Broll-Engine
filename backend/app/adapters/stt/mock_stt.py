import os
import re
from typing import Dict, Any, List
from app.adapters.base import BaseSTTAdapter

class MockSTTAdapter(BaseSTTAdapter):
    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Deterministic mock STT: generates realistic word-level timestamps.
        If a transcript text is encoded or defaults to standard text, creates accurate timing.
        """
        # In a mock scenario, we provide a clean sentence structure
        default_sentence = (
            "Welcome to IncuBrix B-roll Engine. "
            "Trust is earned slowly and lost in a flash. "
            "Over seventy percent of global digital workflows rely on reliable infrastructure. "
            "Our automated video pipeline ensures clean footage and perfect timing every single second."
        )

        words = re.findall(r"\w+[.,!?;]?", default_sentence)
        word_list: List[Dict[str, Any]] = []
        current_time = 0.5
        word_duration = 0.38

        for word in words:
            clean_w = re.sub(r"[^\w]", "", word)
            word_list.append({
                "word": clean_w,
                "start": round(current_time, 2),
                "end": round(current_time + word_duration, 2),
                "probability": 0.98,
            })
            current_time += word_duration + 0.05
            if word.endswith((".", "!", "?")):
                current_time += 0.35  # Pause between sentences

        return {
            "text": default_sentence,
            "language": "en",
            "duration": round(current_time, 2),
            "words": word_list,
        }
