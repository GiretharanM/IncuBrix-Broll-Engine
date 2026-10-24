import json
import httpx
from app.config import settings

params = {
    "key": settings.PIXABAY_API_KEY,
    "q": "puppies running on grass",
    "video_type": "all",
    "per_page": 10,
    "safesearch": "true",
}

with httpx.Client(timeout=10.0) as client:
    resp = client.get("https://pixabay.com/api/videos/", params=params)
    data = resp.json()
    print("Total hits for 'puppies running on grass':", data.get("totalHits"))
    hits = data.get("hits", [])
    print(f"Returned {len(hits)} hits:")
    for h in hits:
        print(f"  ID: {h.get('id')}, tags: {h.get('tags')}")
