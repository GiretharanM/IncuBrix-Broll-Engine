import urllib.request
import json
import time
import uuid

# 1. Submit Quick Prompt job
idem_key = str(uuid.uuid4())
req_body = {
    "prompt": "A joyful golden retriever puppy runs through lush green grass, chases a red tennis ball, and leaps happily into a lake.",
    "aspect_ratio": "16:9",
    "voice_id": "en_male_1",
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
print(f"Created Job: {job_id}")

# 2. Poll until completed
for _ in range(45):
    time.sleep(2)
    st = json.loads(urllib.request.urlopen(f"http://127.0.0.1:8000/api/v1/jobs/{job_id}").read().decode())
    status = st.get("status")
    print(f"  Status: {status} | Progress: {st.get('progress')}% | Stage: {st.get('current_stage')}")
    if status in ("succeeded", "failed"):
        break

if status != "succeeded":
    print("Job did not succeed:", st.get("error_message"))
    exit(1)

print("\n--- JOB SUCCESSFUL ---")
print("Result URLs:", st.get("result_urls"))
for idx, s in enumerate(st.get("scenes", [])):
    print(f"  Scene {idx}: query='{s.get('visual_query')}' -> clip='{s.get('selected_clip_id')}' (provider={s.get('provider')}, score={s.get('relevance_score')})")

# 3. Test Candidate Retrieval for Scene 0
cand_url = f"http://127.0.0.1:8000/api/v1/jobs/{job_id}/candidates/0"
try:
    candidates = json.loads(urllib.request.urlopen(cand_url).read().decode())
    print(f"\nCandidates stored for Scene 0: {len(candidates)}")
    for c in candidates:
        print(f"  - ID: {c.get('id')} | Ext: {c.get('external_id')} | Title: {c.get('title')[:50]}... | Score: {c.get('relevance_score')} | is_selected={c.get('is_selected')}")

    # 4. Perform Manual Swap if alternative candidates exist
    if len(candidates) > 1:
        alt_cand = candidates[1]
        print(f"\nExecuting manual clip swap for Scene 0 to alternative candidate: {alt_cand.get('id')} ({alt_cand.get('title')})")
        swap_req = urllib.request.Request(
            f"http://127.0.0.1:8000/api/v1/jobs/{job_id}/scenes/0/clip",
            data=json.dumps({"candidate_id": alt_cand.get("id")}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="PATCH"
        )
        swap_resp = json.loads(urllib.request.urlopen(swap_req).read().decode())
        print("Swap Response:", swap_resp)
except Exception as e:
    print("Candidates/Swap Error:", e)
