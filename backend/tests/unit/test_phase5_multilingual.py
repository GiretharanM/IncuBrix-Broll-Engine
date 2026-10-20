import os
import wave
import pytest
from app.adapters.tts.tts_adapter import MultiLingualTTSAdapter
from app.adapters.stt.whisper_adapter import FasterWhisperSTTAdapter

class TestMultilingualSupport:
    def setup_method(self):
        self.tts = MultiLingualTTSAdapter()
        self.stt = FasterWhisperSTTAdapter()

    def test_hindi_tts_and_language_detection(self):
        hindi_text = "जब विचार और तकनीक एक साथ आते हैं, तो नए अवसर जन्म लेते हैं।"
        audio_path = self.tts.synthesize(text=hindi_text, voice="hi-IN-Standard", language="hi")

        assert os.path.exists(audio_path)
        assert audio_path.endswith((".wav", ".mp3"))

        # Test STT language detection on Hindi Unicode script
        transcript = self.stt.transcribe(audio_path, reference_text=hindi_text)
        assert transcript["language"] == "hi"
        assert len(transcript["words"]) > 0

    def test_tamil_tts_and_language_detection(self):
        tamil_text = "புதிய சிந்தனைகளும் தொழில்நுட்பமும் இணையும்போது சிறந்த சாதனைகள் நிகழ்கின்றன."
        audio_path = self.tts.synthesize(text=tamil_text, voice="ta-IN-Standard", language="ta")

        assert os.path.exists(audio_path)
        assert audio_path.endswith((".wav", ".mp3"))

        # Test STT language detection on Tamil Unicode script
        transcript = self.stt.transcribe(audio_path, reference_text=tamil_text)
        assert transcript["language"] == "ta"
        assert len(transcript["words"]) > 0

    def test_english_standard_tts(self):
        eng_text = "IncuBrix media pipeline generates license clean B-roll videos."
        audio_path = self.tts.synthesize(text=eng_text, voice="en-US-Standard", language="en")

        assert os.path.exists(audio_path)
        transcript = self.stt.transcribe(audio_path, reference_text=eng_text)
        assert transcript["language"] == "en"
        assert len(transcript["words"]) == len(eng_text.split())
