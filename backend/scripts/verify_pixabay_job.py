import urllib.request
import json
import time

payload = {
    "prompt": "sunrise over snow-covered mountains",
    "duration_seconds": 12,
    "narration": False,
    "aspect_ratios": ["16:9"],
}

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/broll/jobs",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json", "Idempotency-Key": "pixabay-live-verify-script-1"}
)

with urllib.request.urlopen(req) as resp:
    init_data = json.loads(resp.read().decode())
    job_id = init_data["job_id"]
    print("Job initiated successfully! Job ID:", job_id)

for attempt in range(40):
    time.sleep(2)
    poll_req = urllib.request.Request(f"http://127.0.0.1:8000/api/v1/jobs/{job_id}")
    with urllib.request.urlopen(poll_req) as p_resp:
        data = json.loads(p_resp.read().decode())
        status = data.get("status")
        progress = data.get("progress")
        stage = data.get("stage")
        print(f"[{attempt+1}] Progress: {progress}% | Stage: {stage} | Status: {status}")

        if status in ("succeeded", "failed"):
            print("\n--- FINAL PIPELINE RESULT ---")
            print("Status:", status)
            if status == "failed":
                print("Error:", data.get("error_message"))
            scenes = data.get("scenes", [])
            print(f"Total Scenes: {len(scenes)}")
            for idx, sc in enumerate(scenes, 1):
                print(f"\nScene #{idx}:")
                print(f"  - Query: {sc.get('visual_query')}")
                print(f"  - Provider: {sc.get('provider')}")
                print(f"  - Clip ID: {sc.get('selected_clip_id')}")
                print(f"  - Page Link: {sc.get('link')}")
                print(f"  - Licence: {sc.get('licence')}")
            print("\nResult URLs:", json.dumps(data.get("result_urls", {}), indent=2))
            break
