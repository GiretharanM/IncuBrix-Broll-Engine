"""
Stage Upload: S3 (MinIO) Upload Orchestration
------------------------------------------------
Uploads all rendered outputs (videos, SRT, timeline.json, manifest.json)
to MinIO object storage and returns presigned download URLs.

Object key structure:
    jobs/{job_id}/video_{ratio}.mp4
    jobs/{job_id}/captions_{ratio}.srt
    jobs/{job_id}/timeline.json
    jobs/{job_id}/manifest.json
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from app.config import settings
from app.storage.minio_client import minio_storage

logger = logging.getLogger(__name__)

# MIME types for output files
CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".srt": "text/plain; charset=utf-8",
    ".ass": "text/plain; charset=utf-8",
    ".json": "application/json",
}


class OutputUploader:
    """
    Uploads all pipeline outputs to MinIO and generates presigned
    download URLs. Handles missing files gracefully with warnings.
    """

    def __init__(self):
        self.storage = minio_storage

    def upload_job_outputs(
        self,
        job_id: str,
        render_results: Dict[str, Dict[str, Any]],
        timeline_data: Dict[str, Any],
        manifest_data: Dict[str, Any],
        timeline_path: Optional[str] = None,
        manifest_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Uploads all output files for a completed job to MinIO.

        Args:
            job_id: Job identifier for object key prefix
            render_results: Per-ratio render results with file paths
            timeline_data: Timeline JSON dict (saved to file if path not given)
            manifest_data: Manifest JSON dict (saved to file if path not given)
            timeline_path: Pre-existing timeline.json path (optional)
            manifest_path: Pre-existing manifest.json path (optional)

        Returns:
            {
                "videos": {ratio: url, ...},
                "captions_srt": {ratio: url, ...},
                "timeline_json": url,
                "manifest_json": url,
                "warnings": [str],
            }
        """
        result_urls: Dict[str, Any] = {
            "videos": {},
            "captions_srt": {},
            "timeline_json": None,
            "manifest_json": None,
            "warnings": [],
        }

        # Upload videos and SRT captions per ratio
        for ratio, render_info in render_results.items():
            ratio_label = ratio.replace(":", "x")

            # Upload video file
            video_path = render_info.get("video_path")
            if video_path and os.path.isfile(video_path):
                video_key = f"jobs/{job_id}/video_{ratio_label}.mp4"
                url = self.storage.upload_file(
                    object_name=video_key,
                    file_path=video_path,
                    content_type="video/mp4",
                )
                result_urls["videos"][ratio] = url
                logger.info("Uploaded video %s → %s", video_key, url[:80])
            else:
                result_urls["warnings"].append(
                    f"Video file missing for ratio {ratio}"
                )

            # Upload SRT caption file
            srt_path = render_info.get("srt_path")
            if srt_path and os.path.isfile(srt_path):
                srt_key = f"jobs/{job_id}/captions_{ratio_label}.srt"
                url = self.storage.upload_file(
                    object_name=srt_key,
                    file_path=srt_path,
                    content_type="text/plain; charset=utf-8",
                )
                result_urls["captions_srt"][ratio] = url
                logger.info("Uploaded SRT %s", srt_key)

        # Upload timeline.json
        timeline_url = self._upload_json(
            job_id, "timeline.json", timeline_data, timeline_path
        )
        result_urls["timeline_json"] = timeline_url

        # Upload manifest.json
        manifest_url = self._upload_json(
            job_id, "manifest.json", manifest_data, manifest_path
        )
        result_urls["manifest_json"] = manifest_url

        logger.info(
            "Upload complete for job %s: %d videos, %d SRTs",
            job_id,
            len(result_urls["videos"]),
            len(result_urls["captions_srt"]),
        )

        return result_urls

    def _upload_json(
        self,
        job_id: str,
        filename: str,
        data: Dict[str, Any],
        existing_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Uploads a JSON file either from an existing path or by
        serialising the data dict directly as bytes.
        """
        object_key = f"jobs/{job_id}/{filename}"

        try:
            if existing_path and os.path.isfile(existing_path):
                return self.storage.upload_file(
                    object_name=object_key,
                    file_path=existing_path,
                    content_type="application/json",
                )
            else:
                json_bytes = json.dumps(
                    data, indent=2, ensure_ascii=False, default=str
                ).encode("utf-8")
                return self.storage.upload_bytes(
                    object_name=object_key,
                    data=json_bytes,
                    content_type="application/json",
                )
        except Exception as e:
            logger.error("Failed to upload %s for job %s: %s", filename, job_id, e)
            return None


# Module-level singleton
output_uploader = OutputUploader()
