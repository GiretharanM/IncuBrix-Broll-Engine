import urllib.request
import json
import urllib.parse

def test_endpoint(q):
    url = f"http://127.0.0.1:8000/api/v1/footage/test?query={urllib.parse.quote(q)}&count=5"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            hits = data.get("hits", [])
            print(f"\n=== Diagnostic Endpoint for: '{q}' ===")
            print(f"HTTP Status: {resp.status}")
            print(f"Number of results returned: {len(hits)}")
            valid_urls = [
                (h.get("download_url") or h.get("preview_url"))
                for h in hits
                if (h.get("download_url") or h.get("preview_url", "")).startswith("http")
            ]
            print(f"Number of valid video URLs: {len(valid_urls)}")
            for idx, h in enumerate(hits, 1):
                vid_url = h.get("download_url") or h.get("preview_url")
                print(f"  #{idx}: ID={h.get('id')}, Duration={h.get('duration')}s, Res={h.get('resolution')}")
                print(f"      Title: {h.get('title')}")
                print(f"      Video URL: {vid_url}")
    except Exception as e:
        print(f"Error testing '{q}': {e}")

if __name__ == "__main__":
    test_endpoint("golden retriever playing in a park")
    test_endpoint("puppies running on grass")
    test_endpoint("dogs running on a beach")
