import logging
from typing import List, Dict, Any, Optional
from app.adapters.base import BaseFootageProvider

logger = logging.getLogger(__name__)

class GenerativeFootageAdapter(BaseFootageProvider):
    """
    Generative AI / Ken-Burns animation fallback provider.
    Flags all generated candidates with ai_generated=True and commercial provenance.
    """
    def search_footage(self, query: str, count: int = 2, avoid: Optional[List[str]] = None, duration: Optional[float] = None) -> List[Dict[str, Any]]:
        query_slug = "_".join(query.lower().split()[:3])
        candidates = []
        clip_duration = float(duration) if duration is not None else 3.5

        for i in range(max(1, count)):
            cid = f"gen_kenburns_{query_slug}_{i+1}"
            candidates.append({
                "id": cid,
                "provider": "generative",
                "external_id": cid,
                "title": f"Generative Ken-Burns Motion: {query.capitalize()}",
                "preview_url": f"https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1280&q=80",
                "download_url": "mock://generative/kenburns_animation.mp4",
                "duration": clip_duration,
                "width": 1920,
                "height": 1080,
                "licence_name": "Commercial Fallback (AI Synthesized)",
                "licence": "Commercial Fallback (AI Synthesized)",
                "uploader": "None (System Fallback)",
                "page_url": "",
                "attribution": f"Fallback visual motion generated for '{query}'",
                "ai_generated": True,
                "relevance_score": 0.45,  # Reasonable baseline score
                "tags": query.lower().split() + ["generative", "ai", "kenburns"],
                "reason": f"Synthesized AI Ken-Burns motion sequence matching semantic query '{query}'",
            })

        return candidates

generative_footage_adapter = GenerativeFootageAdapter()
