import logging
from typing import List, Dict, Any, Optional
from app.adapters.footage.pexels_adapter import PexelsFootageAdapter
from app.adapters.footage.pixabay_adapter import PixabayFootageAdapter
from app.adapters.footage.generative_adapter import GenerativeFootageAdapter
from app.adapters.footage.mock_footage import MockFootageProvider
from app.config import settings

logger = logging.getLogger(__name__)

class FootageRetrievalEngine:
    def __init__(self):
        self.pexels = PexelsFootageAdapter()
        self.pixabay = PixabayFootageAdapter()
        self.generative = GenerativeFootageAdapter()
        self.mock = MockFootageProvider()

    def retrieve_candidates_for_scene(
        self,
        query: str,
        avoid: Optional[List[str]] = None,
        count: int = 5,
        warnings_out: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves footage candidates with cascading fallback resilience:
        Pexels -> Pixabay -> Mock Catalog -> Generative AI Fallback.
        Appends warnings on provider timeouts or fallback events.
        """
        candidates: List[Dict[str, Any]] = []

        # 1. Primary: Pexels (if adapter enabled and not mock)
        if settings.FOOTAGE_ADAPTER not in ("mock", "offline") and settings.PEXELS_API_KEY:
            try:
                candidates = self.pexels.search_footage(query=query, count=count, avoid=avoid)
            except Exception as e:
                logger.warning(f"Pexels provider failed: {e}")
                if warnings_out is not None:
                    warnings_out.append(f"Pexels search failed for query '{query}'. Falling back to secondary provider.")

        # 2. Secondary: Pixabay (if Pexels yielded 0 candidates)
        if not candidates and settings.FOOTAGE_ADAPTER not in ("mock", "offline") and settings.PIXABAY_API_KEY:
            try:
                candidates = self.pixabay.search_footage(query=query, count=count, avoid=avoid)
                if candidates and warnings_out is not None:
                    warnings_out.append(f"Retrieved footage from secondary provider Pixabay for query '{query}'.")
            except Exception as e:
                logger.warning(f"Pixabay provider failed: {e}")
                if warnings_out is not None:
                    warnings_out.append(f"Pixabay search failed for query '{query}'.")

        # 3. Tertiary: Local Clean Mock Footage Catalog
        if not candidates:
            candidates = self.mock.search_footage(query=query, count=count, avoid=avoid)

        # 4. Safe Generative Fallback if still empty
        if not candidates:
            candidates = self.generative.search_footage(query=query, count=count, avoid=avoid)
            if warnings_out is not None:
                warnings_out.append(f"No stock footage found for '{query}'. Generated safe Ken-Burns fallback.")

        return candidates

footage_retrieval_engine = FootageRetrievalEngine()
