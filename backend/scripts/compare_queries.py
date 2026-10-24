import httpx
from app.config import settings

def test_q(q):
    resp = httpx.get("https://pixabay.com/api/videos/", params={
        "key": settings.PIXABAY_API_KEY,
        "q": q,
        "per_page": 5
    })
    hits = resp.json().get("hits", [])
    print(f"\n=== Query: '{q}' ({len(hits)} hits) ===")
    for h in hits:
        print(f"  ID {h['id']}: {h.get('tags')}")

test_q("golden retriever playing in a park in scenic outdoor environment wide angle")
test_q("golden retriever park")
test_q("golden retriever")
test_q("puppies running on grass moving smoothly through frame medium distance")
test_q("puppies grass")
test_q("puppies running")
test_q("dogs beach")
