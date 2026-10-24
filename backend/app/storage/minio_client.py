import os
import io
import logging
from typing import Optional, Dict
from datetime import timedelta
from app.config import settings

logger = logging.getLogger(__name__)

class MinIOStorage:
    def __init__(self):
        self.endpoint = settings.MINIO_ENDPOINT
        self.public_endpoint = getattr(settings, "STORAGE_PUBLIC_URL", None) or settings.MINIO_PUBLIC_ENDPOINT or "http://localhost:8000"
        self.access_key = settings.MINIO_ROOT_USER
        self.secret_key = settings.MINIO_ROOT_PASSWORD
        self.use_ssl = settings.MINIO_USE_SSL
        self.default_bucket = settings.MINIO_BUCKET_NAME
        self._client = None

    def get_client(self):
        if self._client is None:
            try:
                from minio import Minio
                self._client = Minio(
                    self.endpoint,
                    access_key=self.access_key,
                    secret_key=self.secret_key,
                    secure=self.use_ssl,
                )
            except Exception as e:
                logger.warning(f"MinIO client initialization warning: {e}")
                return None
        return self._client

    def ensure_bucket(self, bucket_name: Optional[str] = None) -> bool:
        if settings.ENVIRONMENT in ("testing", "development") and (self.endpoint.startswith("minio:") or not os.environ.get("USE_REAL_MINIO")):
            return True
        client = self.get_client()
        if not client:
            return False
        bucket = bucket_name or self.default_bucket
        try:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)

            # Configure public read and CORS policy on MinIO bucket
            try:
                import json
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                            "Resource": [f"arn:aws:s3:::{bucket}"]
                        },
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{bucket}/*"]
                        }
                    ]
                }
                client.set_bucket_policy(bucket, json.dumps(policy))
            except Exception as pe:
                logger.debug(f"Bucket policy setup note: {pe}")

            return True
        except Exception as e:
            logger.warning(f"Could not verify or create bucket '{bucket}': {e}")
            return False

    def upload_file(self, object_name: str, file_path: str, bucket_name: Optional[str] = None, content_type: Optional[str] = None) -> str:
        client = self.get_client()
        bucket = bucket_name or self.default_bucket
        if content_type is None:
            content_type = "video/mp4" if object_name.endswith(".mp4") else "application/octet-stream"

        if not client:
            return self.get_presigned_url(object_name, bucket)

        self.ensure_bucket(bucket)
        client.fput_object(bucket, object_name, file_path, content_type=content_type)
        return self.get_presigned_url(object_name, bucket)

    def upload_bytes(self, object_name: str, data: bytes, bucket_name: Optional[str] = None, content_type: str = "application/octet-stream") -> str:
        client = self.get_client()
        bucket = bucket_name or self.default_bucket
        if not client:
            return self.get_presigned_url(object_name, bucket)

        self.ensure_bucket(bucket)
        data_stream = io.BytesIO(data)
        client.put_object(bucket, object_name, data_stream, length=len(data), content_type=content_type)
        return self.get_presigned_url(object_name, bucket)

    def get_presigned_url(self, object_name: str, bucket_name: Optional[str] = None, expires_seconds: int = 3600) -> str:
        client = self.get_client()
        bucket = bucket_name or self.default_bucket
        public_base = self.public_endpoint.rstrip("/")

        if not client or (settings.ENVIRONMENT in ("testing", "development") and (self.endpoint.startswith("minio:") or not os.environ.get("USE_REAL_MINIO"))):
            # Return streaming URL via public API endpoint
            # E.g. jobs/123/video_16x9.mp4 -> http://localhost:8000/api/v1/jobs/123/download/video_16x9.mp4
            if object_name.startswith("jobs/"):
                parts = object_name.split("/", 2)
                if len(parts) >= 3:
                    job_id, fname = parts[1], parts[2]
                    return f"{public_base}/api/v1/jobs/{job_id}/download/{fname}"
            return f"{public_base}/api/v1/download/{object_name}"

        try:
            extra_query = {}
            if object_name.endswith(".mp4"):
                extra_query["response-content-type"] = "video/mp4"

            url = client.presigned_get_object(
                bucket,
                object_name,
                expires=timedelta(seconds=expires_seconds),
                extra_query_params=extra_query if extra_query else None,
            )
            # Rewrite host if public endpoint differs from internal docker network
            if "minio:" in url:
                url = url.replace("http://minio:9000", public_base).replace("minio:9000", public_base.replace("http://", "").replace("https://", ""))
            return url
        except Exception as e:
            logger.warning(f"Presigned URL generation error: {e}")
            if object_name.startswith("jobs/"):
                parts = object_name.split("/", 2)
                if len(parts) >= 3:
                    return f"{public_base}/api/v1/jobs/{parts[1]}/download/{parts[2]}"
            return f"{public_base}/{bucket}/{object_name}"

    def check_health(self) -> bool:
        if settings.ENVIRONMENT in ("testing", "development") and (self.endpoint.startswith("minio:") or not os.environ.get("USE_REAL_MINIO")):
            return True
        client = self.get_client()
        if not client:
            return False
        try:
            client.list_buckets()
            return True
        except Exception:
            return False

minio_storage = MinIOStorage()
