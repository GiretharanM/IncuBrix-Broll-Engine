import logging
from typing import List, Dict, Any, Optional
from app.adapters.footage.pexels_adapter import PexelsFootageAdapter
from app.adapters.footage.pixabay_adapter import PixabayFootageAdapter
from app.adapters.footage.generative_adapter import GenerativeFootageAdapter
from app.adapters.footage.mock_footage import MockFootageProvider
from app.pipeline.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from app.config import settings

logger = logging.getLogger(__name__)

class FootageRetrievalEngine:
    def __init__(self):
        self.pexels = PexelsFootageAdapter()
        self.pixabay = PixabayFootageAdapter()
        self.generative = GenerativeFootageAdapter()
        self.mock = MockFootageProvider()

        # Circuit breakers for external APIs
        self.pexels_breaker = CircuitBreaker("Pexels", failure_threshold=2, recovery_timeout_seconds=30.0)
        self.pixabay_breaker = CircuitBreaker("Pixabay", failure_threshold=2, recovery_timeout_seconds=30.0)
        self.generative_breaker = CircuitBreaker("Generative", failure_threshold=3, recovery_timeout_seconds=30.0)

    def retrieve_candidates_for_scene(
        self,
        query: str,
        avoid: Optional[List[str]] = None,
        count: int = 5,
        warnings_out: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves footage candidates with cascading circuit-breaker resilience:
        Pexels -> Pixabay -> Local Mock Catalog -> Generative AI Fallback -> Safe Solid Card.
        Guarantees that provider timeouts or 5xx errors gracefully degrade rather than crashing.
        """
        candidates: List[Dict[str, Any]] = []

        # 1. Primary: Pexels (guarded by circuit breaker)
        if settings.FOOTAGE_ADAPTER not in ("mock", "offline") and settings.PEXELS_API_KEY:
            try:
                candidates = self.pexels_breaker.call(
                    self.pexels.search_footage, query=query, count=count, avoid=avoid
                )
            except CircuitBreakerOpenException as cbe:
                logger.warning(f"Pexels circuit OPEN: {cbe}")
                if warnings_out is not None:
                    warnings_out.append(f"Pexels circuit breaker is OPEN ({cbe}). Failing over to Pixabay.")
            except Exception as e:
                logger.warning(f"Pexels request failed: {e}")
                if warnings_out is not None:
                    warnings_out.append(f"Pexels retrieval failed for query '{query}': {e}. Failing over to Pixabay.")

        # 2. Secondary: Pixabay (guarded by circuit breaker)
        if not candidates and settings.FOOTAGE_ADAPTER not in ("mock", "offline") and settings.PIXABAY_API_KEY:
            try:
                candidates = self.pixabay_breaker.call(
                    self.pixabay.search_footage, query=query, count=count, avoid=avoid
                )
                if candidates and warnings_out is not None:
                    warnings_out.append(f"Retrieved footage from secondary provider Pixabay for query '{query}'.")
            except CircuitBreakerOpenException as cbe:
                logger.warning(f"Pixabay circuit OPEN: {cbe}")
                if warnings_out is not None:
                    warnings_out.append(f"Pixabay circuit breaker is OPEN ({cbe}). Failing over to local mock catalog.")
            except Exception as e:
                logger.warning(f"Pixabay request failed: {e}")
                if warnings_out is not None:
                    warnings_out.append(f"Pixabay retrieval failed for query '{query}': {e}. Failing over to local catalog.")

        # 3. Tertiary: Local Clean Mock Footage Catalog
        if not candidates:
            try:
                candidates = self.mock.search_footage(query=query, count=count, avoid=avoid)
            except Exception as e:
                logger.warning(f"Mock footage search failed: {e}")

        # 4. Quaternary: Generative AI / Ken-Burns Motion fallback
        if not candidates:
            try:
                candidates = self.generative_breaker.call(
                    self.generative.search_footage, query=query, count=count, avoid=avoid
                )
                if warnings_out is not None:
                    warnings_out.append(f"No stock footage found for '{query}'. Generated safe AI Ken-Burns fallback.")
            except Exception as e:
                logger.warning(f"Generative synthesis failed: {e}")

        # 5. Ultimate Fallback: Safe Solid Card (job never crashes!)
        if not candidates:
            logger.error(f"All footage sources failed for query '{query}'. Synthesizing emergency safe card.")
            fallback_id = f"fallback_card_{abs(hash(query)) % 10000}"
            candidates = [{
                "id": fallback_id,
                "provider": "fallback_title_card",
                "external_id": fallback_id,
                "title": f"Safe Fallback: {query.capitalize()}",
                "preview_url": "",
                "download_url": "mock://fallback/title_card.mp4",
                "duration": 5.0,
                "width": 1920,
                "height": 1080,
                "licence_name": "IncuBrix Clean Fallback",
                "attribution": "IncuBrix System Emergency Generator",
                "ai_generated": True,
                "relevance_score": 0.28,
                "tags": [query.lower(), "fallback"],
                "reason": "Emergency fallback generated to prevent job termination.",
            }]
            if warnings_out is not None:
                warnings_out.append(f"Emergency fallback card synthesized for query '{query}' due to provider exhaustion.")

        return candidates

footage_retrieval_engine = FootageRetrievalEngine()
