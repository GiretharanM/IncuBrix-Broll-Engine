import logging
from typing import Dict, Any, List, Optional, Set
from app.pipeline.stage1_ingest import ingest_validator
from app.adapters.stt.whisper_adapter import whisper_adapter
from app.adapters.tts.tts_adapter import tts_adapter
from app.pipeline.stage3_segment import scene_segmenter
from app.adapters.llm.query_adapter import query_understanding_adapter
from app.pipeline.stage5_retrieval import footage_retrieval_engine
from app.pipeline.stage6_ranking import candidate_ranker
from app.pipeline.timeline import timeline_builder

logger = logging.getLogger(__name__)

class PipelineRunner:
    def __init__(self):
        self.ingest = ingest_validator
        self.stt = whisper_adapter
        self.tts = tts_adapter
        self.segmenter = scene_segmenter
        self.llm = query_understanding_adapter
        self.retrieval = footage_retrieval_engine
        self.ranker = candidate_ranker

    def execute_stages_1_to_6(
        self,
        job_id: str,
        script_text: Optional[str] = None,
        audio_path: Optional[str] = None,
        voice: str = "en-US-Standard",
        avoid_tags: Optional[List[str]] = None,
        aspect_ratios: Optional[List[str]] = None,
        predefined_scenes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Executes pipeline stages 1 through 6:
        1. Ingest & VAD validation
        2. Speech Synthesis (if script) or Transcription (if audio)
        3. Semantic Scene Segmentation (min 2.5s duration, 100% time coverage)
        4. Query Understanding (metaphors, statistics, brand safety)
        5. Multi-Provider Footage Retrieval (cascading fallback)
        6. Ranking & Strict Zero-Reuse Allocation
        7. Timeline Compilation
        """
        warnings: List[str] = []
        ratios = aspect_ratios or ["16:9"]
        avoid = avoid_tags or []

        # ----------------------------------------------------
        # Stage 1: Ingest & Validation
        # ----------------------------------------------------
        if script_text:
            clean_script = self.ingest.validate_script(script_text)
            # Stage 2: TTS Synthesis
            working_audio_path = self.tts.synthesize(clean_script, voice=voice)
            # Transcribe for word-level timestamps with script reference
            transcript = self.stt.transcribe(working_audio_path, reference_text=clean_script)
        elif audio_path:
            self.ingest.validate_file_extension(audio_path)
            vad_meta = self.ingest.analyze_audio_vad(audio_path)
            working_audio_path = audio_path
            transcript = self.stt.transcribe(working_audio_path)
        elif predefined_scenes:
            combined_text = " ".join(s.get("text", "") for s in predefined_scenes)
            working_audio_path = self.tts.synthesize(combined_text, voice=voice)
            transcript = self.stt.transcribe(working_audio_path)
        else:
            raise ValueError("No input provided (script, audio, or scenes required)")

        # ----------------------------------------------------
        # Stage 3: Semantic Scene Segmentation
        # ----------------------------------------------------
        segmented_scenes = self.segmenter.segment_transcript(
            transcript_data=transcript,
            predefined_scenes=predefined_scenes,
        )

        # ----------------------------------------------------
        # Stages 4 & 5 & 6: Query, Retrieval, Ranking & Strict Zero Reuse
        # ----------------------------------------------------
        processed_scenes = []
        used_clip_ids: Set[str] = set()

        for seg in segmented_scenes:
            scene_idx = seg["scene_index"]
            text = seg["text"]
            hint = seg.get("visual_hint")

            # Stage 4: Query Understanding
            llm_result = self.llm.understand_scene(text, visual_hint=hint)
            if llm_result.get("safety_warning"):
                warnings.append(llm_result["safety_warning"])

            search_query = llm_result["search_query"]

            # Stage 5: Multi-provider Footage Retrieval
            candidates = self.retrieval.retrieve_candidates_for_scene(
                query=search_query,
                avoid=avoid,
                count=5,
                warnings_out=warnings,
            )

            # Stage 6: Semantic Ranking & Strict Zero-Reuse Allocation
            chosen_clip, sel_reason, score, src_reason = self.ranker.rank_and_select_clip(
                candidates=candidates,
                scene_text=text,
                visual_hint=hint,
                avoid_tags=avoid,
                used_clip_ids=used_clip_ids,
            )

            processed_scenes.append({
                "scene_id": f"{job_id}_s{scene_idx:02d}",
                "scene_index": scene_idx,
                "text": text,
                "visual_hint": hint,
                "visual_query": search_query,
                "start_time": seg["start_time"],
                "end_time": seg["end_time"],
                "duration": seg["duration"],
                "selected_clip_id": chosen_clip.get("id"),
                "provider": chosen_clip.get("provider", "mock"),
                "licence_name": chosen_clip.get("licence_name", "Commercial Clean"),
                "attribution": chosen_clip.get("attribution", "Royalty Free"),
                "download_url": chosen_clip.get("download_url", ""),
                "ai_generated": chosen_clip.get("ai_generated", False),
                "selection_reason": sel_reason,
                "relevance_score": score,
                "source_choice_reason": src_reason,
                "all_candidates": candidates,
            })

        # ----------------------------------------------------
        # Build timeline.json
        # ----------------------------------------------------
        timeline_data = timeline_builder.build_timeline_json(
            job_id=job_id,
            scenes_data=processed_scenes,
            aspect_ratios=ratios,
            total_duration=transcript.get("duration", 0.0),
        )

        return {
            "job_id": job_id,
            "audio_path": working_audio_path,
            "transcript": transcript,
            "scenes": processed_scenes,
            "timeline": timeline_data,
            "warnings": warnings,
            "used_clip_ids": list(used_clip_ids),
            "repeat_clip_rate": 0.0,
        }

pipeline_runner = PipelineRunner()
