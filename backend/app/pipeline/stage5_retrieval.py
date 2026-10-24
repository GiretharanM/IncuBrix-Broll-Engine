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
        self.pexels_breaker = CircuitBreaker("Pexels", failure_threshold=5, recovery_timeout_seconds=30.0)
        self.pixabay_breaker = CircuitBreaker("Pixabay", failure_threshold=5, recovery_timeout_seconds=30.0)
        self.generative_breaker = CircuitBreaker("Generative", failure_threshold=5, recovery_timeout_seconds=30.0)

    def retrieve_candidates_for_scene(
        self,
        query: str,
        avoid: Optional[List[str]] = None,
        count: int = 5,
        warnings_out: Optional[List[str]] = None,
        duration: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves footage candidates with cascading circuit-breaker resilience:
        Pexels -> Pixabay -> Local Mock Catalog -> Generative AI Fallback -> Safe Solid Card.
        Guarantees that provider timeouts or 5xx errors gracefully degrade rather than crashing.
        """
        candidates: List[Dict[str, Any]] = []

        # Iterate through providers according to FOOTAGE_PROVIDERS priority order
        providers_order = [p.strip().lower() for p in settings.FOOTAGE_PROVIDERS.split(",") if p.strip()]
        if not providers_order:
            providers_order = ["pixabay", "pexels", "mock", "generative"]

        for prov in providers_order:
            if candidates:
                break

            if prov == "pixabay" and settings.PIXABAY_API_KEY and not settings.PIXABAY_API_KEY.startswith("mock"):
                try:
                    candidates = self.pixabay_breaker.call(
                        self.pixabay.search_footage, query=query, count=count, avoid=avoid
                    )
                    if candidates and warnings_out is not None:
                        warnings_out.append(f"Retrieved footage from Pixabay for query '{query}'.")
                except CircuitBreakerOpenException as cbe:
                    logger.warning(f"Pixabay circuit OPEN: {cbe}")
                    if warnings_out is not None:
                        warnings_out.append(f"Pixabay circuit breaker is OPEN ({cbe}). Failing over.")
                except Exception as e:
                    logger.warning(f"Pixabay request failed: {e}")
                    if warnings_out is not None:
                        warnings_out.append(f"Pixabay retrieval failed for query '{query}': {e}. Failing over.")

            elif prov == "pexels" and settings.PEXELS_API_KEY and not settings.PEXELS_API_KEY.startswith("mock"):
                try:
                    candidates = self.pexels_breaker.call(
                        self.pexels.search_footage, query=query, count=count, avoid=avoid
                    )
                    if candidates and warnings_out is not None:
                        warnings_out.append(f"Retrieved footage from Pexels for query '{query}'.")
                except CircuitBreakerOpenException as cbe:
                    logger.warning(f"Pexels circuit OPEN: {cbe}")
                    if warnings_out is not None:
                        warnings_out.append(f"Pexels circuit breaker is OPEN ({cbe}). Failing over.")
                except Exception as e:
                    logger.warning(f"Pexels request failed: {e}")
                    if warnings_out is not None:
                        warnings_out.append(f"Pexels retrieval failed for query '{query}': {e}. Failing over.")

            elif prov == "mock":
                try:
                    candidates = self.mock.search_footage(query=query, count=count, avoid=avoid)
                except Exception as e:
                    logger.warning(f"Mock footage search failed: {e}")

            elif prov == "generative":
                try:
                    candidates = self.generative_breaker.call(
                        self.generative.search_footage, query=query, count=count, avoid=avoid, duration=duration
                    )
                    if candidates and warnings_out is not None:
                        warnings_out.append(f"Generated safe AI Ken-Burns fallback for '{query}'.")
                except Exception as e:
                    logger.warning(f"Generative synthesis failed: {e}")

        # 5. Ultimate Fallback: Safe Solid Card (job never crashes!)
        if not candidates:
            logger.error(f"All footage sources failed for query '{query}'. Synthesizing emergency safe card.")
            fallback_id = f"fallback_card_{abs(hash(query)) % 10000}"
            clip_dur = float(duration) if duration is not None else 3.5
            candidates = [{
                "id": fallback_id,
                "provider": "fallback_title_card",
                "external_id": fallback_id,
                "title": f"Safe Fallback: {query.capitalize()}",
                "preview_url": "",
                "download_url": "mock://fallback/title_card.mp4",
                "duration": clip_dur,
                "width": 1920,
                "height": 1080,
                "licence_name": "None (System Fallback)",
                "licence": "None (System Fallback)",
                "uploader": "None (System Fallback)",
                "page_url": "",
                "attribution": f"Fallback card generated for '{query}'",
                "ai_generated": True,
                "relevance_score": 0.28,
                "tags": [query.lower(), "fallback"],
                "reason": "Emergency fallback generated to prevent job termination.",
            }]
            if warnings_out is not None:
                warnings_out.append(f"Emergency fallback card synthesized for query '{query}' due to provider exhaustion.")

        return candidates

footage_retrieval_engine = FootageRetrievalEngine()
