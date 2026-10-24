import os
import asyncio
from dotenv import load_dotenv
load_dotenv('.env')
from app.adapters.footage.pixabay_adapter import PixabayProvider

async def test():
    pix = PixabayProvider()
    queries = [
        "sunrise snow mountain peaks",
        "waterfall forest",
        "city skyline night skyscrapers"
    ]
    for q in queries:
        hits = await pix.search_footage_async(q, count=2)
        print(f"Query: {q} -> Hits: {len(hits)}")
        for h in hits:
            print(f"   ID: {h['id']} | Title: {h['title'][:60]} | URL: {h['preview_url']}")

if __name__ == "__main__":
    asyncio.run(test())
