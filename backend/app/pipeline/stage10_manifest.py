"""
Stage 10: Manifest Builder
----------------------------
Generates manifest.json containing comprehensive metadata about the
rendered video outputs: models, providers, versions, settings, seed,
timings, cost estimate, warnings, licence/rights summary, and
AI-generated labels.
"""

import json
import logging
import os
import platform
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Version constants
PIPELINE_VERSION = "1.0.0"
ENGINE_VERSION = "broll-studio-engine-v1"


class ManifestBuilder:
    """
    Builds the manifest.json document capturing full provenance,
    configuration, and quality metrics for a completed render job.
    """

    def build_manifest(
        self,
        job_id: str,
        timeline_data: Dict[str, Any],
        render_results: Dict[str, Dict[str, Any]],
        pipeline_config: Dict[str, Any],
        timings: Dict[str, float],
        warnings: List[str],
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Constructs the manifest.json structure.

        Args:
            job_id: Unique job identifier
            timeline_data: Timeline JSON from stage 7 (scene provenance)
            render_results: Per-ratio render outputs from stage 8
            pipeline_config: Configuration snapshot (adapters, settings)
            timings: Stage-by-stage timing breakdown (stage_name → seconds)
            warnings: Accumulated warnings from all pipeline stages
            seed: Random seed used for reproducibility (if applicable)

        Returns:
            Complete manifest dictionary ready for JSON serialization
        """
        now = datetime.now(timezone.utc)
        scenes = timeline_data.get("scenes", [])

        # Compute aggregate metrics
        total_duration = timeline_data.get("total_duration_seconds", 0.0)
        cost_estimate = self._estimate_cost(scenes, render_results)
        licence_summary = self._build_licence_summary(scenes)
        ai_labels = self._build_ai_labels(scenes)

        manifest = {
            "manifest_version": "1.0.0",
            "job_id": job_id,
            "generated_at": now.isoformat(),
            "engine": {
                "name": ENGINE_VERSION,
                "pipeline_version": PIPELINE_VERSION,
                "python_version": platform.python_version(),
                "platform": platform.platform(),
            },
            "models_and_providers": self._build_provider_info(pipeline_config),
            "settings": {
                "voice": pipeline_config.get("voice", "en-US-Standard"),
                "style": pipeline_config.get("style", "cinematic"),
                "aspect_ratios": pipeline_config.get("aspect_ratios", ["16:9"]),
                "burn_in_captions": pipeline_config.get("burn_in_captions", True),
                "srt_captions": pipeline_config.get("srt_captions", True),
                "avoid_tags": pipeline_config.get("avoid_tags", []),
                "min_scene_duration": settings.MIN_SCENE_DURATION_SECONDS,
                "stock_selection_threshold": settings.STOCK_SELECTION_THRESHOLD,
                "max_audio_duration": settings.MAX_AUDIO_DURATION_SECONDS,
            },
            "seed": seed,
            "timings": self._format_timings(timings),
            "cost_estimate": cost_estimate,
            "outputs": self._build_output_info(render_results),
            "quality_metrics": {
                "total_scenes": len(scenes),
                "total_duration_seconds": round(total_duration, 2),
                "avg_relevance_score": self._avg_relevance(scenes),
                "min_relevance_score": self._min_relevance(scenes),
                "repeat_clip_rate": 0.0,  # enforced by stage 6
                "narration_coverage": 1.0,  # enforced by stage 3
            },
            "licence_summary": licence_summary,
            "ai_generated_labels": ai_labels,
            "warnings": warnings,
            "scenes_count": len(scenes),
        }

        return manifest

    def save_manifest(
        self, manifest: Dict[str, Any], output_dir: str, job_id: str
    ) -> str:
        """Writes manifest.json to disk and returns the file path."""
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "manifest.json")

        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)

        logger.info("Manifest written to %s for job %s", path, job_id)
        return path

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def _build_output_info(
        self, render_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Builds the outputs section listing produced files per ratio."""
        outputs: Dict[str, Any] = {}
        for ratio, info in render_results.items():
            ratio_label = ratio.replace(":", "x")
            outputs[ratio] = {
                "video_file": f"video_{ratio_label}.mp4",
                "video_path": info.get("video_path"),
                "srt_file": f"captions_{ratio_label}.srt" if info.get("srt_path") else None,
                "duration": info.get("duration", 0.0),
                "error": info.get("error"),
            }
        return outputs

    def _build_provider_info(
        self, pipeline_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Captures which adapters/models/providers were used."""
        return {
            "stt_adapter": pipeline_config.get("stt_adapter", settings.STT_ADAPTER),
            "tts_adapter": pipeline_config.get("tts_adapter", settings.TTS_ADAPTER),
            "llm_adapter": pipeline_config.get("llm_adapter", settings.LLM_ADAPTER),
            "footage_adapter": pipeline_config.get(
                "footage_adapter", settings.FOOTAGE_ADAPTER
            ),
            "vision_adapter": pipeline_config.get(
                "vision_adapter", settings.VISION_ADAPTER
            ),
            "stt_model": pipeline_config.get("stt_model", "faster-whisper-large-v3"),
            "embedding_model": pipeline_config.get(
                "embedding_model", "SigLIP-B/16"
            ),
            "ffmpeg_version": pipeline_config.get("ffmpeg_version", "6.x"),
        }

    def _format_timings(self, timings: Dict[str, float]) -> Dict[str, Any]:
        """Formats timings with human-readable labels."""
        formatted = {}
        for stage, seconds in timings.items():
            formatted[stage] = {
                "seconds": round(seconds, 2),
                "human": self._seconds_to_human(seconds),
            }

        total = sum(timings.values())
        formatted["total"] = {
            "seconds": round(total, 2),
            "human": self._seconds_to_human(total),
        }
        return formatted

    @staticmethod
    def _seconds_to_human(seconds: float) -> str:
        """Converts seconds to a human-readable string like '2m 15s'."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds // 60)
        secs = seconds % 60
        if minutes < 60:
            return f"{minutes}m {secs:.0f}s"
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m {secs:.0f}s"

    def _estimate_cost(
        self,
        scenes: List[Dict[str, Any]],
        render_results: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Rough cost estimate based on:
        - API calls to stock providers (~$0.00 for free-tier Pexels/Pixabay)
        - TTS synthesis ($0.004/1000 chars approx)
        - LLM inference ($0.002/scene approx)
        - Compute time ($0.001/second of render time)
        """
        n_scenes = len(scenes)
        n_ratios = len(render_results)
        total_text_chars = sum(len(s.get("narration_text", "")) for s in scenes)
        ai_scenes = sum(1 for s in scenes if s.get("ai_generated", False))

        stock_cost = 0.0  # Pexels/Pixabay are free
        tts_cost = (total_text_chars / 1000) * 0.004
        llm_cost = n_scenes * 0.002
        generation_cost = ai_scenes * 0.05  # AI-generated footage
        render_cost = n_scenes * n_ratios * 0.001

        total = stock_cost + tts_cost + llm_cost + generation_cost + render_cost

        return {
            "total_usd": round(total, 4),
            "breakdown": {
                "stock_footage": round(stock_cost, 4),
                "tts_synthesis": round(tts_cost, 4),
                "llm_inference": round(llm_cost, 4),
                "ai_generation": round(generation_cost, 4),
                "compute_render": round(render_cost, 4),
            },
            "currency": "USD",
            "note": "Estimate based on free-tier stock providers and standard pricing",
        }

    def _build_licence_summary(
        self, scenes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregates unique licences used across all scenes."""
        licences: Dict[str, int] = {}
        attributions: List[str] = []

        for scene in scenes:
            lic = scene.get("licence", "Unknown")
            licences[lic] = licences.get(lic, 0) + 1
            attr = scene.get("attribution", "")
            if attr and attr not in attributions:
                attributions.append(attr)

        return {
            "all_commercial_use": all(
                "commercial" in l.lower() or "free" in l.lower() or "pexels" in l.lower()
                for l in licences.keys()
            ),
            "licences_used": licences,
            "unique_attributions": attributions,
        }

    def _build_ai_labels(
        self, scenes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Identifies which scenes used AI-generated content."""
        ai_scenes = [
            {
                "scene_id": s.get("scene_id"),
                "scene_index": s.get("scene_index"),
                "source": s.get("source", "unknown"),
            }
            for s in scenes
            if s.get("ai_generated", False)
        ]

        return {
            "contains_ai_content": len(ai_scenes) > 0,
            "ai_scene_count": len(ai_scenes),
            "total_scene_count": len(scenes),
            "ai_scenes": ai_scenes,
            "disclosure": (
                "This video contains AI-generated footage in "
                f"{len(ai_scenes)} of {len(scenes)} scenes."
                if ai_scenes
                else "No AI-generated footage was used."
            ),
        }

    def _avg_relevance(self, scenes: List[Dict[str, Any]]) -> float:
        """Average relevance score across all scenes."""
        scores = [s.get("relevance_score", 0.0) for s in scenes]
        return round(sum(scores) / max(len(scores), 1), 3)

    def _min_relevance(self, scenes: List[Dict[str, Any]]) -> float:
        """Minimum relevance score across all scenes."""
        scores = [s.get("relevance_score", 0.0) for s in scenes]
        return round(min(scores) if scores else 0.0, 3)


# Module-level singleton
manifest_builder = ManifestBuilder()
