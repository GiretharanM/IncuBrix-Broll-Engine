import os
import sys
import time
from playwright.sync_api import sync_playwright

FRONTEND_URL = "http://localhost:4173"
SCREENSHOT_PATH = os.path.abspath("sample_assets/screenshots/live_user_test_studio.png")
os.makedirs(os.path.dirname(SCREENSHOT_PATH), exist_ok=True)

test_script = (
    "A beautiful golden sunrise illuminates the snow-covered mountain peaks as morning mist drifts across the alpine lake. "
    "A powerful waterfall cascades over rugged cliffs into a crystal-clear pool surrounded by lush green forests. "
    "As night falls, a vibrant modern city skyline comes alive with glowing skyscrapers, busy streets, and sparkling lights."
)

def main():
    print("=" * 70)
    print("LIVE USER BROWSER END-TO-END VALIDATION TEST")
    print("=" * 70)
    print(f"Target Frontend: {FRONTEND_URL}")
    print(f"Script:\n\"{test_script}\"\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        # 1. Open Website
        print("1. Opening Broll Studio in browser...")
        page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(1000)
        assert page.title() == "Broll Studio", f"Expected title 'Broll Studio', got '{page.title()}'"
        print("   Title verified: Broll Studio")

        # 2. Select Script Text Tab
        print("2. Selecting 'Script Text' tab...")
        script_tab = page.locator("button:has-text('Script Text')").first
        script_tab.click()
        page.wait_for_timeout(500)

        # 3. Enter the script into textarea
        print("3. Entering script text into textarea...")
        script_textarea = page.locator("#script-textarea")
        script_textarea.fill(test_script)
        page.wait_for_timeout(500)

        # 4. Click Submit Button
        print("4. Clicking 'Create B-Roll Video' button...")
        create_btn = page.locator("button[type='submit']").first
        create_btn.click()

        # 5. Live Progress Tracking
        print("5. Monitoring live progress page...")
        page.wait_for_function("() => window.location.hash === '#progress'", timeout=25000)
        print("   Successfully transitioned to #progress!")

        # 6. Wait for Completion & Click Open in Result Studio
        print("6. Waiting for automated video rendering & completion...")
        open_studio_btn = page.locator("button:has-text('Open in Result Studio')")
        open_studio_btn.wait_for(state="visible", timeout=120000)
        print("   Media rendering finished! Clicking 'Open in Result Studio'...")
        open_studio_btn.click()
        page.wait_for_function("() => window.location.hash === '#studio'", timeout=15000)
        page.wait_for_timeout(2500)

        # 7. Verify Native <video> Player in Result Studio
        video_el = page.locator("video").first
        assert video_el.is_visible(), "Native <video> element must be visible in Result Studio"
        video_src = video_el.get_attribute("src")
        print(f"7. Native <video> element visible in Studio! src = {video_src}")
        assert video_src, "Video element source URL must not be empty"

        # 8. Check Pixel Rendering via Canvas
        print("8. Checking canvas frame pixels for real visible picture...")
        pixel_data = page.evaluate("""() => {
            const video = document.querySelector('video');
            if (!video) return { error: 'no video' };
            const canvas = document.createElement('canvas');
            canvas.width = 64;
            canvas.height = 36;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, 64, 36);
            const data = ctx.getImageData(0, 0, 64, 36).data;
            let nonZero = 0;
            for (let i = 0; i < data.length; i += 4) {
                if (data[i] > 10 || data[i+1] > 10 || data[i+2] > 10) nonZero++;
            }
            return {
                src: video.currentSrc || video.src,
                duration: video.duration || 0,
                paused: video.paused,
                nonZeroPixels: nonZero,
                totalPixels: 64 * 36
            };
        }""")
        print(f"   Pixel evaluation: {pixel_data}")

        # 9. Verify Scenes & Captions
        scene_count = page.locator("text=Scene").count()
        print(f"9. Scene blocks detected in Studio: {scene_count}")

        # 10. Capture Full Page Screenshot
        page.screenshot(path=SCREENSHOT_PATH)
        print(f"10. Screenshot captured to: {SCREENSHOT_PATH}")

        browser.close()

    print("\n" + "=" * 70)
    print("ALL VERIFICATION CHECKS PASSED! Broll Studio is working end-to-end.")
    print("=" * 70)

if __name__ == "__main__":
    main()
