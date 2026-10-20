import os
import pytest
from httpx import AsyncClient
from cli.metrics import compute_metrics_from_manifests
from cli.export_openapi import export_openapi
from app.models import Job, Scene

@pytest.mark.asyncio
async def test_swap_clip_endpoint_calculates_time_saved(client: AsyncClient, db_session):
    # 1. Create a job with 3 scenes
    job = Job(
        id="job_swap_test_01",
        input_type="script_text",
        status="succeeded",
        progress=100,
        aspect_ratios=["16:9", "9:16"],
    )
    db_session.add(job)

    scenes = [
        Scene(
            id=f"scene_test_{i}",
            job_id=job.id,
            scene_index=i,
            text=f"Scene narration text {i}",
            start_time=float(i * 3.5),
            end_time=float((i + 1) * 3.5),
            duration=3.5,
            selected_clip_id=f"clip_orig_{i}",
            relevance_score=0.85,
        )
        for i in range(3)
    ]
    for s in scenes:
        db_session.add(s)
    await db_session.commit()

    # 2. Call PATCH swap clip on scene 1
    swap_payload = {
        "candidate_id": "cand_handshake_01",
    }
    response = await client.patch(
        f"/api/v1/jobs/{job.id}/scenes/scene_test_1/clip",
        json=swap_payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job.id
    assert data["scene_id"] == "scene_test_1"
    assert data["new_clip_id"] == "cand_handshake_01"
    assert data["time_saved_seconds"] > 0
    assert data["re_render_duration_seconds"] > 0
    assert "partial segment re-rendered from cache" in data["message"]

def test_metrics_script_aggregates_from_folder(tmp_path):
    manifest_data = {
        "quality_metrics": {
            "avg_relevance_score": 0.88,
            "narration_coverage": 1.0,
            "repeat_clip_rate": 0.0,
        },
        "cost_estimate": {
            "total_usd": 0.018,
        },
        "timings": {
            "total_pipeline_seconds": 19.5,
        },
    }
    job_dir = tmp_path / "job_01"
    job_dir.mkdir()
    (job_dir / "manifest.json").write_text(import_json_str(manifest_data), encoding="utf-8")

    metrics = compute_metrics_from_manifests(str(tmp_path))
    assert metrics["total_jobs"] == 1
    assert metrics["succeeded_jobs"] == 1
    assert metrics["narration_coverage_ratio"] == 1.0
    assert metrics["repeat_clip_rate"] == 0.0
    assert metrics["avg_turnaround_seconds"] == 19.5

def test_openapi_exporter_generates_valid_yaml(tmp_path):
    out_yaml = tmp_path / "openapi_test.yaml"
    export_openapi(str(out_yaml))
    assert out_yaml.exists()
    assert out_yaml.stat().st_size > 10000

def import_json_str(d):
    import json
    return json.dumps(d)
