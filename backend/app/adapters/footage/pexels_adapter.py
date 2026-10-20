import logging
import httpx
from typing import List, Dict, Any, Optional
from app.adapters.base import BaseFootageProvider
from app.config import settings
from app.errors import ProviderTimeoutException

logger = logging.getLogger(__name__)

class PexelsFootageAdapter(BaseFootageProvider):
    API_URL = "https://api.pexels.com/videos/search"

    def __init__(self, api_key: Optional[str] = None, timeout_seconds: float = 4.0):
        self.api_key = api_key or settings.PEXELS_API_KEY
        self.timeout_seconds = timeout_seconds

    def search_footage(self, query: str, count: int = 5, avoid: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        if not self.api_key or self.api_key.startswith("mock"):
            logger.debug("Pexels API key not configured, returning empty for provider fallback")
            return []

        headers = {"Authorization": self.api_key}
        params = {"query": query, "per_page": count * 2, "orientation": "landscape"}

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(self.API_URL, headers=headers, params=params)
                if response.status_code != 200:
                    logger.warning(f"Pexels API returned {response.status_code}: {response.text}")
                    return []

                data = response.json()
                videos = data.get("videos", [])
                avoid_set = {a.lower().strip() for a in (avoid or [])}

                results = []
                for v in videos:
                    # Check avoid tags in tags or user title
                    tags = [t.get("name", "").lower() for t in v.get("tags", [])]
                    if avoid_set and any(a in tags for a in avoid_set):
                        continue

                    # Select best 1080p video file
                    video_files = v.get("video_files", [])
                    hd_files = [f for f in video_files if f.get("width") == 1920 or f.get("quality") == "hd"]
                    chosen_file = hd_files[0] if hd_files else (video_files[0] if video_files else None)
                    if not chosen_file:
                        continue

                    results.append({
                        "id": f"pexels_{v.get('id')}",
                        "provider": "pexels",
                        "external_id": str(v.get("id")),
                        "title": f"Pexels: {query} by {v.get('user', {}).get('name', 'Pexels Creator')}",
                        "preview_url": v.get("image", ""),
                        "download_url": chosen_file.get("link", ""),
                        "duration": float(v.get("duration", 10.0)),
                        "width": chosen_file.get("width", 1920),
                        "height": chosen_file.get("height", 1080),
                        "licence_name": "Pexels License (Commercial Clean)",
                        "attribution": f"Video by {v.get('user', {}).get('name', 'Pexels Creator')} on Pexels",
                        "ai_generated": False,
                        "relevance_score": 0.75,
                        "tags": tags,
                    })

                return results[:count]

        except httpx.TimeoutException:
            logger.warning(f"Pexels API timed out after {self.timeout_seconds}s querying '{query}'")
            return []
        except Exception as e:
            logger.warning(f"Pexels retrieval exception: {e}")
            return []
