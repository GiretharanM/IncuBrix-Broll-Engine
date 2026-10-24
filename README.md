# IncuBrix B-Roll Video Studio Engine

> **IncuBrix Engineering Assessment 3**: High-performance Script and Voiceover to B-roll Video Generation Engine with semantic stock footage retrieval, automated scene segmentation, VLM candidate ranking, and instant partial segment re-rendering.

---

## 🚀 Live Demo & Studio
- **Hosted Public Demo**: [https://redeem-each-photograph-smaller.trycloudflare.com](https://redeem-each-photograph-smaller.trycloudflare.com)
- **API Documentation (Swagger UI)**: [https://redeem-each-photograph-smaller.trycloudflare.com/docs](https://redeem-each-photograph-smaller.trycloudflare.com/docs)
- **OpenAPI 3.1 Specification**: [openapi.yaml](openapi.yaml)

---

## 🛠️ Key Capabilities
1. **Multi-Input Generation**:
   - **Quick Prompt**: Single concise prompt (e.g. *"golden retriever puppy in a park"*) expanded into rich cinematic scenes.
   - **Script Text**: Full script segmented at natural sentence boundaries with synchronized local TTS voiceover (EN, HI, TA).
   - **Uploaded Voiceover**: MP3, WAV, and M4A voiceovers up to 10 minutes, transcribed with word-level speech-to-text.
2. **Real Commercial Stock Retrieval**:
   - Live integration with Pixabay Video API with stop-word query optimization and commercial-use license compliance.
3. **Semantic VLM Scoring & Deduplication**:
   - Rule-based stemming and subject-overlap gating to guarantee zero non-sequitur matches and 0.0% repeat clip rate.
4. **Fast Partial Re-rendering (Manual Swap)**:
   - Scene candidate pool cached in SQLite; user manual clip swapping leverages SHA-256 segment caching to re-render only the modified scene (0.6s re-render vs 14.0s full render).
5. **Web-Optimized Video Output**:
   - FFmpeg H.264 High Profile, `yuv420p`, AAC audio, and `+faststart` (`moov` before `mdat`).

---

## 📋 Quick Start

### 1. Run with Docker Compose
```bash
docker compose up -d
```
The service starts on `http://localhost:8000` with the React SPA frontend, FastAPI backend, MinIO storage, and SQLite database ready.

### 2. Run Locally (Development)
```bash
# Backend
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# Frontend (Production Build)
cd frontend
npm install
npm run build
```

---

## 📑 Standardized Error Codes

All errors conform to `{ "error": { "code", "message", "retryable", "details" } }`:

| Code | HTTP Status | Description |
| :--- | :--- | :--- |
| `PROMPT_EMPTY` | 400 | Prompt input is empty or contains only whitespace |
| `PROMPT_TOO_LONG` | 400 | Prompt exceeds maximum allowed length |
| `PROMPT_NOT_ALLOWED` | 422 | Prompt violates content safety policies |
| `AUDIO_INVALID` | 400 | Uploaded audio file is silent, corrupted, or unsupported |
| `JOB_NOT_FOUND` | 404 | The requested job ID does not exist |
| `SCENE_NOT_FOUND` | 404 | The specified scene index or ID was not found |
| `PROVIDER_RATE_LIMITED` | 429 | Footage provider API rate limit exceeded |
| `INTERNAL_ERROR` | 500 | Unexpected rendering or pipeline failure |

---

## 📄 Documentation Links
- **[REPORT.md](REPORT.md)**: Full architecture breakdown, pipeline trace, and benchmark metrics.
- **[SOURCES.md](SOURCES.md)**: Commercial licensing ledger, stock API terms, and ambient audio licenses.
- **[AI_USE.md](AI_USE.md)**: AI pair-programming disclosures, algorithm details, and verification methods.
- **[Assessment3_Giretharan_M.xlsx](Assessment3_Giretharan_M.xlsx)**: Complete official submission form.
