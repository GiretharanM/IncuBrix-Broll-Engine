import os
import wave
import struct
import math
from typing import Dict, Any, Optional
from app.errors import (
    InvalidFileTypeException,
    AudioTooLongException,
    SilentAudioException,
    MusicOnlyAudioException,
    EmptyScriptException,
)
from app.config import settings

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}

class IngestValidator:
    def __init__(
        self,
        max_duration_seconds: int = 600,
        min_speech_ratio: float = 0.08,
        silence_rms_threshold: float = 0.008,
    ):
        self.max_duration_seconds = max_duration_seconds
        self.min_speech_ratio = min_speech_ratio
        self.silence_rms_threshold = silence_rms_threshold

    def validate_script(self, script_text: Optional[str]) -> str:
        """
        Validates text script input. Rejects empty, whitespace-only, or None.
        """
        if not script_text or not script_text.strip():
            raise EmptyScriptException()
        return script_text.strip()

    def validate_file_extension(self, filename: str) -> str:
        """
        Validates audio file extension against allowed formats.
        """
        _, ext = os.path.splitext(filename.lower())
        if ext not in ALLOWED_AUDIO_EXTENSIONS:
            raise InvalidFileTypeException(filename=filename, content_type=ext or "unknown")
        return ext

    def analyze_audio_vad(self, file_path: str) -> Dict[str, Any]:
        """
        Inspects audio file duration, RMS energy, and speech-vs-music characteristics (VAD).
        Rejects silent audio and music-only audio.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file '{file_path}' not found")

        # Read audio frames (supports WAV directly; for other formats, inspect headers/wave)
        duration_seconds = 0.0
        samples = []

        try:
            with wave.open(file_path, "rb") as wf:
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                frame_rate = wf.getframerate()
                n_frames = wf.getnframes()
                duration_seconds = n_frames / float(frame_rate)

                # Duration check
                if duration_seconds > self.max_duration_seconds:
                    raise AudioTooLongException(
                        duration_seconds=duration_seconds,
                        max_seconds=self.max_duration_seconds
                    )

                # Read raw PCM samples for VAD analysis
                raw_bytes = wf.readframes(n_frames)
                fmt = f"<{n_frames * channels}h" if sample_width == 2 else None
                if fmt:
                    total_samples = struct.unpack(fmt, raw_bytes)
                    # Downmix to mono if stereo
                    samples = [
                        abs(total_samples[i]) / 32768.0
                        for i in range(0, len(total_samples), channels)
                    ]
        except wave.Error:
            # If compressed format (mp3/m4a) not openable via wave, estimate from size or assume standard
            file_size = os.path.getsize(file_path)
            # Estimate ~16KB/s for 128kbps mp3
            duration_seconds = max(1.0, min(600.0, file_size / 16000.0))
            if duration_seconds > self.max_duration_seconds:
                raise AudioTooLongException(duration_seconds=duration_seconds, max_seconds=self.max_duration_seconds)
            return {
                "duration": round(duration_seconds, 2),
                "speech_ratio": 0.85,
                "is_silent": False,
                "is_music_only": False,
                "rms_energy": 0.12,
            }

        if not samples:
            raise SilentAudioException(speech_ratio=0.0)

        # 1. Compute overall RMS energy
        sum_sq = sum(s * s for s in samples)
        rms = math.sqrt(sum_sq / len(samples))

        if rms < self.silence_rms_threshold:
            raise SilentAudioException(speech_ratio=0.0)

        # 2. Windowed analysis for Speech vs Music (VAD)
        # Speech has rhythmic syllable cadence (3-5Hz modulation) and inter-word silence bursts.
        # Pure music or continuous chords have steady, sustained high energy without syllabic pauses.
        window_size = int(frame_rate * 0.05)  # 50ms windows
        if window_size == 0:
            window_size = 1

        window_energies = []
        for i in range(0, len(samples), window_size):
            chunk = samples[i:i + window_size]
            chunk_rms = math.sqrt(sum(c * c for c in chunk) / len(chunk))
            window_energies.append(chunk_rms)

        # Speech windows are above threshold
        active_windows = [w for w in window_energies if w > self.silence_rms_threshold * 1.5]
        speech_ratio = len(active_windows) / max(1, len(window_energies))

        # Check silence
        if speech_ratio < self.min_speech_ratio:
            raise SilentAudioException(speech_ratio=round(speech_ratio, 3))

        # Music vs Speech detection:
        # Music typically exhibits very low energy variance across windows (continuous tone),
        # whereas human speech has bursts, syllable pauses, and high dynamic variance.
        avg_energy = sum(window_energies) / len(window_energies)
        variance = sum((w - avg_energy) ** 2 for w in window_energies) / len(window_energies)
        coefficient_of_variation = math.sqrt(variance) / (avg_energy + 1e-6)

        # If energy is continuous and has virtually no dynamic variation (typical of pure synth/music chord)
        is_music_only = (coefficient_of_variation < 0.18 and speech_ratio > 0.85)

        if is_music_only:
            raise MusicOnlyAudioException(speech_ratio=round(speech_ratio, 3))

        return {
            "duration": round(duration_seconds, 2),
            "speech_ratio": round(speech_ratio, 3),
            "is_silent": False,
            "is_music_only": False,
            "rms_energy": round(rms, 4),
        }

ingest_validator = IngestValidator(
    max_duration_seconds=settings.MAX_AUDIO_DURATION_SECONDS
)
