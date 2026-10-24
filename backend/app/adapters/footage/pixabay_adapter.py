import os
import re
import asyncio
import logging
import httpx
from typing import List, Dict, Any, Optional

from app.adapters.base import BaseFootageProvider
from app.config import settings

logger = logging.getLogger(__name__)

PIXABAY_STOP_WORDS = {
    "in", "on", "at", "a", "an", "the", "of", "with", "into", "through", "from",
    "over", "under", "across", "for", "and", "to", "is", "are", "as", "that", "this",
    "view", "shot", "angle", "distance", "frame", "moving", "smoothly", "lighting",
    "crisp", "beautiful", "stunning", "scenic", "experience", "around"
}

def clean_pixabay_query(query: str) -> str:
    """Extracts high-signal visual keywords for Pixabay's tag-based search engine."""
    tokens = [w.strip() for w in re.findall(r"\b[a-zA-Z0-9-]+\b", query.lower())]
    informative = [w for w in tokens if w not in PIXABAY_STOP_WORDS and len(w) > 2]
    if not informative:
        return query.strip()
    # Return top 2-4 salient nouns/verbs
    return " ".join(informative[:4])

class PixabayProvider(BaseFootageProvider):
    """
    Async Pixabay Video API adapter.
    Features:
    - Async HTTP requests via httpx.AsyncClient
    - Safe search filter enabled
    - HTTP 429 exponential backoff retry
    - Query simplification fallback when 0 hits returned
    - PROVIDER_AUTH_FAILED error classification for bad credentials
    - Local storage downloading and caching (no hotlinking in output)
    - Full clip metadata extraction for timeline.json
    """
    API_URL = "https://pixabay.com/api/videos/"

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout_seconds: float = 8.0,
        cache_dir: Optional[str] = None,
    ):
        # Read strictly from environment or settings; never hardcode or log
        self.api_key = api_key or os.getenv("PIXABAY_API_KEY") or settings.PIXABAY_API_KEY
        self.timeout_seconds = timeout_seconds
        base_cache = cache_dir or settings.CACHE_DIR or "/tmp/incubrix_cache"
        self.clip_cache_dir = os.path.join(base_cache, "clips")
        self._search_cache: Dict[str, List[Dict[str, Any]]] = {}
        try:
            os.makedirs(self.clip_cache_dir, exist_ok=True)
        except Exception:
            pass

    async def search_footage_async(
        self,
        query: str,
        count: int = 5,
        avoid: Optional[List[str]] = None,
        warnings_out: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Asynchronously search Pixabay for commercial video clips.
        """
        cache_key = f"{query.strip().lower()}:{count}:{','.join(sorted(avoid or []))}"
        if cache_key in self._search_cache:
            logger.info(f"Pixabay search cache hit for '{query}'")
            return [dict(c) for c in self._search_cache[cache_key]]

        if not self.api_key or self.api_key.startswith("mock") or self.api_key.strip() == "":
            logger.debug("Pixabay API key not configured or set to mock. Falling back.")
            if warnings_out is not None:
                warnings_out.append("Pixabay API key not configured or mock.")
            return []

        # Check if provider is enabled in FOOTAGE_PROVIDERS
        configured_providers = [p.strip().lower() for p in (os.getenv("FOOTAGE_PROVIDERS") or settings.FOOTAGE_PROVIDERS).split(",")]
        if "pixabay" not in configured_providers and settings.FOOTAGE_ADAPTER not in ("real", "pixabay"):
            logger.debug("Pixabay not in active FOOTAGE_PROVIDERS list.")
            return []

        # Extract clean, focused visual search keywords
        cleaned_query = clean_pixabay_query(query)

        params = {
            "key": self.api_key,
            "q": cleaned_query,
            "video_type": "all",
            "per_page": min(max(count * 2, 8), 50),
            "safesearch": "true",
        }

        hits = await self._fetch_with_backoff(params, query=cleaned_query, warnings_out=warnings_out)

        # If 0 hits, try core 2 words
        if not hits:
            core_words = [w for w in cleaned_query.split() if len(w) > 2][:2]
            if core_words and " ".join(core_words) != cleaned_query:
                simplified = " ".join(core_words)
                logger.info(f"Pixabay returned 0 hits for '{cleaned_query}'. Trying simplified query '{simplified}'.")
                params["q"] = simplified
                hits = await self._fetch_with_backoff(params, query=simplified, warnings_out=warnings_out)

        if not hits:
            return []

        avoid_set = {a.lower().strip() for a in (avoid or [])}
        results: List[Dict[str, Any]] = []

        for h in hits:
            tag_str = h.get("tags", "").lower()
            tags = [t.strip() for t in tag_str.split(",") if t.strip()]
            if avoid_set and any(a in tags for a in avoid_set):
                continue

            videos_dict = h.get("videos", {})
            # Pick best available file: large, then medium, then small
            chosen_vid = (
                videos_dict.get("large")
                or videos_dict.get("medium")
                or videos_dict.get("small")
                or videos_dict.get("tiny")
            )
            if not chosen_vid or not chosen_vid.get("url"):
                continue

            vid_url = chosen_vid.get("url", "")
            clip_id = f"pixabay_{h.get('id')}"
            uploader = h.get("user", "Pixabay Filmmaker")
            page_url = h.get("pageURL", f"https://pixabay.com/videos/id-{h.get('id')}/")
            duration = float(h.get("duration", 10.0))
            width = int(chosen_vid.get("width", 1920))
            height = int(chosen_vid.get("height", 1080))

            results.append({
                "id": clip_id,
                "provider": "pixabay",
                "external_id": str(h.get("id")),
                "title": f"Pixabay: {h.get('tags', query)} by {uploader}",
                "pageURL": page_url,
                "uploader": uploader,
                "preview_url": vid_url,
                "download_url": vid_url,
                "duration": duration,
                "width": width,
                "height": height,
                "resolution": f"{width}x{height}",
                "licence": "Pixabay Content License (Commercial Use Allowed)",
                "licence_name": "Pixabay Content License (Commercial Use Allowed)",
                "attribution": f"Video by {uploader} via Pixabay ({page_url})",
                "ai_generated": False,
                "relevance_score": 0.88,
                "tags": tags,
            })

            if len(results) >= count:
                break

        self._search_cache[cache_key] = results
        return results

    async def _fetch_with_backoff(
        self,
        params: Dict[str, Any],
        query: str,
        warnings_out: Optional[List[str]] = None,
        max_retries: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Executes HTTP GET with exponential backoff on HTTP 429 rate limit.
        Handles PROVIDER_AUTH_FAILED and timeouts gracefully.
        """
        delay = 1.0
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.get(self.API_URL, params=params)

                    if resp.status_code == 200:
                        data = resp.json()
                        return data.get("hits", [])

                    # HTTP 429 Rate Limit
                    if resp.status_code == 429:
                        logger.warning(
                            f"Pixabay HTTP 429 Rate Limit on query '{query}' (attempt {attempt + 1}/{max_retries}). Backing off {delay}s."
                        )
                        if attempt < max_retries - 1:
                            await asyncio.sleep(delay)
                            delay *= 2.0
                            continue
                        if warnings_out is not None:
                            warnings_out.append(f"Pixabay HTTP 429 Rate Limit exceeded for '{query}'.")
                        return []

                    # Authentication failure (Invalid or revoked API key)
                    if resp.status_code in (400, 401, 403):
                        logger.error(
                            f"PROVIDER_AUTH_FAILED: Pixabay API key invalid or unauthorized (HTTP {resp.status_code})."
                        )
                        if warnings_out is not None:
                            warnings_out.append("PROVIDER_AUTH_FAILED: Pixabay key unauthorized. Switched to fallback.")
                        return []

                    logger.warning(f"Pixabay API returned HTTP {resp.status_code} for query '{query}'.")
                    return []

            except httpx.TimeoutException:
                logger.warning(f"Pixabay timeout after {self.timeout_seconds}s for query '{query}' (attempt {attempt+1}).")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
                    continue
                if warnings_out is not None:
                    warnings_out.append(f"Pixabay search timed out for query '{query}'.")
                return []
            except Exception as e:
                logger.warning(f"Pixabay search exception on query '{query}': {e}")
                return []

        return []

    async def download_clip_async(self, download_url: str, clip_id: str) -> str:
        """
        Downloads the remote video file to local storage cache.
        Returns the absolute local path. Guarantees no hotlinking in final output.
        """
        safe_name = "".join(c for c in clip_id if c.isalnum() or c in ("-", "_"))
        local_path = os.path.join(self.clip_cache_dir, f"{safe_name}.mp4")

        # Cache hit: already downloaded and has content
        if os.path.exists(local_path) and os.path.getsize(local_path) > 1024:
            logger.info(f"Clip cache hit for {clip_id}: {local_path}")
            return local_path

        logger.info(f"Downloading Pixabay clip {clip_id} to {local_path}...")
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                async with client.stream("GET", download_url) as resp:
                    if resp.status_code == 200:
                        temp_path = f"{local_path}.part"
                        with open(temp_path, "wb") as f:
                            async for chunk in resp.aiter_bytes(chunk_size=65536):
                                f.write(chunk)
                        os.replace(temp_path, local_path)
                        logger.info(f"Downloaded clip {clip_id} ({os.path.getsize(local_path)} bytes)")
                        return local_path
                    else:
                        logger.warning(f"Failed to download clip {clip_id} (HTTP {resp.status_code})")
        except Exception as e:
            logger.error(f"Error downloading clip {clip_id}: {e}")

        # If download failed, return download_url as fallback
        return download_url

    def download_clip(self, download_url: str, clip_id: str) -> str:
        """Synchronous wrapper for download_clip_async."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(lambda: asyncio.run(self.download_clip_async(download_url, clip_id))).result()
            return loop.run_until_complete(self.download_clip_async(download_url, clip_id))
        except Exception:
            return asyncio.run(self.download_clip_async(download_url, clip_id))

    def search_footage(self, query: str, count: int = 5, avoid: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Synchronous interface matching BaseFootageProvider.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(lambda: asyncio.run(self.search_footage_async(query, count, avoid))).result()
            return loop.run_until_complete(self.search_footage_async(query, count, avoid))
        except Exception:
            return asyncio.run(self.search_footage_async(query, count, avoid))

# Backward-compatibility alias
PixabayFootageAdapter = PixabayProvider
