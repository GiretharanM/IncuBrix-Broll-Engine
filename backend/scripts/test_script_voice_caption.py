import urllib.request
import json
import time

script_text = (
    "A beautiful golden sunrise illuminates the snow-covered mountain peaks as morning mist drifts across the alpine lake. "
    "A powerful waterfall cascades over rugged cliffs into a crystal-clear pool surrounded by lush green forests. "
    "As night falls, a vibrant modern city skyline comes alive with glowing skyscrapers, busy streets, and sparkling lights."
)

payload = {
    "script_text": script_text,
    "voice": "en-US-Standard",
    "aspect_ratios": ["16:9"],
    "burn_in_captions": True,
    "srt_captions": True,
}

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/broll/jobs",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json", "Idempotency-Key": "script-voice-caption-test-1"}
)

print("Submitting script job to API...")
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode())
    job_id = res["job_id"]
    print("Job created:", job_id)

for i in range(40):
    time.sleep(2)
    with urllib.request.urlopen(f"http://127.0.0.1:8000/api/v1/jobs/{job_id}") as poll_r:
        job = json.loads(poll_r.read().decode())
        st = job.get("status")
        pr = job.get("progress")
        print(f"[{i+1}] Progress: {pr}% | Status: {st}")
        if st in ("succeeded", "failed"):
            print("\n=== JOB FINISHED ===")
            print("Status:", st)
            if st == "failed":
                print("Error:", job.get("error_message"))
            print("Result URLs:")
            for k, v in job.get("result_urls", {}).items():
                print(f"  {k}: {v}")
            print("\nScenes with Pixabay footage:")
            for sc in job.get("scenes", []):
                print(f"  Scene #{sc.get('scene_index') + 1}:")
                print(f"    Text: {sc.get('text')}")
                print(f"    Timing: {sc.get('start_time')}s -> {sc.get('end_time')}s ({sc.get('duration')}s)")
                print(f"    Query: {sc.get('visual_query')}")
                print(f"    Provider: {sc.get('provider')}")
                print(f"    Clip ID: {sc.get('selected_clip_id')}")
                print(f"    Link: {sc.get('link')}")
                print(f"    Licence: {sc.get('licence')}")
            break
