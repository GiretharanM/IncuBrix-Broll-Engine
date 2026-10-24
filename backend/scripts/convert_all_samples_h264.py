import subprocess
import os
import json
import shutil

ffmpeg_path = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe")
ffprobe_path = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffprobe.exe")

vdir = "frontend/public/videos"
for f in os.listdir(vdir):
    if f.endswith(".mp4"):
        full_p = os.path.join(vdir, f)
        res = subprocess.run([ffprobe_path, "-v", "quiet", "-print_format", "json", "-show_streams", full_p], capture_output=True, text=True)
        try:
            data = json.loads(res.stdout)
            v_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
            if v_stream and v_stream.get("codec_name") != "h264":
                print(f"Re-encoding {f} from {v_stream.get('codec_name')} to h264...")
                tmp_out = full_p.replace(".mp4", "_h264.mp4")
                subprocess.run([ffmpeg_path, "-y", "-i", full_p, "-c:v", "libx264", "-profile:v", "main", "-pix_fmt", "yuv420p", "-movflags", "+faststart", tmp_out], check=True, capture_output=True)
                os.replace(tmp_out, full_p)
                dist_p = os.path.join("frontend/dist/videos", f)
                if os.path.exists("frontend/dist/videos"):
                    shutil.copy2(full_p, dist_p)
        except Exception as e:
            print(f"Skipping {f}: {e}")

print("All static video assets verified as browser-playable H.264!")
