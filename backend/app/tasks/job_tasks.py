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

        # In Phase 1, we simulate initial queue transitions and stage updates
        stages = [
            ("Narration Processing", 25),
            ("Scene Segmentation", 45),
            ("Footage Retrieval", 65),
            ("Ranking & Normalisation", 85),
            ("Multi-Ratio Render", 95),
            ("Completed", 100),
        ]

        for stage_name, prog in stages:
            time.sleep(0.5)
            job.current_stage = stage_name
            job.progress = prog
            db.commit()
            logger.info(f"Job {job_id} stage: {stage_name} ({prog}%)", extra={"job_id": job_id})

        job.status = "succeeded"
        job.completed_at = datetime.now(timezone.utc)
        job.result_urls = {
            "video_16x9": f"/api/v1/jobs/{job_id}/download/video_16x9.mp4",
            "captions_srt": f"/api/v1/jobs/{job_id}/download/captions.srt",
            "timeline": f"/api/v1/jobs/{job_id}/download/timeline.json",
            "manifest": f"/api/v1/jobs/{job_id}/download/manifest.json",
        }
        db.commit()
        logger.info(f"Job {job_id} completed successfully", extra={"job_id": job_id})
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
