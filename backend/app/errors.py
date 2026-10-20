from fastapi import Request
from fastapi.responses import JSONResponse
from typing import Any, Dict, Optional

class AppException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "retryable": self.retryable,
                "details": self.details,
            }
        }

# Domain Exceptions
class JobNotFoundException(AppException):
    def __init__(self, job_id: str):
        super().__init__(
            code="JOB_NOT_FOUND",
            message=f"Job with ID '{job_id}' does not exist",
            status_code=404,
            retryable=False,
            details={"job_id": job_id},
        )

class SceneNotFoundException(AppException):
    def __init__(self, scene_id: str):
        super().__init__(
            code="SCENE_NOT_FOUND",
            message=f"Scene with ID '{scene_id}' does not exist",
            status_code=404,
            retryable=False,
            details={"scene_id": scene_id},
        )

class InvalidFileTypeException(AppException):
    def __init__(self, filename: str, content_type: str):
        super().__init__(
            code="INVALID_FILE_TYPE",
            message=f"File '{filename}' with content type '{content_type}' is not supported. Supported: mp3, wav, m4a",
            status_code=400,
            retryable=False,
            details={"filename": filename, "content_type": content_type},
        )

class AudioTooLongException(AppException):
    def __init__(self, duration_seconds: float, max_seconds: int = 600):
        super().__init__(
            code="AUDIO_DURATION_EXCEEDED",
            message=f"Audio length of {duration_seconds:.1f}s exceeds maximum limit of {max_seconds}s (10 min)",
            status_code=400,
            retryable=False,
            details={"duration_seconds": duration_seconds, "max_seconds": max_seconds},
        )

class SilentAudioException(AppException):
    def __init__(self, speech_ratio: float = 0.0):
        super().__init__(
            code="SILENT_AUDIO_DETECTED",
            message="Provided audio track contains no detected speech (silence)",
            status_code=422,
            retryable=False,
            details={"speech_ratio": speech_ratio},
        )

class MusicOnlyAudioException(AppException):
    def __init__(self, speech_ratio: float = 0.0):
        super().__init__(
            code="MUSIC_ONLY_AUDIO_DETECTED",
            message="Provided audio track contains background music with no distinguishable voice narration",
            status_code=422,
            retryable=False,
            details={"speech_ratio": speech_ratio},
        )

class EmptyScriptException(AppException):
    def __init__(self):
        super().__init__(
            code="EMPTY_SCRIPT",
            message="The provided script is empty or whitespace-only",
            status_code=400,
            retryable=False,
        )

class ProviderTimeoutException(AppException):
    def __init__(self, provider: str):
        super().__init__(
            code="PROVIDER_TIMEOUT",
            message=f"Footage provider '{provider}' timed out while querying candidates",
            status_code=504,
            retryable=True,
            details={"provider": provider},
        )

class CorruptedDownloadException(AppException):
    def __init__(self, url: str):
        super().__init__(
            code="CORRUPTED_DOWNLOAD",
            message=f"Failed to download or parse media from '{url}'",
            status_code=502,
            retryable=True,
            details={"url": url},
        )

class IdempotencyConflictException(AppException):
    def __init__(self, key: str):
        super().__init__(
            code="IDEMPOTENCY_CONFLICT",
            message=f"A request with Idempotency-Key '{key}' is already currently processing",
            status_code=409,
            retryable=True,
            details={"idempotency_key": key},
        )

class StorageUnavailableException(AppException):
    def __init__(self, message: str = "MinIO storage service unavailable"):
        super().__init__(
            code="STORAGE_UNAVAILABLE",
            message=message,
            status_code=503,
            retryable=True,
        )

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )

async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(exc),
                "retryable": False,
                "details": None,
            }
        },
    )
