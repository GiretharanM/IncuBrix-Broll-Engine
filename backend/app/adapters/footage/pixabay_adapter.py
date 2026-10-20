import logging
import httpx
from typing import List, Dict, Any, Optional
from app.adapters.base import BaseFootageProvider
from app.config import settings

logger = logging.getLogger(__name__)

class PixabayFootageAdapter(BaseFootageProvider):
    API_URL = "https://pixabay.com/api/videos/"

    def __init__(self, api_key: Optional[str] = None, timeout_seconds: float = 4.0):
        self.api_key = api_key or settings.PIXABAY_API_KEY
        self.timeout_seconds = timeout_seconds

    def search_footage(self, query: str, count: int = 5, avoid: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        if not self.api_key or self.api_key.startswith("mock"):
            logger.debug("Pixabay API key not configured, returning empty for provider fallback")
            return []

        params = {
            "key": self.api_key,
            "q": query,
            "video_type": "film",
            "per_page": count * 2,
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(self.API_URL, params=params)
                if response.status_code != 200:
                    logger.warning(f"Pixabay API returned {response.status_code}: {response.text}")
                    return []

                data = response.json()
                hits = data.get("hits", [])
                avoid_set = {a.lower().strip() for a in (avoid or [])}

                results = []
                for h in hits:
                    tag_str = h.get("tags", "").lower()
                    tags = [t.strip() for t in tag_str.split(",") if t.strip()]
                    if avoid_set and any(a in tags for a in avoid_set):
                        continue

                    videos_dict = h.get("videos", {})
                    # Prefer large or medium
                    chosen_vid = videos_dict.get("large") or videos_dict.get("medium") or videos_dict.get("small")
                    if not chosen_vid or not chosen_vid.get("url"):
                        continue

                    results.append({
                        "id": f"pixabay_{h.get('id')}",
                        "provider": "pixabay",
                        "external_id": str(h.get("id")),
                        "title": f"Pixabay: {h.get('tags', query)} by {h.get('user', 'Pixabay Filmmaker')}",
                        "preview_url": h.get("picture_id", ""),
                        "download_url": chosen_vid.get("url", ""),
                        "duration": float(h.get("duration", 10.0)),
                        "width": chosen_vid.get("width", 1920),
                        "height": chosen_vid.get("height", 1080),
                        "licence_name": "Pixabay Content License (Commercial Use Allowed)",
                        "attribution": f"Video by {h.get('user', 'Pixabay Filmmaker')} on Pixabay",
                        "ai_generated": False,
                        "relevance_score": 0.72,
                        "tags": tags,
                    })

                return results[:count]

        except httpx.TimeoutException:
            logger.warning(f"Pixabay API timed out after {self.timeout_seconds}s querying '{query}'")
            return []
        except Exception as e:
            logger.warning(f"Pixabay retrieval exception: {e}")
            return []
