import pytest
from app.pipeline.stage3_segment import SceneSegmenter

def test_scene_segmentation_minimum_length():
    segmenter = SceneSegmenter(min_scene_duration=2.5)

    # Transcript with a short sentence followed by longer sentences
    transcript_data = {
        "text": "Yes. Trust is earned slowly. Every enterprise workflow relies on digital infrastructure.",
        "duration": 9.5,
        "words": [
            {"word": "Yes.", "start": 0.2, "end": 0.6},               # Only 0.4s! Must be merged!
            {"word": "Trust", "start": 1.2, "end": 1.6},
            {"word": "is", "start": 1.7, "end": 1.9},
            {"word": "earned", "start": 2.0, "end": 2.4},
            {"word": "slowly.", "start": 2.5, "end": 3.0},
            {"word": "Every", "start": 3.8, "end": 4.2},
            {"word": "enterprise", "start": 4.3, "end": 4.9},
            {"word": "workflow", "start": 5.0, "end": 5.5},
            {"word": "relies", "start": 5.6, "end": 6.0},
            {"word": "on", "start": 6.1, "end": 6.3},
            {"word": "digital", "start": 6.4, "end": 6.8},
            {"word": "infrastructure.", "start": 6.9, "end": 7.8},
        ]
    }

    scenes = segmenter.segment_transcript(transcript_data)
    assert len(scenes) >= 2

    # Verify no scene has duration < 2.5s
    for scene in scenes:
        assert scene["duration"] >= 2.5, f"Scene {scene['scene_index']} is shorter than 2.5s ({scene['duration']}s)"

    # First scene must include "Yes. Trust is earned slowly." because "Yes." was < 2.5s
    assert "Yes" in scenes[0]["text"]
    assert "Trust" in scenes[0]["text"]

def test_complete_temporal_coverage_no_gaps():
    segmenter = SceneSegmenter(min_scene_duration=2.5)

    transcript_data = {
        "text": "First sentence here. Second sentence follows immediately. Third sentence concludes the video.",
        "duration": 12.0,
        "words": [
            {"word": "First", "start": 0.5, "end": 1.0},
            {"word": "sentence", "start": 1.1, "end": 1.6},
            {"word": "here.", "start": 1.7, "end": 2.2},
            {"word": "Second", "start": 3.5, "end": 4.0},
            {"word": "sentence", "start": 4.1, "end": 4.6},
            {"word": "follows", "start": 4.7, "end": 5.2},
            {"word": "immediately.", "start": 5.3, "end": 6.0},
            {"word": "Third", "start": 7.0, "end": 7.5},
            {"word": "sentence", "start": 7.6, "end": 8.0},
            {"word": "concludes", "start": 8.1, "end": 8.6},
            {"word": "the", "start": 8.7, "end": 8.9},
            {"word": "video.", "start": 9.0, "end": 9.5},
        ]
    }

    scenes = segmenter.segment_transcript(transcript_data)

    # 1. Total coverage from 0.0 to 12.0s
    assert scenes[0]["start_time"] == 0.0
    assert scenes[-1]["end_time"] >= 12.0

    # 2. No gaps between consecutive scenes: scene[i].end == scene[i+1].start
    for i in range(len(scenes) - 1):
        assert scenes[i]["end_time"] == scenes[i + 1]["start_time"]

    # 3. Sum of durations equals total time span
    total_coverage = sum(s["duration"] for s in scenes)
    assert round(total_coverage, 1) == round(scenes[-1]["end_time"] - scenes[0]["start_time"], 1)
