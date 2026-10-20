import pytest
from app.pipeline.runner import pipeline_runner

def test_pipeline_abstract_script():
    script = "Trust is earned slowly through transparent execution and lost in a single instant."
    result = pipeline_runner.execute_stages_1_to_6(
        job_id="test_abstract_job",
        script_text=script,
        voice="en-US-Standard",
        avoid_tags=["watermark"],
        aspect_ratios=["16:9", "9:16"],
    )

    assert result["job_id"] == "test_abstract_job"
    assert len(result["scenes"]) > 0
    assert result["repeat_clip_rate"] == 0.0

    # Verify timeline.json structure
    timeline = result["timeline"]
    assert "scenes" in timeline
    assert timeline["total_duration_seconds"] > 0
    first_scene = timeline["scenes"][0]
    assert "relevance_score" in first_scene
    assert "selection_reason" in first_scene
    assert "source_choice_reason" in first_scene
    assert first_scene["licence"] is not None

def test_pipeline_statistics_script():
    script = "Over 78.5% of modern data centers will migrate to renewable micro-grids by 2030."
    result = pipeline_runner.execute_stages_1_to_6(
        job_id="test_stat_job",
        script_text=script,
    )

    scene = result["scenes"][0]
    assert "analytics" in scene["visual_query"] or "charts" in scene["visual_query"] or "data" in scene["visual_query"]
    assert scene["duration"] >= 2.5

def test_pipeline_brand_safety_script():
    script = "Elon Musk announced that Tesla will open-source its neural telemetry."
    result = pipeline_runner.execute_stages_1_to_6(
        job_id="test_brand_job",
        script_text=script,
    )

    # Compliance check: Warning must be captured
    assert len(result["warnings"]) > 0
    warning_text = " ".join(result["warnings"])
    assert "Biometric and trademark generation blocked" in warning_text

    # Footage must be generic alternative
    scene = result["scenes"][0]
    assert "electric vehicle" in scene["visual_query"] or "clean transportation" in scene["visual_query"]

def test_pipeline_polysemous_script():
    script = "The software developer updated the python script with the database team."
    result = pipeline_runner.execute_stages_1_to_6(
        job_id="test_poly_job",
        script_text=script,
    )

    scene = result["scenes"][0]
    # Disambiguated to tech/coding, NOT a reptile
    assert "code" in scene["visual_query"] or "programmer" in scene["visual_query"]

def test_pipeline_multi_scene_zero_clip_reuse_and_coverage():
    multi_scene_script = (
        "Welcome to the IncuBrix B-roll automation engine. "
        "Our high-performance media pipeline splits audio into meaningful scenes. "
        "Every second of voiceover is perfectly covered with clean commercial footage. "
        "We guarantee zero clip repetition across every rendered aspect ratio."
    )

    result = pipeline_runner.execute_stages_1_to_6(
        job_id="test_multi_scene_job",
        script_text=multi_scene_script,
        aspect_ratios=["16:9", "9:16", "1:1"],
    )

    scenes = result["scenes"]
    assert len(scenes) >= 3

    # Check zero clip reuse
    selected_clip_ids = [s["selected_clip_id"] for s in scenes]
    assert len(selected_clip_ids) == len(set(selected_clip_ids)), f"Duplicate clip reused: {selected_clip_ids}"

    # Check 100% coverage: scene 0 starts at 0.0, each scene[i].end == scene[i+1].start
    assert scenes[0]["start_time"] == 0.0
    for i in range(len(scenes) - 1):
        assert scenes[i]["end_time"] == scenes[i + 1]["start_time"]

    # Minimum scene length check
    for s in scenes:
        assert s["duration"] >= 2.5
