import logging
import time
from datetime import datetime, timezone
from app.tasks.celery_app import celery_app
from app.database import get_sync_db
from app.models import Job

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="process_broll_job")
def process_broll_job(self, job_id: str):
    logger.info(f"Worker received job: {job_id}", extra={"job_id": job_id})
    db = get_sync_db()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found in database", extra={"job_id": job_id})
            return {"status": "error", "message": "Job not found"}

        job.status = "running"
        job.current_stage = "Ingesting"
        job.progress = 10
        db.commit()

        from app.pipeline.runner import pipeline_runner
        from app.models import Scene

        res_dict = pipeline_runner.execute_full_pipeline(
            job_id=job.id,
            prompt=job.prompt,
            duration_seconds=job.duration_seconds or 20,
            narration=job.narration or False,
            seed=job.seed,
            scene_captions_without_narration=job.scene_captions_without_narration or False,
            script_text=job.script_text,
            audio_path=job.audio_url,
            voice=job.voice or "en-US-Standard",
            aspect_ratios=job.aspect_ratios or ["16:9"],
            avoid_tags=job.avoid_tags or [],
            style=job.style or "cinematic",
            burn_in_captions=job.burn_in_captions,
            srt_captions=job.srt_captions,
            upload_to_s3=False,
        )

        for idx, sc in enumerate(res_dict.get("scenes", [])):
            scene_record = Scene(
                job_id=job.id,
                scene_index=idx,
                text=sc.get("text", ""),
                visual_hint=sc.get("visual_hint", ""),
                visual_query=sc.get("visual_query", ""),
                start_time=sc.get("start_time", 0.0),
                end_time=sc.get("end_time", 3.0),
                duration=sc.get("duration", 3.0),
                selected_clip_id=sc.get("selected_clip_id", ""),
                selection_reason=sc.get("selection_reason", ""),
                source_choice_reason=sc.get("source_choice_reason", ""),
                relevance_score=sc.get("relevance_score", 0.88),
                ai_generated=sc.get("ai_generated", False),
                segment_hash=sc.get("segment_hash", ""),
            )
            db.add(scene_record)

        render_res = res_dict.get("render_results", {})
        vid_16x9 = render_res.get("16:9", {}).get("output_path", f"/api/v1/jobs/{job_id}/download/video_16x9.mp4")

        job.status = "succeeded"
        job.progress = 100
        job.current_stage = "Completed"
        job.completed_at = datetime.now(timezone.utc)
        job.result_urls = {
            "video_16x9": vid_16x9,
            "video_9x16": render_res.get("9:16", {}).get("output_path", vid_16x9),
            "video_1x1": render_res.get("1:1", {}).get("output_path", vid_16x9),
            "captions_srt": f"/api/v1/jobs/{job_id}/captions.srt",
            "timeline_json": f"/api/v1/jobs/{job_id}/timeline.json",
            "manifest_json": f"/api/v1/jobs/{job_id}/manifest.json",
        }
        job.warnings = res_dict.get("warnings", [])
        db.commit()
        logger.info(f"Job {job_id} completed successfully via worker", extra={"job_id": job_id})
        return {"status": "succeeded", "job_id": job_id}

    except Exception as e:
        logger.exception(f"Error executing job {job_id}: {e}", extra={"job_id": job_id})
        db.rollback()
        if job:
            job.status = "failed"
            job.error_code = "PIPELINE_ERROR"
            job.error_message = str(e)
            db.commit()
        raise e
    finally:
        db.close()
