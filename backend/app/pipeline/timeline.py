import json
from typing import List, Dict, Any

class TimelineBuilder:
    @staticmethod
    def build_timeline_json(
        job_id: str,
        scenes_data: List[Dict[str, Any]],
        aspect_ratios: List[str],
        total_duration: float,
        prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Builds the structured timeline.json document describing scene-by-scene provenance.
        """
        scenes_output = []
        for s in scenes_data:
            cand = s.get("selected_candidate") or {}
            page_url = cand.get("pageURL") or cand.get("page_url") or s.get("page_url") or ""
            storage_url = s.get("storage_url") or s.get("preview_url") or cand.get("download_url") or ""

            scenes_output.append({
                "scene_id": s.get("scene_id") or f"scene_{s.get('scene_index', 0):02d}",
                "scene_index": s.get("scene_index", 0),
                "prompt": prompt or s.get("prompt", ""),
                "narration_text": s.get("text", ""),
                "visual_query": s.get("visual_query") or s.get("search_query", ""),
                "start_time": round(s.get("start_time", 0.0), 2),
                "end_time": round(s.get("end_time", 0.0), 2),
                "duration": round(s.get("duration", 0.0), 2),
                "clip_id": s.get("selected_clip_id"),
                "source": s.get("provider", "mock"),
                "licence": s.get("licence_name") or cand.get("licence_name") or "Commercial Clean",
                "attribution": s.get("attribution") or cand.get("attribution") or "Royalty Free",
                "link": page_url or cand.get("pageURL") or s.get("download_url", ""),
                "storage_url": storage_url,
                "ai_generated": bool(s.get("ai_generated", False)),
                "selection_reason": s.get("selection_reason", ""),
                "relevance_score": round(float(s.get("relevance_score", 0.0)), 3),
                "source_choice_reason": s.get("source_choice_reason", ""),
            })

        return {
            "job_id": job_id,
            "version": "1.0.0",
            "prompt": prompt,
            "total_scenes": len(scenes_output),
            "total_duration_seconds": round(total_duration, 2),
            "aspect_ratios": aspect_ratios,
            "scenes": scenes_output,
        }

timeline_builder = TimelineBuilder()
