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
from app.pipeline.prompt_expansion import prompt_expander
from app.config import settings

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
        prompt: Optional[str] = None,
        duration_seconds: int = 20,
        narration: bool = False,
        seed: Optional[int] = None,
        scene_captions_without_narration: bool = False,
        script_text: Optional[str] = None,
        audio_path: Optional[str] = None,
        voice: str = "en-US-Standard",
        avoid_tags: Optional[List[str]] = None,
        aspect_ratios: Optional[List[str]] = None,
        predefined_scenes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Executes pipeline stages 1 through 6:
        1. Ingest & Validation (or Quick Prompt expansion)
        2. Speech Synthesis (TTS) / Ambient Soundtrack Generation
        3. Semantic Scene Segmentation
        4. Query Understanding
        5. Multi-Provider Footage Retrieval (cascading 3-tier queries, stop at first passing query)
        6. Ranking & 2-Tier Selection (threshold + floor) with Strict Zero-Reuse
        7. Timeline Compilation
        """
        warnings: List[str] = []
        ratios = aspect_ratios or ["16:9"]
        avoid = avoid_tags or []

        # ----------------------------------------------------
        # Stage 1: Ingest, Prompt Expansion & Audio Preparation
        # ----------------------------------------------------
        if prompt:
            expansion = prompt_expander.expand_prompt(
                prompt=prompt,
                duration_seconds=duration_seconds,
                narration=narration,
                seed=seed,
                avoid_tags=avoid,
            )
            warnings.extend(expansion.get("warnings", []))

            if narration:
                combined_script = " ".join(s["text"] for s in expansion["scenes"])
                working_audio_path = self.tts.synthesize(combined_script, voice=voice)
                transcript = self.stt.transcribe(working_audio_path, reference_text=combined_script)
                segmented_scenes = self.segmenter.segment_transcript(
                    transcript_data=transcript,
                    predefined_scenes=expansion["scenes"],
                )
            else:
                # Ambient audio track (CC0 / harmonic synthesis recorded in SOURCES.md)
                working_audio_path = self.tts.synthesize_ambient(duration_seconds=float(duration_seconds))

                words = []
                if scene_captions_without_narration:
                    for s in expansion["scenes"]:
                        sc_words = s["text"].split()
                        sc_dur = s["duration"]
                        w_dur = sc_dur / max(1, len(sc_words))
                        w_start = s["start_time"]
                        for w in sc_words:
                            words.append({"word": w, "start": round(w_start, 2), "end": round(w_start + w_dur, 2), "confidence": 1.0})
                            w_start += w_dur

                transcript = {
                    "duration": float(duration_seconds),
                    "words": words,
                    "text": prompt,
                    "language": "en",
                }
                segmented_scenes = expansion["scenes"]

        elif script_text:
            clean_script = self.ingest.validate_script(script_text)
            working_audio_path = self.tts.synthesize(clean_script, voice=voice)
            transcript = self.stt.transcribe(working_audio_path, reference_text=clean_script)
            segmented_scenes = self.segmenter.segment_transcript(
                transcript_data=transcript,
                predefined_scenes=predefined_scenes,
            )
        elif audio_path:
            clean_audio_path = audio_path
            if clean_audio_path.startswith("http://") or clean_audio_path.startswith("https://"):
                if "test_pack/" in clean_audio_path:
                    local_rel = clean_audio_path.split("test_pack/", 1)[1]
                    clean_audio_path = os.path.join("test_pack", local_rel)
                else:
                    try:
                        import urllib.request
                        local_tmp = os.path.join(settings.CACHE_DIR, "downloads", os.path.basename(clean_audio_path))
                        os.makedirs(os.path.dirname(local_tmp), exist_ok=True)
                        urllib.request.urlretrieve(clean_audio_path, local_tmp)
                        clean_audio_path = local_tmp
                    except Exception:
                        from app.errors import CorruptedDownloadException
                        raise CorruptedDownloadException(url=clean_audio_path)

            self.ingest.validate_file_extension(clean_audio_path)
            vad_meta = self.ingest.analyze_audio_vad(clean_audio_path)
            working_audio_path = clean_audio_path
            transcript = self.stt.transcribe(working_audio_path)
            segmented_scenes = self.segmenter.segment_transcript(
                transcript_data=transcript,
                predefined_scenes=predefined_scenes,
            )
        elif predefined_scenes:
            combined_text = " ".join(s.get("text", "") for s in predefined_scenes)
            working_audio_path = self.tts.synthesize(combined_text, voice=voice)
            transcript = self.stt.transcribe(working_audio_path)
            segmented_scenes = self.segmenter.segment_transcript(
                transcript_data=transcript,
                predefined_scenes=predefined_scenes,
            )
        else:
            raise ValueError("No input provided (prompt, script, audio, or scenes required)")

        # ----------------------------------------------------
        # Stages 4 & 5 & 6: Query, Cascading Retrieval, Ranking & Strict Zero Reuse
        # ----------------------------------------------------
        processed_scenes = []
        used_clip_ids: Set[str] = set()

        for seg in segmented_scenes:
            scene_idx = seg["scene_index"]
            text = seg["text"]
            hint = seg.get("visual_hint")

            queries_to_try = seg.get("search_queries")
            if not queries_to_try:
                # Stage 4: Query Understanding
                llm_result = self.llm.understand_scene(text, visual_hint=hint)
                if llm_result.get("safety_warning"):
                    warnings.append(llm_result["safety_warning"])
                queries_to_try = [llm_result["search_query"]]

            # Rule 7: Try queries in order. Stop at the FIRST passing query!
            all_candidates = []
            chosen_query = queries_to_try[0]

            for q in queries_to_try:
                candidates = self.retrieval.retrieve_candidates_for_scene(
                    query=q,
                    avoid=avoid,
                    count=5,
                    warnings_out=warnings,
                    duration=seg["duration"],
                )
                logger.info(
                    "Scene %d retrieval: query='%s', count=%d, providers=%s",
                    scene_idx + 1, q, len(candidates),
                    list({c.get("provider") for c in candidates})
                )
                # Compute semantic alignment for candidates against scene text
                for c in candidates:
                    c["relevance_score"] = self.ranker.vision_scorer.score_relevance(c, text, hint)
                all_candidates.extend(candidates)

                # Stop at first query that yields candidates clearing primary threshold
                passed = [
                    c for c in candidates
                    if (c.get("id") or c.get("external_id")) not in used_clip_ids
                    and c.get("relevance_score", 0.0) >= self.ranker.stock_threshold
                ]
                if passed:
                    chosen_query = q
                    break  # Stop at first passing query!

            # Stage 6: Semantic Ranking & 2-Tier Selection
            chosen_clip, sel_reason, score, src_reason = self.ranker.rank_and_select_clip(
                candidates=all_candidates,
                scene_text=text,
                visual_hint=hint,
                avoid_tags=avoid,
                used_clip_ids=used_clip_ids,
                warnings_out=warnings,
                scene_index=scene_idx,
                queries_tried=queries_to_try,
            )

            is_fallback = (
                chosen_clip.get("provider") in ("fallback_title_card", "generative")
                or "fallback" in str(chosen_clip.get("id", "")).lower()
            )

            cand_page_url = chosen_clip.get("pageURL") or chosen_clip.get("page_url") or ""
            cand_uploader = chosen_clip.get("uploader") or ("None (System Fallback)" if is_fallback else "Stock Contributor")
            cand_licence = chosen_clip.get("licence_name") or chosen_clip.get("licence") or ("None (System Fallback)" if is_fallback else "Commercial Stock License")
            cand_attribution = chosen_clip.get("attribution") or (f"Fallback card generated for Scene {scene_idx + 1} ({chosen_query})" if is_fallback else "Royalty Free")

            logger.info(
                "Scene %d selection: clip_id=%s, provider=%s, score=%.3f, fallback=%s, uploader='%s'",
                scene_idx + 1, chosen_clip.get("id"), chosen_clip.get("provider"), score, is_fallback, cand_uploader
            )

            processed_scenes.append({
                "scene_id": f"{job_id}_s{scene_idx:02d}",
                "scene_index": scene_idx,
                "text": text,
                "visual_hint": hint,
                "visual_query": chosen_query,
                "prompt": prompt or text,
                "start_time": seg["start_time"],
                "end_time": seg["end_time"],
                "duration": seg["duration"],
                "selected_clip_id": chosen_clip.get("id"),
                "preview_url": chosen_clip.get("preview_url") or chosen_clip.get("download_url", ""),
                "provider": chosen_clip.get("provider", "mock"),
                "licence_name": cand_licence,
                "attribution": cand_attribution,
                "download_url": chosen_clip.get("download_url", ""),
                "page_url": cand_page_url,
                "selected_candidate": chosen_clip,
                "ai_generated": chosen_clip.get("ai_generated", False),
                "selection_reason": sel_reason,
                "relevance_score": score,
                "source_choice_reason": src_reason,
                "candidates": all_candidates,
                "all_candidates": all_candidates,
            })

        # Calculate fallback percentage across all scenes
        fallback_scenes = [
            s for s in processed_scenes
            if s.get("provider") in ("fallback_title_card", "generative")
            or "fallback" in str(s.get("selected_clip_id", "")).lower()
        ]
        fallback_ratio = len(fallback_scenes) / max(len(processed_scenes), 1)
        if fallback_ratio > 0.30:
            pct = int(fallback_ratio * 100)
            high_fallback_msg = (
                f"HIGH_FALLBACK_RATE: {len(fallback_scenes)} of {len(processed_scenes)} scenes ({pct}%) "
                f"used fallback cards rather than authentic stock footage."
            )
            warnings.append(high_fallback_msg)
            logger.warning(high_fallback_msg)

        for fs in fallback_scenes:
            warn_scene = (
                f"Scene {fs['scene_index'] + 1}: Used fallback card because {fs.get('source_choice_reason', 'no suitable footage met relevance threshold')}."
            )
            if warn_scene not in warnings:
                warnings.append(warn_scene)

        # ----------------------------------------------------
        # Build timeline.json
        # ----------------------------------------------------
        timeline_data = timeline_builder.build_timeline_json(
            job_id=job_id,
            scenes_data=processed_scenes,
            aspect_ratios=ratios,
            total_duration=transcript.get("duration", 0.0),
            prompt=prompt,
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
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Executes pipeline stages 7 through 10 + upload + QA:
        7. FFmpeg normalisation (resolution, fps, smart crop, colour matching)
        8. Render (concat + narration overlay + captions)
        10. Manifest generation (with seed, timings, cost_estimate)
        Upload: S3/MinIO upload
        QA: Automated output quality verification
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
        prompt_text = stage_1_to_6_result.get("timeline", {}).get("prompt", "")
        script_full_text = transcript.get("full_text", "") or prompt_text or ""
        normalized_by_ratio = self.normalizer.normalize_all_scenes(
            scenes=scenes,
            clip_paths=clip_paths,
            ratios=aspect_ratios,
            colour_normalize=True,
            script_text=script_full_text,
            prompt=prompt_text,
            seed=seed,
            voice=voice,
            style=style,
            avoid_tags=avoid_tags,
            provider=settings.FOOTAGE_PROVIDERS.split(",")[0] if settings.FOOTAGE_PROVIDERS else "pixabay",
            settings_version=settings.SETTINGS_VERSION,
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
            "seed": seed,
        }

        manifest_data = self.manifest.build_manifest(
            job_id=job_id,
            timeline_data=timeline_data,
            render_results=render_results,
            pipeline_config=pipeline_config,
            timings=timings,
            warnings=warnings,
            seed=seed,
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
        prompt: Optional[str] = None,
        duration_seconds: int = 20,
        narration: bool = False,
        seed: Optional[int] = None,
        scene_captions_without_narration: bool = False,
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
        Supports Quick Prompt (1-click generation) as well as full scripts and voiceovers.
        """
        ratios = aspect_ratios or ["16:9"]

        # Stages 1-6
        stage_1_6 = self.execute_stages_1_to_6(
            job_id=job_id,
            prompt=prompt,
            duration_seconds=duration_seconds,
            narration=narration,
            seed=seed,
            scene_captions_without_narration=scene_captions_without_narration,
            script_text=script_text,
            audio_path=audio_path,
            voice=voice,
            avoid_tags=avoid_tags,
            aspect_ratios=ratios,
            predefined_scenes=predefined_scenes,
        )

        # Build clip_paths mapping (download remote clips to local storage cache)
        if clip_paths is None:
            clip_paths = {}

        for sc in stage_1_6.get("scenes", []):
            cand = sc.get("selected_candidate") or {}
            c_id = sc.get("selected_clip_id") or cand.get("id")
            d_url = cand.get("download_url") or cand.get("preview_url")
            if c_id and c_id not in clip_paths and d_url and str(d_url).startswith("http"):
                try:
                    local_p = self.retrieval.pixabay.download_clip(d_url, c_id)
                    clip_paths[c_id] = local_p
                except Exception as e:
                    logger.warning(f"Could not download footage clip {c_id}: {e}")

        # If narration is false and scene captions without narration is false, disable captions burn-in
        effective_burn_in = burn_in_captions
        effective_srt = srt_captions
        if prompt and not narration and not scene_captions_without_narration:
            effective_burn_in = False
            effective_srt = False

        # Stages 7-10 + Upload + QA
        stage_7_10 = self.execute_stages_7_to_10(
            job_id=job_id,
            stage_1_to_6_result=stage_1_6,
            aspect_ratios=ratios,
            clip_paths=clip_paths,
            burn_in_captions=effective_burn_in,
            srt_captions=effective_srt,
            voice=voice,
            style=style,
            avoid_tags=avoid_tags,
            upload_to_s3=upload_to_s3,
            seed=seed,
        )

        # Merge results
        return {
            **stage_1_6,
            **stage_7_10,
        }

pipeline_runner = PipelineRunner()
