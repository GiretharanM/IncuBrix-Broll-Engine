import os
import wave
import struct
import math
import tempfile
from app.adapters.base import BaseTTSAdapter

class MockTTSAdapter(BaseTTSAdapter):
    def __init__(self, output_dir: str = "/tmp/incubrix_cache/tts"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def synthesize(self, text: str, voice: str = "en-US-Standard", language: str = "en") -> str:
        """
        Synthesizes speech audio using deterministic synthetic PCM audio.
        Duration scales with word count (approx 150 words per minute ~ 2.5 words/sec).
        """
        words = text.split()
        word_count = max(1, len(words))
        # ~0.4s per word + padding
        duration_seconds = max(2.5, word_count * 0.45)

        sample_rate = 16000
        total_samples = int(sample_rate * duration_seconds)

        filename = f"tts_{abs(hash(text)) % 1000000}_{voice}.wav"
        file_path = os.path.join(self.output_dir, filename)

        if os.path.exists(file_path):
            return file_path

        # Generate a gentle, pleasant synthetic voice tone with pauses between sentences
        with wave.open(file_path, "w") as wav_file:
            wav_file.setnchannels(1)      # Mono
            wav_file.setsampwidth(2)      # 16-bit
            wav_file.setframerate(sample_rate)

            # Harmonic pitch frequency based on voice
            base_freq = 220.0 if "female" in voice.lower() else 140.0
            frames = bytearray()

            for i in range(total_samples):
                t = i / sample_rate
                # Simulate speech syllabic modulation (3Hz envelope)
                envelope = 0.5 * (1 + math.sin(2 * math.pi * 3 * t))
                # Base voice harmonic
                sample_val = envelope * (
                    0.6 * math.sin(2 * math.pi * base_freq * t) +
                    0.3 * math.sin(2 * math.pi * base_freq * 2 * t)
                )
                int_sample = int(sample_val * 16384)
                frames.extend(struct.pack("<h", max(-32767, min(32767, int_sample))))

            wav_file.writeframes(frames)

        return file_path
