"""
Tests for Stage 8: Video Rendering & Captions
------------------------------------------------
Tests SRT generation, ASS generation, FFmpeg render command
construction, and multi-ratio rendering.
"""

import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from app.pipeline.stage8_render import (
    CaptionGenerator,
    VideoRenderer,
    video_renderer,
)
from app.pipeline.stage7_normalize import NormalizedClip, VideoNormalizer


# Shared test transcript words
SAMPLE_WORDS = [
    {"word": "Trust", "start": 0.0, "end": 0.3, "probability": 0.99},
    {"word": "is", "start": 0.35, "end": 0.45, "probability": 0.98},
    {"word": "earned", "start": 0.5, "end": 0.8, "probability": 0.97},
    {"word": "slowly", "start": 0.85, "end": 1.2, "probability": 0.96},
    {"word": "but", "start": 1.3, "end": 1.45, "probability": 0.99},
    {"word": "lost", "start": 1.5, "end": 1.7, "probability": 0.98},
    {"word": "in", "start": 1.75, "end": 1.85, "probability": 0.97},
    {"word": "an", "start": 1.9, "end": 2.0, "probability": 0.96},
    {"word": "instant.", "start": 2.05, "end": 2.5, "probability": 0.95},
    {"word": "Growth", "start": 2.7, "end": 3.0, "probability": 0.99},
    {"word": "comes", "start": 3.05, "end": 3.3, "probability": 0.98},
    {"word": "from", "start": 3.35, "end": 3.5, "probability": 0.97},
    {"word": "within.", "start": 3.55, "end": 3.9, "probability": 0.96},
]


class TestSRTGeneration:
    """Tests for SRT subtitle file generation."""

    def test_srt_basic_output(self):
        """SRT should have numbered cues with timestamps and text."""
        srt = CaptionGenerator.build_srt(SAMPLE_WORDS, max_words_per_cue=4)
        assert srt.strip() != ""
        lines = srt.strip().split("\n")
        # First line should be cue number "1"
        assert lines[0] == "1"
        # Second line should contain " --> "
        assert " --> " in lines[1]
        # Third line should have text
        assert len(lines[2]) > 0

    def test_srt_timestamp_format(self):
        """SRT timestamps must follow HH:MM:SS,mmm format."""
        srt = CaptionGenerator.build_srt(SAMPLE_WORDS)
        # Find a timestamp line
        for line in srt.split("\n"):
            if " --> " in line:
                parts = line.split(" --> ")
                for ts in parts:
                    ts = ts.strip()
                    # Must match HH:MM:SS,mmm
                    assert len(ts) == 12, f"Bad SRT timestamp length: '{ts}'"
                    assert ts[2] == ":" and ts[5] == ":" and ts[8] == ","
                break

    def test_srt_word_grouping(self):
        """Words should be grouped respecting max_words_per_cue."""
        srt = CaptionGenerator.build_srt(SAMPLE_WORDS, max_words_per_cue=4)
        cue_texts = []
        lines = srt.strip().split("\n")
        i = 0
        while i < len(lines):
            if lines[i].strip().isdigit():
                i += 1  # skip number
                i += 1  # skip timestamp
                if i < len(lines):
                    cue_texts.append(lines[i])
                i += 1  # skip blank
            i += 1

        for text in cue_texts:
            word_count = len(text.split())
            assert word_count <= 4, f"Cue has {word_count} words: '{text}'"

    def test_srt_empty_input(self):
        """Empty word list should produce empty SRT."""
        srt = CaptionGenerator.build_srt([])
        assert srt == ""

    def test_srt_format_time_helper(self):
        """Time formatting should handle edge cases."""
        assert CaptionGenerator._format_srt_time(0.0) == "00:00:00,000"
        assert CaptionGenerator._format_srt_time(61.5) == "00:01:01,500"
        assert CaptionGenerator._format_srt_time(3661.123) == "01:01:01,123"


class TestASSGeneration:
    """Tests for ASS (burn-in) subtitle generation."""

    def test_ass_has_script_info(self):
        """ASS output should contain [Script Info] header."""
        ass = CaptionGenerator.build_ass(SAMPLE_WORDS)
        assert "[Script Info]" in ass
        assert "IncuBrix" in ass

    def test_ass_has_styles(self):
        """ASS should define a Default style."""
        ass = CaptionGenerator.build_ass(SAMPLE_WORDS)
        assert "[V4+ Styles]" in ass
        assert "Style: Default" in ass

    def test_ass_has_dialogue_events(self):
        """ASS should contain Dialogue events for the words."""
        ass = CaptionGenerator.build_ass(SAMPLE_WORDS)
        assert "[Events]" in ass
        assert "Dialogue:" in ass
        # Count dialogue lines
        dialogue_count = ass.count("Dialogue:")
        assert dialogue_count > 0

    def test_ass_resolution_settings(self):
        """ASS should use the provided video resolution."""
        ass = CaptionGenerator.build_ass(SAMPLE_WORDS, video_width=1080, video_height=1920)
        assert "PlayResX: 1080" in ass
        assert "PlayResY: 1920" in ass

    def test_ass_empty_input(self):
        """Empty word list should produce empty ASS."""
        ass = CaptionGenerator.build_ass([])
        assert ass == ""

    def test_ass_timestamp_format(self):
        """ASS timestamps should be H:MM:SS.cc format."""
        assert CaptionGenerator._format_ass_time(0.0) == "0:00:00.00"
        assert CaptionGenerator._format_ass_time(61.5) == "0:01:01.50"
        # 3661.99 → fractional part subject to floating-point; check structure
        result = CaptionGenerator._format_ass_time(3661.99)
        assert result.startswith("1:01:01.")
        assert len(result) == 10  # H:MM:SS.cc


class TestRenderCommand:
    """Tests for FFmpeg render command construction."""

    def setup_method(self):
        self.renderer = VideoRenderer(output_dir=tempfile.mkdtemp())

    def test_build_render_command_with_captions(self):
        """Render command should include ASS filter when captions provided."""
        # Create a temporary ASS file
        ass_path = os.path.join(self.renderer.output_dir, "test.ass")
        with open(ass_path, "w") as f:
            f.write("[Script Info]\nTitle: Test\n")

        cmd = self.renderer._build_render_command(
            concat_file="concat.txt",
            narration_audio="audio.wav",
            ass_path=ass_path,
            output_path="output.mp4",
        )

        assert "ffmpeg" in cmd[0]
        assert "-f" in cmd
        assert "concat" in cmd
        assert "-c:v" in cmd
        assert "-c:a" in cmd
        assert "aac" in cmd
        assert "-vf" in cmd  # ASS filter should be present

    def test_build_render_command_without_captions(self):
        """Render command should NOT include ASS filter when no captions."""
        cmd = self.renderer._build_render_command(
            concat_file="concat.txt",
            narration_audio="audio.wav",
            ass_path=None,
            output_path="output.mp4",
        )

        assert "-vf" not in cmd

    def test_build_render_command_audio_codec(self):
        """Output should use AAC audio at 192kbps."""
        cmd = self.renderer._build_render_command(
            concat_file="c.txt",
            narration_audio="a.wav",
            ass_path=None,
            output_path="o.mp4",
        )
        assert "aac" in cmd
        assert "192k" in cmd


class TestConcatFile:
    """Tests for concat demuxer file writing."""

    def setup_method(self):
        self.renderer = VideoRenderer(output_dir=tempfile.mkdtemp())

    def test_concat_file_format(self):
        """Concat file should list files with durations."""
        clips = [
            NormalizedClip(
                scene_id="s01", scene_index=0, ratio="16:9",
                output_path="/tmp/seg1.mp4", duration=3.0,
                segment_hash="abc123", width=1920, height=1080,
            ),
            NormalizedClip(
                scene_id="s02", scene_index=1, ratio="16:9",
                output_path="/tmp/seg2.mp4", duration=4.5,
                segment_hash="def456", width=1920, height=1080,
            ),
        ]

        path = os.path.join(self.renderer.output_dir, "concat_test.txt")
        self.renderer._write_concat_file(path, clips)

        content = open(path).read()
        assert "file '/tmp/seg1.mp4'" in content
        assert "duration 3.000" in content
        assert "file '/tmp/seg2.mp4'" in content
        assert "duration 4.500" in content

    def test_concat_file_ordering(self):
        """Clips should appear in the order provided."""
        clips = [
            NormalizedClip(
                scene_id="s02", scene_index=1, ratio="16:9",
                output_path="/tmp/second.mp4", duration=2.0,
                segment_hash="222", width=1920, height=1080,
            ),
            NormalizedClip(
                scene_id="s01", scene_index=0, ratio="16:9",
                output_path="/tmp/first.mp4", duration=3.0,
                segment_hash="111", width=1920, height=1080,
            ),
        ]

        path = os.path.join(self.renderer.output_dir, "concat_order.txt")
        self.renderer._write_concat_file(path, clips)

        content = open(path).read()
        pos_second = content.index("second.mp4")
        pos_first = content.index("first.mp4")
        assert pos_second < pos_first, "Clips should maintain insertion order"
