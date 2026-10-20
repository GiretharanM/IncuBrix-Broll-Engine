import pytest
from app.config import Settings
from app.errors import (
    AppException,
    JobNotFoundException,
    SceneNotFoundException,
    InvalidFileTypeException,
    SilentAudioException,
    MusicOnlyAudioException,
    EmptyScriptException,
    IdempotencyConflictException,
)

def test_settings_defaults():
    settings = Settings()
    assert settings.PORT == 8000
    assert settings.STT_ADAPTER == "mock"
    assert settings.MIN_SCENE_DURATION_SECONDS == 2.5
    assert settings.STOCK_SELECTION_THRESHOLD == 0.28

def test_custom_exception_structure():
    exc = AppException(
        code="TEST_ERROR",
        message="This is a test failure",
        status_code=400,
        retryable=True,
        details={"foo": "bar"}
    )
    data = exc.to_dict()
    assert "error" in data
    assert data["error"]["code"] == "TEST_ERROR"
    assert data["error"]["message"] == "This is a test failure"
    assert data["error"]["retryable"] is True
    assert data["error"]["details"] == {"foo": "bar"}

def test_domain_exceptions():
    job_err = JobNotFoundException("job-123")
    assert job_err.code == "JOB_NOT_FOUND"
    assert job_err.status_code == 404
    assert job_err.details["job_id"] == "job-123"

    scene_err = SceneNotFoundException("scene-456")
    assert scene_err.code == "SCENE_NOT_FOUND"
    assert scene_err.status_code == 404

    file_err = InvalidFileTypeException("bad.exe", "application/octet-stream")
    assert file_err.code == "INVALID_FILE_TYPE"
    assert file_err.status_code == 400

    silent_err = SilentAudioException(speech_ratio=0.01)
    assert silent_err.code == "SILENT_AUDIO_DETECTED"
    assert silent_err.status_code == 422

    music_err = MusicOnlyAudioException(speech_ratio=0.04)
    assert music_err.code == "MUSIC_ONLY_AUDIO_DETECTED"
    assert music_err.status_code == 422

    empty_script = EmptyScriptException()
    assert empty_script.code == "EMPTY_SCRIPT"
    assert empty_script.status_code == 400

    idem_err = IdempotencyConflictException("idem-key-999")
    assert idem_err.code == "IDEMPOTENCY_CONFLICT"
    assert idem_err.status_code == 409
    assert idem_err.retryable is True
