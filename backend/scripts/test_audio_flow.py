import urllib.request
import json
import time
import uuid
import os

audio_path = os.path.abspath("sample_assets/audio/clean_voice.wav")

idem_key = str(uuid.uuid4())
req_body = {
    "audio_url": audio_path,
    "aspect_ratios": ["16:9"],
    "style": "cinematic"
}
req = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/broll/jobs",
    data=json.dumps(req_body).encode("utf-8"),
    headers={"Content-Type": "application/json", "Idempotency-Key": idem_key},
    method="POST"
)
resp = json.loads(urllib.request.urlopen(req).read().decode())
job_id = resp["job_id"]
print(f"Created Audio Voiceover Job: {job_id}")

for _ in range(35):
    time.sleep(2)
    st = json.loads(urllib.request.urlopen(f"http://127.0.0.1:8000/api/v1/jobs/{job_id}").read().decode())
    status = st.get("status")
    print(f"  Status: {status} | Progress: {st.get('progress')}% | Stage: {st.get('current_stage')}")
    if status in ("succeeded", "failed"):
        break

print("\n--- AUDIO JOB RESULT ---")
print("Status:", st.get("status"))
print("Result URLs:", st.get("result_urls"))
for idx, s in enumerate(st.get("scenes", [])):
    print(f"  Scene {idx}: query='{s.get('visual_query')}' -> clip='{s.get('selected_clip_id')}' (provider={s.get('provider')}, score={s.get('relevance_score')})")
