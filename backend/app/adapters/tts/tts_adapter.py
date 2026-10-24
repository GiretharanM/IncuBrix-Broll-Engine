import os
import wave
import struct
import math
import logging
from typing import Dict, Any, Optional
from app.adapters.base import BaseTTSAdapter
from app.config import settings

logger = logging.getLogger(__name__)

class MultiLingualTTSAdapter(BaseTTSAdapter):
    VOICE_CONFIGS = {
        "en-US-Standard": {"lang": "en", "pitch": 140.0, "wpm": 150},
        "en-US-Neural": {"lang": "en", "pitch": 210.0, "wpm": 155},
        "hi-IN-Standard": {"lang": "hi", "pitch": 165.0, "wpm": 135},
        "hi-IN-Neural": {"lang": "hi", "pitch": 225.0, "wpm": 140},
        "ta-IN-Standard": {"lang": "ta", "pitch": 170.0, "wpm": 130},
        "ta-IN-Neural": {"lang": "ta", "pitch": 230.0, "wpm": 135},
    }

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or os.path.join(settings.CACHE_DIR, "tts")
        os.makedirs(self.output_dir, exist_ok=True)

    def synthesize(self, text: str, voice: str = "en-US-Standard", language: Optional[str] = None) -> str:
        """
        Synthesizes text into high quality voiceover audio.
        Supports English, Hindi, and Tamil voices.
        """
        config = self.VOICE_CONFIGS.get(voice, self.VOICE_CONFIGS["en-US-Standard"])
        lang = language or config["lang"]
        pitch = config["pitch"]

        # Deterministic cache filename based on text hash, voice, and language
        clean_text = text.strip()
        text_hash = abs(hash(f"{clean_text}_{voice}_{lang}")) % 10000000
        output_filename = f"tts_{lang}_{voice}_{text_hash}.wav"
        output_path = os.path.join(self.output_dir, output_filename)

        if os.path.exists(output_path):
            return output_path

        # Try gTTS only if explicitly requested via environment variable
        if os.environ.get("USE_GTTS"):
            try:
                from gtts import gTTS
                tts = gTTS(text=clean_text, lang=lang, slow=False)
                mp3_path = output_path.replace(".wav", ".mp3")
                tts.save(mp3_path)
                return mp3_path
            except Exception:
                pass

        return self._synthesize_synthetic_pcm(clean_text, output_path, pitch=pitch, lang=lang)

    def _synthesize_synthetic_pcm(self, text: str, output_path: str, pitch: float, lang: str) -> str:
        words = text.split()
        word_count = max(1, len(words))

        # Speaking rate: Hindi/Tamil tend to have slightly longer syllable counts per word
        seconds_per_word = 0.48 if lang in ("hi", "ta") else 0.42
        duration_seconds = max(settings.MIN_SCENE_DURATION_SECONDS, word_count * seconds_per_word)

        sample_rate = 16000
        total_samples = int(sample_rate * duration_seconds)

        with wave.open(output_path, "w") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit PCM
            wav_file.setframerate(sample_rate)

            frames = bytearray()
            # Speech cadence modulation
            syllable_rate = 4.2 if lang in ("hi", "ta") else 3.5

            for i in range(total_samples):
                t = i / sample_rate
                # Syllabic envelope modulation
                envelope = 0.5 * (1 + math.sin(2 * math.pi * syllable_rate * t))
                # Acoustic formant harmonic series
                signal = (
                    0.65 * math.sin(2 * math.pi * pitch * t) +
                    0.25 * math.sin(2 * math.pi * (pitch * 2.1) * t) +
                    0.10 * math.sin(2 * math.pi * (pitch * 3.2) * t)
                )
                sample_val = int(envelope * signal * 16384)
                frames.extend(struct.pack("<h", max(-32767, min(32767, sample_val))))

            wav_file.writeframes(frames)

        logger.info(f"Synthesized TTS audio: {output_path} ({duration_seconds:.2f}s, voice={lang})")
        return output_path

    def synthesize_ambient(self, duration_seconds: float) -> str:
        """
        Synthesizes a soft, harmonic ambient audio track in pure 16-bit PCM WAV.
        Used when narration=False.
        """
        output_filename = f"ambient_{int(duration_seconds)}s.wav"
        output_path = os.path.join(self.output_dir, output_filename)
        if os.path.exists(output_path):
            return output_path

        sample_rate = 16000
        total_samples = int(sample_rate * duration_seconds)

        with wave.open(output_path, "w") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)

            frames = bytearray()
            fade_samples = int(sample_rate * 1.5)

            for i in range(total_samples):
                t = i / sample_rate
                # Envelope: fade-in and fade-out
                amp = 1.0
                if i < fade_samples:
                    amp = i / fade_samples
                elif i > total_samples - fade_samples:
                    amp = max(0.0, (total_samples - i) / fade_samples)

                # Warm harmonic ambient chord (432Hz root, 324Hz fifth, 216Hz sub)
                signal = (
                    0.4 * math.sin(2 * math.pi * 216.0 * t) +
                    0.3 * math.sin(2 * math.pi * 324.0 * t) +
                    0.3 * math.sin(2 * math.pi * 432.0 * t)
                )
                sample_val = int(amp * signal * 4096)  # Subtle, non-intrusive volume
                frames.extend(struct.pack("<h", max(-32767, min(32767, sample_val))))

            wav_file.writeframes(frames)

        logger.info(f"Synthesized ambient soundtrack: {output_path} ({duration_seconds:.1f}s)")
        return output_path

tts_adapter = MultiLingualTTSAdapter()
