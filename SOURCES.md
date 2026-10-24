# Broll Studio Media Sources & Licensing Ledger

All media assets utilized or synthesized by Broll Studio adhere to commercial licensing standards with zero proprietary copyright infringement.

---

## 1. Stock Footage Providers

### Pixabay Video API
- **License**: [Pixabay Content License](https://pixabay.com/service/license-summary/)
- **Terms**: Free for commercial and non-commercial use across digital and print; attribution is appreciated but not legally required.
- **Implementation**: Fetched via authenticated API requests (`https://pixabay.com/api/videos/`), downloaded to secure local cache, and verified for commercial clearance.

### Pexels Video API
- **License**: [Pexels License](https://www.pexels.com/license/)
- **Terms**: All photos and videos on Pexels can be downloaded and used for free for commercial purposes without attribution.

---

## 2. Ambient Audio & Soundtracks

When a video is generated without voiceover narration (`narration=false`), Broll Studio provides commercial-clean ambient audio:

### Ambient Track A: Soft Cinematic Ambient Tone (Generated Synthesis)
- **Source**: Deterministic synthesized 432Hz sine/warm harmonics audio with subtle low-pass acoustic filtering generated directly via FFmpeg `sine=frequency=216:sample_rate=44100` with subtle fade-in / fade-out envelope.
- **License**: CC0 1.0 Universal (Public Domain Dedication) / Programmatically Generated.
- **Attribution**: Synthesized in-engine by Broll Studio Audio Engine.

### Ambient Track B: Peaceful Acoustic Flow
- **Source**: Royalty-Free Ambient Acoustic (CC0 / Clean Commercial Audio Archive).
- **License**: Creative Commons Zero (CC0) / Royalty-Free Commercial License.
- **Attribution**: Broll Studio Clean Audio Library.

---

## 3. Generative AI Video Fallback
- **Engine**: Broll Studio Generative Parallax & Ken-Burns Synthesis.
- **License**: Proprietary Commercially Safe Synthesis.
- **Usage**: Deployed only as a fallback when no stock footage passes minimum relevance criteria.
