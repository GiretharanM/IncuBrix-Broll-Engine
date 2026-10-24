# AI Use & Development Ledger

**Candidate**: Giretharan M  
**Assessment**: IncuBrix Engineering Assessment 3 (B-roll Video Engine)  
**Date**: October 2026  

---

## 1. AI Coding Assistants & Models Used
- **Assistant**: Antigravity Pair-Programming Agent (Google DeepMind)
- **Primary Model**: Advanced Reasoning / Coding LLM
- **Roles & Tasks**:
  - Codebase inspection, dependency graph tracing, and runtime execution diagnostics.
  - Designing rule-based query cleaning algorithms (`clean_pixabay_query`).
  - Implementing morphological stemming and subject gating for VLM candidate scoring.
  - Automated test scripting, end-to-end HTTP pipeline validation, and Playwright verification.

---

## 2. In-Engine AI & Machine Learning Components
The B-roll engine incorporates the following AI and algorithmic components:

1. **Vision-Language Scorer (`vlm_scorer.py`)**:
   - Scores candidate footage relevance against scene transcripts using lexical embedding and tag correlation algorithms.
   - Applies subject gating rules to prevent semantic mismatch on generic action verbs.

2. **Named Entity Detector & Moderation (`named_entity_detector.py` & `prompt_moderation.py`)**:
   - Parses input scripts for named celebrities, living figures, and proprietary brands to protect against unauthorized likeness generation or copyright infringement.

3. **Speech & Audio Alignment (Whisper / VAD Adapter)**:
   - Derives word-level timestamps from voiceover audio files (MP3/WAV/M4A) to align B-roll scene transitions with speech pauses.

4. **Generative Ken-Burns Parallax Synthesis (`generative_adapter.py`)**:
   - Fallback video synthesis engine producing subtle camera motion and smooth transitions when stock clips are unavailable or fail minimum threshold criteria.

---

## 3. Human Oversight & Declaration
- All generated code was inspected, tested against live HTTP endpoints, verified with `ffprobe` for codec and container integrity, and audited against the IncuBrix Integration Standards.
- No synthetic benchmarks, mock responses, or hardcoded shortcuts were used to pass quality evaluations.
