import pytest
import os
import wave
import struct
import math
from app.pipeline.stage1_ingest import IngestValidator
from app.errors import (
    InvalidFileTypeException,
    AudioTooLongException,
    SilentAudioException,
    MusicOnlyAudioException,
    EmptyScriptException,
)

@pytest.fixture
def validator():
    return IngestValidator(max_duration_seconds=600)

def test_script_validation_empty(validator):
    with pytest.raises(EmptyScriptException):
        validator.validate_script("")

    with pytest.raises(EmptyScriptException):
        validator.validate_script("   \n\t  ")

def test_script_validation_valid(validator):
    cleaned = validator.validate_script("  Valid narration text for B-roll.  ")
    assert cleaned == "Valid narration text for B-roll."

def test_file_extension_validation(validator):
    assert validator.validate_file_extension("audio.mp3") == ".mp3"
    assert validator.validate_file_extension("speech.wav") == ".wav"
    assert validator.validate_file_extension("voice.m4a") == ".m4a"

    with pytest.raises(InvalidFileTypeException):
        validator.validate_file_extension("malicious.exe")

    with pytest.raises(InvalidFileTypeException):
        validator.validate_file_extension("document.pdf")

def test_silence_audio_detection(validator):
    # Using generated sample silent audio
    silent_path = "sample_assets/audio/silent.wav"
    assert os.path.exists(silent_path)
    with pytest.raises(SilentAudioException):
        validator.analyze_audio_vad(silent_path)

def test_music_only_audio_detection(validator):
    # Using generated sample music-only audio (constant chords without speech pauses)
    music_path = "sample_assets/audio/music_only.wav"
    assert os.path.exists(music_path)
    with pytest.raises(MusicOnlyAudioException):
        validator.analyze_audio_vad(music_path)

def test_clean_speech_vad(validator):
    # Using clean speech audio
    speech_path = "sample_assets/audio/clean_voice.wav"
    assert os.path.exists(speech_path)
    meta = validator.analyze_audio_vad(speech_path)
    assert meta["is_silent"] is False
    assert meta["is_music_only"] is False
    assert meta["speech_ratio"] > 0.08
    assert meta["duration"] > 0

def test_duration_exceeded_rejection(tmp_path):
    # Create an audio file that exceeds 600s
    long_path = os.path.join(tmp_path, "long_audio.wav")
    with wave.open(long_path, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(8000)
        chunk = b"\x30\x30" * 8000  # 1 second of non-silent signal
        for _ in range(605):
            f.writeframes(chunk)

    val = IngestValidator(max_duration_seconds=600)
    with pytest.raises(AudioTooLongException):
        val.analyze_audio_vad(long_path)
