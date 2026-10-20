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
        self.public_endpoint = settings.MINIO_PUBLIC_ENDPOINT
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
        if settings.ENVIRONMENT == "testing":
            return True
        client = self.get_client()
        if not client:
            return False
        bucket = bucket_name or self.default_bucket
        try:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
            return True
        except Exception as e:
            logger.warning(f"Could not verify or create bucket '{bucket}': {e}")
            return False

    def upload_file(self, object_name: str, file_path: str, bucket_name: Optional[str] = None, content_type: str = "application/octet-stream") -> str:
        client = self.get_client()
        bucket = bucket_name or self.default_bucket
        if not client:
            return f"mock://minio/{bucket}/{object_name}"

        self.ensure_bucket(bucket)
        client.fput_object(bucket, object_name, file_path, content_type=content_type)
        return self.get_presigned_url(object_name, bucket)

    def upload_bytes(self, object_name: str, data: bytes, bucket_name: Optional[str] = None, content_type: str = "application/octet-stream") -> str:
        client = self.get_client()
        bucket = bucket_name or self.default_bucket
        if not client:
            return f"mock://minio/{bucket}/{object_name}"

        self.ensure_bucket(bucket)
        data_stream = io.BytesIO(data)
        client.put_object(bucket, object_name, data_stream, length=len(data), content_type=content_type)
        return self.get_presigned_url(object_name, bucket)

    def get_presigned_url(self, object_name: str, bucket_name: Optional[str] = None, expires_seconds: int = 3600) -> str:
        client = self.get_client()
        bucket = bucket_name or self.default_bucket
        if not client:
            return f"http://localhost:9000/{bucket}/{object_name}"

        try:
            url = client.presigned_get_object(
                bucket,
                object_name,
                expires=timedelta(seconds=expires_seconds)
            )
            # Rewrite host if public endpoint differs from internal docker network
            if self.public_endpoint and "minio:" in url:
                url = url.replace("http://minio:9000", self.public_endpoint)
            return url
        except Exception as e:
            logger.warning(f"Presigned URL generation error: {e}")
            return f"{self.public_endpoint}/{bucket}/{object_name}"

    def check_health(self) -> bool:
        if settings.ENVIRONMENT == "testing":
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
