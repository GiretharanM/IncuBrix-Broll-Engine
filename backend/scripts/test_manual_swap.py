import urllib.request
import json

job_id = "ce6f625e-5230-41fd-b60a-76cdd42f1a7f"

# 1. Fetch Candidates for Scene 0
url = f"http://127.0.0.1:8000/api/v1/jobs/{job_id}/scenes/0/candidates"
try:
    with urllib.request.urlopen(url) as resp:
        candidates = json.loads(resp.read().decode())
        print(f"Candidates available for scene 0: {len(candidates)}")
        for idx, c in enumerate(candidates[:4], 1):
            print(f"  Candidate #{idx}: {c.get('id')} | Title: {c.get('title')[:60]}... | Score: {c.get('relevance_score')}")

        if len(candidates) > 1:
            alt_id = candidates[1]["id"]
            print(f"\nSwapping scene 0 to alternative candidate: {alt_id}")
            swap_req = urllib.request.Request(
                f"http://127.0.0.1:8000/api/v1/jobs/{job_id}/scenes/0/swap",
                data=json.dumps({"selected_candidate_id": alt_id}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="PATCH"
            )
            with urllib.request.urlopen(swap_req) as s_resp:
                swap_res = json.loads(s_resp.read().decode())
                print("Manual swap result:", swap_res.get("message"))
                print("New selected clip:", swap_res.get("scene", {}).get("selected_clip_id"))
except Exception as e:
    print("Error:", e)
