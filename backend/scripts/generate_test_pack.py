"""
Generate Test Pack (/test_pack)
-------------------------------
Generates a comprehensive, reproducible test pack of at least 30 varied inputs:
- 12 scripts (tutorial, news, promo, story, finance, health, travel, tech, abstract, stats, double-meaning, named entity)
- 8 voiceovers (EN, HI, TA across WAV, MP3, M4A from 20s to 5m)
- 6 quick prompts
- 4 edge cases (sad news, extreme crop 9:16, scene list JSON, same-script-different-voice)
- 6 failure cases (silent audio, music-only, corrupted mp3, wrong file type, empty script, empty prompt)
- tests.yaml specifying 70/30 train/held-out split assigned by category, aspect ratios, expected outcomes, and semantic checks.
"""

import os
import sys
import wave
import struct
import math
import subprocess
import yaml
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.adapters.tts.tts_adapter import MultiLingualTTSAdapter
from app.pipeline.stage7_normalize import find_ffmpeg_binary

FFMPEG = find_ffmpeg_binary("ffmpeg")
TEST_PACK_DIR = Path("test_pack")
SCRIPTS_DIR = TEST_PACK_DIR / "scripts"
AUDIO_DIR = TEST_PACK_DIR / "audio"
EDGE_DIR = TEST_PACK_DIR / "edge_cases"
FAILURES_DIR = TEST_PACK_DIR / "failures"

for d in [SCRIPTS_DIR, AUDIO_DIR, EDGE_DIR, FAILURES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

tts = MultiLingualTTSAdapter(output_dir=str(AUDIO_DIR))

# ====================================================================
# 1. SCRIPTS (12 items)
# ====================================================================
SCRIPTS = {
    "script_01_tutorial": (
        "In this developer tutorial, we configure an automated Python workflow. "
        "We install the core libraries, configure environmental variables, and run our first integration test pipeline. "
        "Each command executes directly in your local development workspace for seamless testing.",
        "train", "16:9"
    ),
    "script_02_news": (
        "Global technology markets experienced notable movements today as cloud computing investments expanded rapidly. "
        "Industry analysts reported significant gains across enterprise software and automated infrastructure sectors.",
        "train", "16:9"
    ),
    "script_03_promo": (
        "Unlock seamless collaboration with our new cloud productivity suite. "
        "Work in real time with remote team members across the globe, share documents instantly, and accelerate your creative output.",
        "held_out", "9:16"
    ),
    "script_04_story": (
        "At sunrise, the young marathoner laced her running shoes and stepped out into the crisp morning fog. "
        "Every stride pushed through the steep winding mountain trails, driven by relentless dedication and steady discipline.",
        "train", "16:9"
    ),
    "script_05_finance": (
        "Prudent portfolio diversification remains essential in dynamic market environments. "
        "Disciplined asset allocation, comprehensive risk management, and long-term index investments yield sustainable compound returns.",
        "held_out", "1:1"
    ),
    "script_06_health": (
        "Healthy daily habits start with morning hydration, clean nutrition, and regular aerobic movement. "
        "Prioritizing deep restorative sleep and mindful stress reduction dramatically enhances long-term energy and physical vitality.",
        "train", "16:9"
    ),
    "script_07_travel": (
        "Explore the vibrant energy of Tokyo streets at night, surrounded by neon signs, historic shrines, and tranquil bamboo gardens. "
        "Travel opens our horizons to diverse traditions and breathtaking natural landscapes.",
        "held_out", "9:16"
    ),
    "script_08_tech": (
        "Advanced industrial robotics are transforming modern precision manufacturing. "
        "High-speed automated arms assemble intricate mechanical components with nanometer precision and uninterrupted reliability.",
        "train", "16:9"
    ),
    "script_09_abstract": (
        "Creative ideas emerge like resilient seeds germinating in fertile soil. "
        "With patience, iterative focus, and relentless curiosity, abstract thoughts transform into groundbreaking architectural marvels.",
        "held_out", "1:1"
    ),
    "script_10_stats": (
        "Enterprise revenue grew 40% in 2025 across international regions. "
        "Key operational metrics demonstrated a 25% efficiency surge, surpassing initial quarterly projections.",
        "train", "16:9"
    ),
    "script_11_double_meaning": (
        "We deposited our software package into the code bank and deployed it to the cloud. "
        "Using our wireless mouse, we wrote an automated script in python that calculates customer lifetime value.",
        "held_out", "16:9"
    ),
    "script_12_named_entity": (
        "Elon Musk spoke at the technology symposium regarding electric transportation, while Apple announced new workstation hardware.",
        "train", "9:16"
    ),
}

# ====================================================================
# 2. VOICEOVER GENERATOR (8 items)
# ====================================================================
def convert_audio(src_path: str, dst_path: str):
    """Converts WAV to MP3 or M4A using ffmpeg."""
    if os.path.exists(dst_path):
        return dst_path
    cmd = [FFMPEG, "-y", "-i", src_path, "-c:a", "aac" if dst_path.endswith(".m4a") else "libmp3lame", dst_path]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return dst_path

def generate_tone_wav(path: str, duration: float, freq: float = 440.0, is_music: bool = False):
    """Generates synthetic tone or musical arpeggio."""
    sample_rate = 16000
    total_samples = int(sample_rate * duration)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        frames = bytearray()
        for i in range(total_samples):
            t = i / sample_rate
            if is_music:
                # Musical arpeggio C-E-G chord without formant speech envelope
                chord_freq = 261.63 * (1.25 ** (int(t * 4) % 4))
                sig = 0.5 * math.sin(2 * math.pi * chord_freq * t)
            else:
                sig = 0.5 * math.sin(2 * math.pi * freq * t)
            sample_val = int(sig * 16384)
            frames.extend(struct.pack("<h", max(-32767, min(32767, sample_val))))
        w.writeframes(frames)
    return path

# ====================================================================
# 3. EDGE CASES & FAILURES
# ====================================================================
def build_all_assets():
    print("Generating scripts...")
    for sid, (text, split, ratio) in SCRIPTS.items():
        p = SCRIPTS_DIR / f"{sid}.txt"
        p.write_text(text, encoding="utf-8")

    print("Generating voiceovers (EN, HI, TA in WAV/MP3/M4A)...")
    vo_specs = [
        ("vo_01_tech_en", SCRIPTS["script_01_tutorial"][0], "en-US-Standard", "en", ".mp3", "train", "16:9"),
        ("vo_02_health_hi", "स्वस्थ जीवन के लिए दैनिक व्यायाम, संतुलित आहार और पर्याप्त जलपान अत्यंत आवश्यक है। यह हमारे शरीर को ऊर्जा प्रदान करता है।", "hi-IN-Standard", "hi", ".wav", "train", "16:9"),
        ("vo_03_travel_ta", "டோக்கியோ நகரின் இரவுக் காட்சிகள் மற்றும் வரலாற்றுத் தளங்கள் நம் பயணத்தை அற்புதமாக மாற்றுகின்றன. இயற்கை அழகை ரசிப்போம்.", "ta-IN-Standard", "ta", ".m4a", "held_out", "9:16"),
        ("vo_04_finance_en", SCRIPTS["script_05_finance"][0], "en-US-Standard", "en", ".wav", "held_out", "1:1"),
        ("vo_05_story_hi", "सुबह के समय दौड़ना और पर्वत की चोटियों को देखना जीवन में नई उमंग और ताजगी भर देता है। कठिन परिश्रम से लक्ष्य प्राप्त होता है।", "hi-IN-Neural", "hi", ".mp3", "train", "16:9"),
        ("vo_06_tutorial_ta", "மென்பொருள் உருவாக்கத்தில் கணினி கட்டளைகள் மற்றும் தானியங்கி அமைப்புகள் வேகமான வளர்ச்சியைத் தருகின்றன.", "ta-IN-Neural", "ta", ".wav", "train", "16:9"),
        ("vo_07_news_en", SCRIPTS["script_02_news"][0], "en-US-Neural", "en", ".m4a", "held_out", "16:9"),
        ("vo_08_long_5min", (SCRIPTS["script_06_health"][0] + " ") * 10, "en-US-Standard", "en", ".mp3", "train", "16:9"),
    ]

    for vo_id, text, voice, lang, ext, split, ratio in vo_specs:
        raw_wav = tts.synthesize(text, voice=voice, language=lang)
        final_path = AUDIO_DIR / f"{vo_id}{ext}"
        if ext == ".wav":
            if str(final_path) != raw_wav:
                import shutil
                shutil.copyfile(raw_wav, str(final_path))
        else:
            convert_audio(raw_wav, str(final_path))

    print("Generating edge cases...")
    # 1. Sad news
    (EDGE_DIR / "edge_01_sad_news.txt").write_text(
        "Doctors and nurses worked tirelessly through the night at the regional hospital, providing compassionate care to patients recovering from unexpected illness.",
        encoding="utf-8"
    )
    # 2. Extreme crop 9:16
    (EDGE_DIR / "edge_02_extreme_crop_9x16.txt").write_text(
        "A lone hiker stands at the far edge of the rugged cliff overlooking a vast ocean panorama.",
        encoding="utf-8"
    )
    # 3. Scene list JSON
    scene_list = [
        {"scene_index": 0, "text": "Sun rising over mist-covered lake", "visual_hint": "sunrise alpine lake calm waters", "duration": 4.0},
        {"scene_index": 1, "text": "Mountain peaks glowing with golden morning light", "visual_hint": "snow mountain peaks golden hour", "duration": 4.0},
        {"scene_index": 2, "text": "Pine forest canopy in gentle wind", "visual_hint": "evergreen pine trees aerial forest", "duration": 4.0},
    ]
    import json
    (EDGE_DIR / "edge_03_scene_list.json").write_text(json.dumps(scene_list, indent=2), encoding="utf-8")

    # 4. Same script different voice
    common_text = "Modern architecture incorporates sustainable timber, expansive glass facades, and passive solar illumination."
    (EDGE_DIR / "edge_04_same_script_voice_a.txt").write_text(common_text, encoding="utf-8")
    (EDGE_DIR / "edge_04_same_script_voice_b.txt").write_text(common_text, encoding="utf-8")

    print("Generating failure cases...")
    # 1. Silent audio
    silent_wav = FAILURES_DIR / "fail_01_silent.wav"
    with wave.open(str(silent_wav), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(bytes(16000 * 2 * 3)) # 3 seconds of zero amplitude

    # 2. Music only audio
    music_wav = FAILURES_DIR / "fail_02_music_only.wav"
    generate_tone_wav(str(music_wav), duration=4.0, is_music=True)

    # 3. Corrupted MP3
    corrupt_mp3 = FAILURES_DIR / "fail_03_corrupted.mp3"
    corrupt_mp3.write_bytes(b"\xFF\xFB\x90\x44" + b"CORRUPTED_TRUNCATED_GARBAGE_BYTES_12345" * 10)

    # 4. Wrong file type
    wrong_file = FAILURES_DIR / "fail_04_wrong_type.pdf"
    wrong_file.write_text("%PDF-1.4 dummy document bytes for invalid file test", encoding="utf-8")

    # 5. Empty script
    empty_script = FAILURES_DIR / "fail_05_empty_script.txt"
    empty_script.write_text("   \n\t  \n", encoding="utf-8")

    # 6. Empty prompt
    empty_prompt = FAILURES_DIR / "fail_06_empty_prompt.txt"
    empty_prompt.write_text("   ", encoding="utf-8")

    # ====================================================================
    # 4. BUILD tests.yaml
    # ====================================================================
    print("Assembling tests.yaml with 70/30 split and assertions...")
    tests = []

    # Add 12 scripts
    for sid, (text, split, ratio) in SCRIPTS.items():
        entry = {
            "id": sid,
            "category": "script",
            "split": split,
            "input_type": "script",
            "file": f"scripts/{sid}.txt",
            "aspect_ratios": [ratio],
            "expected_outcome": "success",
            "checks": ["ffprobe_valid", "faststart_moov_before_mdat", "no_repeat_clips", "duration_sync_100ms"],
        }
        if sid == "script_11_double_meaning":
            entry["semantic_checks"] = ["bank_not_cash", "cloud_not_sky", "python_not_snake", "mouse_not_rodent"]
        elif sid == "script_12_named_entity":
            entry["expected_outcome"] = "success_with_warning"
            entry["expected_warning"] = "NAMED_ENTITY_SUBSTITUTED"
        tests.append(entry)

    # Add 8 voiceovers
    for vo_id, text, voice, lang, ext, split, ratio in vo_specs:
        tests.append({
            "id": vo_id,
            "category": "voiceover",
            "split": split,
            "input_type": "audio",
            "file": f"audio/{vo_id}{ext}",
            "voice": voice,
            "language": lang,
            "aspect_ratios": [ratio],
            "expected_outcome": "success",
            "checks": ["ffprobe_valid", "faststart_moov_before_mdat", "duration_sync_100ms", "no_repeat_clips"],
        })

    # Add 6 quick prompts
    prompts = [
        ("prompt_01_cat_walking", "cat walking", "train", "16:9"),
        ("prompt_02_ocean_waves", "ocean waves", "train", "16:9"),
        ("prompt_03_city_night", "busy city night", "held_out", "9:16"),
        ("prompt_04_coffee_pouring", "coffee pouring", "train", "1:1"),
        ("prompt_05_python_code", "python code on screen", "held_out", "16:9"),
        ("prompt_06_sunrise_mountains", "sunrise over mountains", "train", "16:9"),
    ]
    for pid, prompt_text, split, ratio in prompts:
        tests.append({
            "id": pid,
            "category": "quick_prompt",
            "split": split,
            "input_type": "prompt",
            "prompt": prompt_text,
            "duration_seconds": 12,
            "narration": False,
            "aspect_ratios": [ratio],
            "expected_outcome": "success",
            "checks": ["ffprobe_valid", "duration_matches_requested", "faststart_moov_before_mdat", "no_repeat_clips"],
        })

    # Add 4 edge cases
    tests.append({
        "id": "edge_01_sad_news",
        "category": "edge_case",
        "split": "held_out",
        "input_type": "script",
        "file": "edge_cases/edge_01_sad_news.txt",
        "aspect_ratios": ["16:9"],
        "expected_outcome": "success",
        "checks": ["respectful_medical_coverage", "no_violent_footage"],
    })
    tests.append({
        "id": "edge_02_extreme_crop_9x16",
        "category": "edge_case",
        "split": "train",
        "input_type": "script",
        "file": "edge_cases/edge_02_extreme_crop_9x16.txt",
        "aspect_ratios": ["9:16"],
        "expected_outcome": "success",
        "checks": ["ffprobe_1080x1920", "saliency_crop_applied"],
    })
    tests.append({
        "id": "edge_03_scene_list",
        "category": "edge_case",
        "split": "train",
        "input_type": "scenes",
        "file": "edge_cases/edge_03_scene_list.json",
        "aspect_ratios": ["16:9"],
        "expected_outcome": "success",
        "checks": ["scene_duration_respected", "visual_hints_matched"],
    })
    tests.append({
        "id": "edge_04_same_script_diff_voice_a",
        "category": "edge_case",
        "split": "held_out",
        "input_type": "script",
        "file": "edge_cases/edge_04_same_script_voice_a.txt",
        "voice": "en-US-Standard",
        "aspect_ratios": ["16:9"],
        "expected_outcome": "success",
        "checks": ["distinct_cache_hash_from_pair_b"],
    })
    tests.append({
        "id": "edge_04_same_script_diff_voice_b",
        "category": "edge_case",
        "split": "held_out",
        "input_type": "script",
        "file": "edge_cases/edge_04_same_script_voice_b.txt",
        "voice": "en-US-Neural",
        "aspect_ratios": ["16:9"],
        "expected_outcome": "success",
        "checks": ["distinct_cache_hash_from_pair_a"],
    })

    # Add 6 failure cases
    failure_cases = [
        ("fail_01_silent", "audio", "failures/fail_01_silent.wav", "expected_error", "SILENT_AUDIO_DETECTED"),
        ("fail_02_music_only", "audio", "failures/fail_02_music_only.wav", "expected_error", "MUSIC_ONLY_AUDIO_DETECTED"),
        ("fail_03_corrupted", "audio", "failures/fail_03_corrupted.mp3", "expected_error", "CORRUPTED_DOWNLOAD"),
        ("fail_04_wrong_type", "audio", "failures/fail_04_wrong_type.pdf", "expected_error", "INVALID_FILE_TYPE"),
        ("fail_05_empty_script", "script", "failures/fail_05_empty_script.txt", "expected_error", "EMPTY_SCRIPT"),
        ("fail_06_empty_prompt", "prompt", "failures/fail_06_empty_prompt.txt", "expected_error", "PROMPT_EMPTY"),
    ]
    for fid, in_type, fname, outcome, err_code in failure_cases:
        tests.append({
            "id": fid,
            "category": "failure_case",
            "split": "train",
            "input_type": in_type,
            "file": fname if in_type != "prompt" else None,
            "prompt": "   " if in_type == "prompt" else None,
            "expected_outcome": outcome,
            "expected_error_code": err_code,
            "checks": ["error_code_matches", "status_code_matches"],
        })

    # Write tests.yaml
    manifest = {
        "version": "2.0.0",
        "total_tests": len(tests),
        "split_summary": {
            "train": sum(1 for t in tests if t["split"] == "train"),
            "held_out": sum(1 for t in tests if t["split"] == "held_out"),
            "train_ratio": round(sum(1 for t in tests if t["split"] == "train") / len(tests), 2),
            "held_out_ratio": round(sum(1 for t in tests if t["split"] == "held_out") / len(tests), 2),
        },
        "tests": tests,
    }

    yaml_path = TEST_PACK_DIR / "tests.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, sort_keys=False, default_flow_style=False)

    print(f"Generated {len(tests)} test specifications successfully in {yaml_path}")
    print(f"Split: Train={manifest['split_summary']['train']} ({manifest['split_summary']['train_ratio']*100:.0f}%), "
          f"Held-Out={manifest['split_summary']['held_out']} ({manifest['split_summary']['held_out_ratio']*100:.0f}%)")

if __name__ == "__main__":
    build_all_assets()
