from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseSTTAdapter(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribes audio file to text with word-level timestamps.
        Returns:
            {
                "text": str,
                "language": str,
                "duration": float,
                "words": [{"word": str, "start": float, "end": float, "probability": float}]
            }
        """
        pass

class BaseTTSAdapter(ABC):
    @abstractmethod
    def synthesize(self, text: str, voice: str = "en-US-Standard", language: str = "en") -> str:
        """
        Synthesizes text to speech audio file.
        Returns local file path to rendered WAV/MP3.
        """
        pass

class BaseLLMAdapter(ABC):
    @abstractmethod
    def understand_scene(self, scene_text: str, visual_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Extracts visual search query, resolves ambiguity, handles statistics,
        detects brand names and issues safety warnings.
        Returns:
            {
                "search_query": str,
                "metaphors": List[str],
                "contains_brand_or_person": bool,
                "is_statistic": bool,
                "safety_warning": Optional[str]
            }
        """
        pass

class BaseFootageProvider(ABC):
    @abstractmethod
    def search_footage(self, query: str, count: int = 5, avoid: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Searches provider for clean commercial B-roll clips.
        Returns candidate list with external_id, title, preview_url, download_url, duration, licence, etc.
        """
        pass

class BaseVisionScorer(ABC):
    @abstractmethod
    def score_relevance(self, candidate_meta: Dict[str, Any], scene_text: str, visual_hint: Optional[str] = None) -> float:
        """
        Computes semantic similarity score (0.0 to 1.0) between footage candidate and scene context.
        """
        pass
