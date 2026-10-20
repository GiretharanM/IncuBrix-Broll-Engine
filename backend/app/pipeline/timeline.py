import json
from typing import List, Dict, Any

class TimelineBuilder:
    @staticmethod
    def build_timeline_json(
        job_id: str,
        scenes_data: List[Dict[str, Any]],
        aspect_ratios: List[str],
        total_duration: float,
    ) -> Dict[str, Any]:
        """
        Builds the structured timeline.json document describing scene-by-scene provenance.
        """
        scenes_output = []
        for s in scenes_data:
            scenes_output.append({
                "scene_id": s.get("scene_id") or f"scene_{s.get('scene_index', 0):02d}",
                "scene_index": s.get("scene_index", 0),
                "narration_text": s.get("text", ""),
                "start_time": round(s.get("start_time", 0.0), 2),
                "end_time": round(s.get("end_time", 0.0), 2),
                "duration": round(s.get("duration", 0.0), 2),
                "clip_id": s.get("selected_clip_id"),
                "source": s.get("provider", "mock"),
                "licence": s.get("licence_name", "Commercial Clean"),
                "attribution": s.get("attribution", "Royalty Free"),
                "link": s.get("download_url", ""),
                "ai_generated": bool(s.get("ai_generated", False)),
                "selection_reason": s.get("selection_reason", ""),
                "relevance_score": round(float(s.get("relevance_score", 0.0)), 3),
                "source_choice_reason": s.get("source_choice_reason", ""),
            })

        return {
            "job_id": job_id,
            "version": "1.0.0",
            "total_scenes": len(scenes_output),
            "total_duration_seconds": round(total_duration, 2),
            "aspect_ratios": aspect_ratios,
            "scenes": scenes_output,
        }

timeline_builder = TimelineBuilder()
