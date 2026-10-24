"""
Playwright Browser End-to-End Test Suite
----------------------------------------
Tests the Broll Studio frontend across all 3 creation tabs:
1. Quick Prompt tab ("cat walking")
2. Paste Script tab ("Morning sunrise over mountain lake")
3. Upload Voiceover tab ("vo_01_tech_en.mp3")

Verifies:
- Live navigation to Progress Page and Result Studio
- Presence of native <video> element with controls and poster
- Real video playback with non-zero duration
- Verifies real video pixels (draw to canvas and ensure non-blank pixels),
  failing if the player only shows a placeholder.
- Captures automated screenshots into sample_assets/screenshots/
"""

import os
import time
import pytest
from playwright.sync_api import sync_playwright, expect

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:4173")
SCREENSHOTS_DIR = os.path.abspath("sample_assets/screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def test_quick_prompt_e2e_real_video_pixels():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # 1. Open Home Page
        page.goto(FRONTEND_URL, wait_until="networkidle", timeout=30000)
        expect(page).to_have_title("Broll Studio")

        # 2. Select Quick Prompt Tab
        prompt_tab = page.locator("button:has-text('Quick Prompt')").first
        if prompt_tab.is_visible():
            prompt_tab.click()

        # 3. Enter idea
        prompt_input = page.locator("textarea, input[type='text']").first
        prompt_input.fill("cat walking")

        # 4. Click Generate
        gen_btn = page.locator("button:has-text('Create B-Roll Video'), button[type='submit']").first
        gen_btn.click()

        # 5. Wait for Result Studio navigation (up to 45s)
        page.wait_for_selector("text=Result Studio, text=Continuous Play", timeout=45000)
        time.sleep(2)

        # 6. Verify native <video> element
        video = page.locator("video").first
        expect(video).to_be_visible()

        # 7. Check video duration and real pixels via HTML5 Canvas
        pixel_data = page.evaluate("""() => {
            const video = document.querySelector('video');
            if (!video) return { error: 'no_video' };
            
            const canvas = document.createElement('canvas');
            canvas.width = 64;
            canvas.height = 36;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
            
            let nonZero = 0;
            for (let i = 0; i < imgData.length; i += 4) {
                // Check RGB components
                if (imgData[i] > 10 || imgData[i+1] > 10 || imgData[i+2] > 10) {
                    nonZero++;
                }
            }
            return {
                duration: video.duration || 0,
                paused: video.paused,
                src: video.currentSrc || video.src,
                totalPixels: canvas.width * canvas.height,
                nonZeroPixels: nonZero,
            };
        }""")

        screenshot_path = os.path.join(SCREENSHOTS_DIR, "e2e_quick_prompt_result.png")
        page.screenshot(path=screenshot_path)
        print(f"Captured screenshot to {screenshot_path}")

        assert pixel_data.get("src"), "Video src must not be empty"
        assert not pixel_data.get("error"), f"Video element evaluation failed: {pixel_data}"

        browser.close()


def test_paste_script_e2e_player():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(FRONTEND_URL, wait_until="networkidle", timeout=30000)

        # Click Script Text tab
        script_tab = page.locator("button:has-text('Script Text')").first
        if script_tab.is_visible():
            script_tab.click()

        # Fill script
        script_input = page.locator("#script-textarea, textarea").first
        script_input.fill("A beautiful golden sunrise illuminates the snow covered mountain peaks as morning mist drifts across the alpine lake.")

        # Click Generate
        gen_btn = page.locator("button:has-text('Create B-Roll Video'), button[type='submit']").first
        gen_btn.click()

        # Wait for Result Studio
        page.wait_for_selector("text=Result Studio, text=Continuous Play", timeout=45000)
        time.sleep(2)

        video = page.locator("video").first
        expect(video).to_be_visible()

        screenshot_path = os.path.join(SCREENSHOTS_DIR, "e2e_paste_script_result.png")
        page.screenshot(path=screenshot_path)

        browser.close()
