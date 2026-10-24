import urllib.request
import json
import time

payload = {
    "audio_url": "http://localhost:8000/test_pack/audio/vo_01_tech_en.mp3",
    "aspect_ratios": ["16:9", "9:16"],
    "burn_in_captions": True,
    "srt_captions": True,
}

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/broll/jobs",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json", "Idempotency-Key": "voiceover-test-run-2"}
)

with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode())
    job_id = res["job_id"]
    print("Audio Voiceover Job submitted:", job_id)

for attempt in range(40):
    time.sleep(2)
    with urllib.request.urlopen(f"http://127.0.0.1:8000/api/v1/jobs/{job_id}") as poll_r:
        job = json.loads(poll_r.read().decode())
        st = job.get("status")
        if st in ("succeeded", "failed"):
            print("Voiceover Job Status:", st)
            print(f"Total Scenes: {len(job.get('scenes', []))}")
            for sc in job.get("scenes", []):
                print(f"  Scene #{sc['scene_index']+1}: Clip={sc.get('selected_clip_id')} | Provider={sc.get('provider')} | Timing={sc.get('start_time')}s-{sc.get('end_time')}s")
            print("Result URLs:", json.dumps(job.get("result_urls", {}), indent=2))
            break
