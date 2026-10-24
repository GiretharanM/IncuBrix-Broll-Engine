import os
from typing import List, Dict, Any, Optional
from app.adapters.base import BaseFootageProvider

class MockFootageProvider(BaseFootageProvider):
    # Static catalog of clean mock B-roll footage items
    MOCK_CATALOG = [
        {
            "id": "clip_workspace_01",
            "title": "Engineer typing code in dark terminal environment",
            "tags": ["technology", "coding", "terminal", "python", "software"],
            "preview_url": "https://assets.mixkit.co/videos/preview/mixkit-hands-typing-on-a-laptop-keyboard-41139-large.mp4",
            "download_url": "https://assets.mixkit.co/videos/download/mixkit-hands-typing-on-a-laptop-keyboard-41139.mp4",
            "duration": 12.0,
            "width": 1920,
            "height": 1080,
            "provider": "mock_pexels",
            "licence_name": "Commercial Clean / Royalty-Free",
            "attribution": "Mock Assets Studio (Royalty Free)",
            "ai_generated": False,
        },
        {
            "id": "clip_handshake_02",
            "title": "Close up business partners shaking hands in boardroom",
            "tags": ["trust", "business", "handshake", "agreement", "partnership"],
            "preview_url": "https://assets.mixkit.co/videos/preview/mixkit-business-partners-shaking-hands-41129-large.mp4",
            "download_url": "https://assets.mixkit.co/videos/download/mixkit-business-partners-shaking-hands-41129.mp4",
            "duration": 9.5,
            "width": 1920,
            "height": 1080,
            "provider": "mock_pixabay",
            "licence_name": "Pixabay Commercial Clean",
            "attribution": "Pixabay / Mock Photographer",
            "ai_generated": False,
        },
        {
            "id": "clip_datacenter_03",
            "title": "Blinking lights in modern enterprise cloud server rack room",
            "tags": ["cloud", "server", "data", "infrastructure", "network"],
            "preview_url": "https://assets.mixkit.co/videos/preview/mixkit-server-room-with-blinking-lights-42512-large.mp4",
            "download_url": "https://assets.mixkit.co/videos/download/mixkit-server-room-with-blinking-lights-42512.mp4",
            "duration": 14.0,
            "width": 1920,
            "height": 1080,
            "provider": "mock_pexels",
            "licence_name": "Pexels License (Commercial Use Allowed)",
            "attribution": "Pexels Creator",
            "ai_generated": False,
        },
        {
            "id": "clip_finance_04",
            "title": "Digital analytics screen with glowing growth charts and curves",
            "tags": ["finance", "bank", "value", "growth", "statistics", "data"],
            "preview_url": "https://assets.mixkit.co/videos/preview/mixkit-financial-charts-and-graphs-on-a-screen-42353-large.mp4",
            "download_url": "https://assets.mixkit.co/videos/download/mixkit-financial-charts-and-graphs-on-a-screen-42353.mp4",
            "duration": 11.2,
            "width": 1920,
            "height": 1080,
            "provider": "mock_pixabay",
            "licence_name": "Pixabay Commercial Clean",
            "attribution": "Pixabay Creator",
            "ai_generated": False,
        },
        {
            "id": "clip_nature_05",
            "title": "Gentle river flowing over smooth mossy stones in morning sun",
            "tags": ["nature", "river", "peace", "calm", "morning", "stones"],
            "preview_url": "https://assets.mixkit.co/videos/preview/mixkit-stream-of-water-in-a-forest-41315-large.mp4",
            "download_url": "https://assets.mixkit.co/videos/download/mixkit-stream-of-water-in-a-forest-41315.mp4",
            "duration": 15.0,
            "width": 1920,
            "height": 1080,
            "provider": "mock_pexels",
            "licence_name": "Pexels Clean License",
            "attribution": "Nature Filmmaker",
            "ai_generated": False,
        },
        {
            "id": "clip_gen_kenburns_06",
            "title": "Generative cinematic 3D pan over abstract architectural landscape",
            "tags": ["abstract", "future", "architecture", "generative", "ai"],
            "preview_url": "https://assets.mixkit.co/videos/preview/mixkit-abstract-glowing-digital-waves-42508-large.mp4",
            "download_url": "https://assets.mixkit.co/videos/download/mixkit-abstract-glowing-digital-waves-42508.mp4",
            "duration": 8.0,
            "width": 1920,
            "height": 1080,
            "provider": "generative",
            "licence_name": "Broll Studio Generative Commercial",
            "attribution": "Broll Studio AI Engine",
            "ai_generated": True,
        },
        {
            "id": "clip_cat_walking_01",
            "title": "Fluffy domestic cat strolling outside on sunny sidewalk path",
            "tags": ["cat", "walking", "pet", "sidewalk", "outdoor", "feline", "cute"],
            "preview_url": "https://assets.mixkit.co/videos/preview/mixkit-cat-walking-in-the-grass-43282-large.mp4",
            "download_url": "https://assets.mixkit.co/videos/download/mixkit-cat-walking-in-the-grass-43282.mp4",
            "duration": 10.0,
            "width": 1920,
            "height": 1080,
            "provider": "mock_pixabay",
            "licence_name": "Pixabay Clean Commercial",
            "attribution": "Pixabay / Animal Filmmaker",
            "ai_generated": False,
        },
        {
            "id": "clip_cat_paws_close_02",
            "title": "Close up paws and tail of curious cat walking softly on carpet",
            "tags": ["cat", "walking", "close up", "paws", "detail", "feline"],
            "preview_url": "https://assets.mixkit.co/videos/preview/mixkit-cat-lying-on-a-carpet-43283-large.mp4",
            "download_url": "https://assets.mixkit.co/videos/download/mixkit-cat-lying-on-a-carpet-43283.mp4",
            "duration": 8.0,
            "width": 1920,
            "height": 1080,
            "provider": "mock_pexels",
            "licence_name": "Pexels Clean License",
            "attribution": "Pexels Creator",
            "ai_generated": False,
        },
        {
            "id": "clip_cat_garden_slowmo_03",
            "title": "Slow motion cat leaping and walking across green backyard grass",
            "tags": ["cat", "walking", "slow motion", "garden", "grass", "sunlight"],
            "preview_url": "https://assets.mixkit.co/videos/preview/mixkit-cat-in-the-garden-43284-large.mp4",
            "download_url": "https://assets.mixkit.co/videos/download/mixkit-cat-in-the-garden-43284.mp4",
            "duration": 9.0,
            "width": 1920,
            "height": 1080,
            "provider": "mock_pixabay",
            "licence_name": "Pixabay Clean Commercial",
            "attribution": "Pixabay Filmmaker",
            "ai_generated": False,
        },
        {
            "id": "clip_ocean_waves_01",
            "title": "Deep blue ocean waves gently crashing onto tropical sandy shoreline",
            "tags": ["ocean", "waves", "water", "sea", "beach", "coast", "nature"],
            "preview_url": "https://assets.mixkit.co/videos/preview/mixkit-aerial-view-of-waves-coming-to-the-beach-5016-large.mp4",
            "download_url": "https://assets.mixkit.co/videos/download/mixkit-aerial-view-of-waves-coming-to-the-beach-5016.mp4",
            "duration": 12.0,
            "width": 1920,
            "height": 1080,
            "provider": "mock_pexels",
            "licence_name": "Pexels Clean License",
            "attribution": "Ocean Drone Studio",
            "ai_generated": False,
        },
        {
            "id": "clip_city_night_01",
            "title": "Glowing modern city skyline skyscrapers traffic light trails night",
            "tags": ["city", "night", "skyline", "busy", "lights", "urban", "traffic"],
            "preview_url": "https://assets.mixkit.co/videos/preview/mixkit-time-lapse-of-a-busy-city-at-night-42354-large.mp4",
            "download_url": "https://assets.mixkit.co/videos/download/mixkit-time-lapse-of-a-busy-city-at-night-42354.mp4",
            "duration": 11.0,
            "width": 1920,
            "height": 1080,
            "provider": "mock_pixabay",
            "licence_name": "Pixabay Clean Commercial",
            "attribution": "Urban Night Filmmaker",
            "ai_generated": False,
        },
        {
            "id": "clip_coffee_pour_01",
            "title": "Fresh steaming hot dark roasted coffee pouring into ceramic mug",
            "tags": ["coffee", "pouring", "cup", "morning", "drink", "steam"],
            "preview_url": "https://assets.mixkit.co/videos/preview/mixkit-pouring-coffee-into-a-cup-42864-large.mp4",
            "download_url": "https://assets.mixkit.co/videos/download/mixkit-pouring-coffee-into-a-cup-42864.mp4",
            "duration": 8.5,
            "width": 1920,
            "height": 1080,
            "provider": "mock_pexels",
            "licence_name": "Pexels Clean License",
            "attribution": "Barista Studio",
            "ai_generated": False,
        },
        {
            "id": "clip_apple_orchard_fruit_01",
            "title": "Ripe fresh red apples hanging from leafy green tree branches in orchard",
            "tags": ["apple", "tree", "fruit", "orchard", "harvest", "fresh", "nature"],
            "preview_url": "https://assets.mixkit.co/videos/preview/mixkit-ripe-apples-on-tree-branch-42999-large.mp4",
            "download_url": "https://assets.mixkit.co/videos/download/mixkit-ripe-apples-on-tree-branch-42999.mp4",
            "duration": 10.0,
            "width": 1920,
            "height": 1080,
            "provider": "mock_pixabay",
            "licence_name": "Pixabay Clean Commercial",
            "attribution": "Farm Grower Studio",
            "ai_generated": False,
        },
        {
            "id": "clip_hospital_medical_01",
            "title": "Caring healthcare doctors walking through quiet clean hospital hallway",
            "tags": ["hospital", "doctor", "medical", "sad news", "healthcare", "patient"],
            "preview_url": "https://assets.mixkit.co/videos/preview/mixkit-hospital-hallway-with-doctors-43100-large.mp4",
            "download_url": "https://assets.mixkit.co/videos/download/mixkit-hospital-hallway-with-doctors-43100.mp4",
            "duration": 9.0,
            "width": 1920,
            "height": 1080,
            "provider": "mock_pexels",
            "licence_name": "Pexels Clean License",
            "attribution": "Medical Documentaries",
            "ai_generated": False,
        },
    ]

    def search_footage(self, query: str, count: int = 5, avoid: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        avoid_set = {a.lower().strip() for a in (avoid or [])}
        query_terms = [t.lower() for t in query.split()]

        scored_candidates = []
        for item in self.MOCK_CATALOG:
            # Check avoid tags
            item_tags_set = {t.lower() for t in item["tags"]}
            if avoid_set and any(avoid_tag in item_tags_set or avoid_tag in item["title"].lower() for avoid_tag in avoid_set):
                continue  # Skip avoided candidate

            # Match score based on query term overlap
            overlap = sum(1 for term in query_terms if term in item_tags_set or term in item["title"].lower())
            score = 0.35 + (0.15 * overlap)
            score = min(0.96, score)

            candidate = dict(item)
            candidate["relevance_score"] = round(score, 3)
            candidate["reason"] = f"Matched {overlap} query terms with visual tags: {', '.join(item['tags'][:3])}"
            scored_candidates.append(candidate)

        # Sort descending by relevance score
        scored_candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored_candidates[:count]
