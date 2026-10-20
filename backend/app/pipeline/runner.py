"""
Pipeline Runner — Full Orchestrator (Stages 1–10)
---------------------------------------------------
Executes the complete B-roll video production pipeline:

  Stage 1:  Ingest & VAD validation
  Stage 2:  Speech Synthesis (TTS) or Transcription (STT)
  Stage 3:  Semantic Scene Segmentation
  Stage 4:  Query Understanding (metaphors, stats, brand safety)
  Stage 5:  Multi-Provider Footage Retrieval
  Stage 6:  Ranking & Zero-Reuse Allocation
  Stage 7:  FFmpeg Normalisation (resolution, fps, smart crop, colour)
  Stage 8:  Render (concat, narration overlay, captions)
  Stage 9:  (Available via ClipSwapper for PATCH swap-a-clip)
  Stage 10: Manifest generation
  Upload:   S3/MinIO upload with presigned download URLs
  QA:       Automated output quality verification
"""

import logging
import os
import time
from typing import Dict, Any, List, Optional, Set

from app.pipeline.stage1_ingest import ingest_validator
from app.adapters.stt.whisper_adapter import whisper_adapter
from app.adapters.tts.tts_adapter import tts_adapter
from app.pipeline.stage3_segment import scene_segmenter
from app.adapters.llm.query_adapter import query_understanding_adapter
from app.pipeline.stage5_retrieval import footage_retrieval_engine
from app.pipeline.stage6_ranking import candidate_ranker
from app.pipeline.timeline import timeline_builder
from app.pipeline.stage7_normalize import video_normalizer, NormalizedClip
from app.pipeline.stage8_render import video_renderer
from app.pipeline.stage10_manifest import manifest_builder
from app.pipeline.stage_upload import output_uploader
from app.pipeline.qa_checks import output_qa_checker

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
        self.normalizer = video_normalizer
        self.renderer = video_renderer
        self.manifest = manifest_builder
        self.uploader = output_uploader
        self.qa = output_qa_checker

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

    def execute_stages_7_to_10(
        self,
        job_id: str,
        stage_1_to_6_result: Dict[str, Any],
        aspect_ratios: List[str],
        clip_paths: Dict[str, str],
        burn_in_captions: bool = True,
        srt_captions: bool = True,
        voice: str = "en-US-Standard",
        style: str = "cinematic",
        avoid_tags: Optional[List[str]] = None,
        upload_to_s3: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes pipeline stages 7 through 10 + upload + QA:

        7. FFmpeg normalisation (resolution, fps, smart crop, colour matching)
        8. Render (concat + narration overlay + captions)
        10. Manifest generation
        Upload: S3/MinIO upload
        QA: Automated output quality verification

        Args:
            job_id: Job identifier
            stage_1_to_6_result: Output from execute_stages_1_to_6()
            aspect_ratios: Target ratios (e.g. ["16:9", "9:16"])
            clip_paths: Dict mapping clip_id → local file path
            burn_in_captions: Whether to burn ASS subtitles into video
            srt_captions: Whether to generate SRT caption files
            voice: Voice used (for manifest)
            style: Style preset (for manifest)
            avoid_tags: Avoid tags (for manifest)
            upload_to_s3: Whether to upload results to MinIO

        Returns:
            Complete pipeline result with download URLs, QA reports, manifest
        """
        timings: Dict[str, float] = {}
        warnings = list(stage_1_to_6_result.get("warnings", []))
        scenes = stage_1_to_6_result["scenes"]
        transcript = stage_1_to_6_result["transcript"]
        audio_path = stage_1_to_6_result["audio_path"]
        timeline_data = stage_1_to_6_result["timeline"]
        transcript_words = transcript.get("words", [])
        narration_duration = transcript.get("duration", 0.0)

        # -------------------------------------------------------
        # Stage 7: FFmpeg Normalisation
        # -------------------------------------------------------
        t0 = time.time()
        normalized_by_ratio = self.normalizer.normalize_all_scenes(
            scenes=scenes,
            clip_paths=clip_paths,
            ratios=aspect_ratios,
            colour_normalize=True,
        )
        timings["stage_7_normalize"] = time.time() - t0

        # Collect normalisation warnings
        for ratio_clips in normalized_by_ratio.values():
            for clip in ratio_clips:
                for w in clip.warnings:
                    if w not in ("cache_hit",):
                        warnings.append(w)

        # -------------------------------------------------------
        # Stage 8: Render (concat + narration + captions)
        # -------------------------------------------------------
        t0 = time.time()
        render_results = self.renderer.render_all_ratios(
            job_id=job_id,
            normalized_clips_by_ratio=normalized_by_ratio,
            narration_audio_path=audio_path,
            transcript_words=transcript_words,
            burn_in_captions=burn_in_captions,
            srt_captions=srt_captions,
        )
        timings["stage_8_render"] = time.time() - t0

        # Collect render warnings
        for ratio, info in render_results.items():
            warnings.extend(info.get("warnings", []))

        # -------------------------------------------------------
        # Stage 10: Manifest
        # -------------------------------------------------------
        t0 = time.time()
        pipeline_config = {
            "voice": voice,
            "style": style,
            "aspect_ratios": aspect_ratios,
            "burn_in_captions": burn_in_captions,
            "srt_captions": srt_captions,
            "avoid_tags": avoid_tags or [],
        }

        manifest_data = self.manifest.build_manifest(
            job_id=job_id,
            timeline_data=timeline_data,
            render_results=render_results,
            pipeline_config=pipeline_config,
            timings=timings,
            warnings=warnings,
        )

        # Save manifest to disk
        output_dir = os.path.join(
            self.renderer.output_dir, job_id
        )
        manifest_path = self.manifest.save_manifest(
            manifest_data, output_dir, job_id
        )
        timings["stage_10_manifest"] = time.time() - t0

        # -------------------------------------------------------
        # QA Checks
        # -------------------------------------------------------
        t0 = time.time()
        qa_reports = self.qa.run_full_qa(
            job_id=job_id,
            render_results=render_results,
            timeline_data=timeline_data,
            narration_duration=narration_duration,
        )
        timings["qa_checks"] = time.time() - t0

        # Collect QA warnings
        for ratio, report in qa_reports.items():
            warnings.extend(report.warnings)
            warnings.extend(report.errors)

        # -------------------------------------------------------
        # Upload to S3/MinIO
        # -------------------------------------------------------
        result_urls: Dict[str, Any] = {}
        if upload_to_s3:
            t0 = time.time()
            result_urls = self.uploader.upload_job_outputs(
                job_id=job_id,
                render_results=render_results,
                timeline_data=timeline_data,
                manifest_data=manifest_data,
                manifest_path=manifest_path,
            )
            timings["upload"] = time.time() - t0
            warnings.extend(result_urls.get("warnings", []))

        return {
            "job_id": job_id,
            "render_results": render_results,
            "manifest": manifest_data,
            "manifest_path": manifest_path,
            "timeline": timeline_data,
            "qa_reports": {r: rpt.summary() for r, rpt in qa_reports.items()},
            "result_urls": result_urls,
            "warnings": warnings,
            "timings": timings,
            "normalized_segments": normalized_by_ratio,
        }

    def execute_full_pipeline(
        self,
        job_id: str,
        script_text: Optional[str] = None,
        audio_path: Optional[str] = None,
        voice: str = "en-US-Standard",
        avoid_tags: Optional[List[str]] = None,
        aspect_ratios: Optional[List[str]] = None,
        predefined_scenes: Optional[List[Dict[str, Any]]] = None,
        burn_in_captions: bool = True,
        srt_captions: bool = True,
        style: str = "cinematic",
        clip_paths: Optional[Dict[str, str]] = None,
        upload_to_s3: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes the complete pipeline from ingest to delivery.

        This is the top-level method that chains stages 1-6 → 7-10.
        In production, clip_paths are populated by downloading footage
        from the URLs returned by stage 5. For testing with mock adapters,
        clip_paths can be pre-populated or left empty (triggering fallback cards).
        """
        ratios = aspect_ratios or ["16:9"]

        # Stages 1-6
        stage_1_6 = self.execute_stages_1_to_6(
            job_id=job_id,
            script_text=script_text,
            audio_path=audio_path,
            voice=voice,
            avoid_tags=avoid_tags,
            aspect_ratios=ratios,
            predefined_scenes=predefined_scenes,
        )

        # Build clip_paths mapping (in real pipeline, this downloads clips)
        if clip_paths is None:
            clip_paths = {}

        # Stages 7-10 + Upload + QA
        stage_7_10 = self.execute_stages_7_to_10(
            job_id=job_id,
            stage_1_to_6_result=stage_1_6,
            aspect_ratios=ratios,
            clip_paths=clip_paths,
            burn_in_captions=burn_in_captions,
            srt_captions=srt_captions,
            voice=voice,
            style=style,
            avoid_tags=avoid_tags,
            upload_to_s3=upload_to_s3,
        )

        # Merge results
        return {
            **stage_1_6,
            **stage_7_10,
        }

pipeline_runner = PipelineRunner()
