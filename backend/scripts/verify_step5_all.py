import urllib.request
import json
import time

API_BASE = "http://127.0.0.1:8000/api/v1"

def run_job(payload, label):
    print(f"\n==========================================")
    print(f"TEST: {label}")
    print(f"==========================================")
    idempotency_key = f"step5-{abs(hash(label))}-{int(time.time())}"
    req = urllib.request.Request(
        f"{API_BASE}/broll/jobs",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Idempotency-Key": idempotency_key}
    )
    with urllib.request.urlopen(req) as resp:
        job = json.loads(resp.read().decode())
        job_id = job["job_id"]
    print(f"Job ID: {job_id}")

    for _ in range(40):
        time.sleep(2)
        with urllib.request.urlopen(f"{API_BASE}/jobs/{job_id}") as poll_r:
            data = json.loads(poll_r.read().decode())
            st = data.get("status")
            if st in ("succeeded", "failed"):
                print(f"Status: {st}")
                scenes = data.get("scenes", [])
                print(f"Scenes count: {len(scenes)}")
                for idx, sc in enumerate(scenes, 1):
                    print(f"  Scene #{idx}:")
                    print(f"    Text: {sc.get('text')}")
                    print(f"    Visual Query: {sc.get('visual_query')}")
                    print(f"    Clip ID: {sc.get('selected_clip_id')} (Provider: {sc.get('provider')})")
                    print(f"    Link: {sc.get('link')}")
                    print(f"    Relevance Score: {sc.get('relevance_score')}")
                print("Result URLs:", json.dumps(data.get("result_urls", {}), indent=2))
                return data

if __name__ == "__main__":
    # Test 1: Quick Prompt
    p1 = {
        "prompt": "golden retriever running in park",
        "duration_seconds": 12,
        "narration": False,
        "aspect_ratios": ["16:9"]
    }
    run_job(p1, "1. Quick Prompt (golden retriever running in park)")

    # Test 2: Script Text with separate scenes
    p2 = {
        "script_text": (
            "Playful golden retriever puppies run across the green park grass chasing a tennis ball. "
            "A happy dog dives into the cool lake water on a warm sunny afternoon."
        ),
        "voice": "en-US-Standard",
        "aspect_ratios": ["16:9"]
    }
    run_job(p2, "2. Script Text (Two distinct dog scenes)")
