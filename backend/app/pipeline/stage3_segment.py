import re
from typing import List, Dict, Any, Optional
from app.config import settings

class SceneSegment:
    def __init__(
        self,
        scene_index: int,
        text: str,
        start_time: float,
        end_time: float,
        visual_hint: Optional[str] = None,
    ):
        self.scene_index = scene_index
        self.text = text.strip()
        self.start_time = round(start_time, 2)
        self.end_time = round(end_time, 2)
        self.duration = round(end_time - start_time, 2)
        self.visual_hint = visual_hint

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_index": self.scene_index,
            "text": self.text,
            "visual_hint": self.visual_hint,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
        }

class SceneSegmenter:
    def __init__(self, min_scene_duration: float = 2.5):
        self.min_scene_duration = min_scene_duration

    def segment_transcript(
        self,
        transcript_data: Dict[str, Any],
        predefined_scenes: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Segments narration into semantic scenes using word-level timestamps.
        Guarantees:
        - 100% time coverage (no gaps, no overlaps: scene[i].end == scene[i+1].start)
        - Start time of scene 0 is 0.0s, end time of final scene is audio total duration
        - Enforces minimum scene duration (default 2.5s) to prevent flash cuts
        """
        words = transcript_data.get("words", [])
        total_duration = transcript_data.get("duration", 0.0)

        # Fallback if words list is empty
        if not words:
            raw_text = transcript_data.get("text", "")
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", raw_text) if s.strip()]
            if not sentences:
                sentences = ["Voiceover narration"]
            step = max(self.min_scene_duration, total_duration / len(sentences))
            segments = []
            curr_start = 0.0
            for i, sent in enumerate(sentences):
                curr_end = total_duration if i == len(sentences) - 1 else round(curr_start + step, 2)
                segments.append(SceneSegment(i, sent, curr_start, curr_end).to_dict())
                curr_start = curr_end
            return segments

        # 1. Group words into sentence / phrase chunks based on punctuation & pauses
        raw_chunks = []
        current_chunk_words = []
        current_chunk_start = words[0]["start"]

        for i, w in enumerate(words):
            current_chunk_words.append(w["word"])
            word_text = w["word"].strip()

            is_punctuation = bool(re.search(r"[.!?]$", word_text))
            has_pause = False
            if i < len(words) - 1:
                pause_gap = words[i + 1]["start"] - w["end"]
                if pause_gap >= 0.45:
                    has_pause = True

            # If punctuation or long pause reached, finish candidate chunk
            if is_punctuation or has_pause or i == len(words) - 1:
                chunk_text = " ".join(current_chunk_words)
                chunk_end = w["end"]
                raw_chunks.append({
                    "text": chunk_text,
                    "start": current_chunk_start,
                    "end": chunk_end,
                })
                current_chunk_words = []
                if i < len(words) - 1:
                    current_chunk_start = words[i + 1]["start"]

        # 2. Merge chunks that are shorter than min_scene_duration (default 2.5s)
        merged_chunks = []
        for chunk in raw_chunks:
            if not merged_chunks:
                merged_chunks.append(chunk)
            else:
                prev = merged_chunks[-1]
                prev_duration = prev["end"] - prev["start"]
                # If previous chunk is too short, merge with current
                if prev_duration < self.min_scene_duration:
                    prev["text"] = f"{prev['text']} {chunk['text']}"
                    prev["end"] = chunk["end"]
                else:
                    merged_chunks.append(chunk)

        # Check final chunk duration; if too short, merge into previous
        if len(merged_chunks) > 1:
            last = merged_chunks[-1]
            if (last["end"] - last["start"]) < self.min_scene_duration:
                penultimate = merged_chunks[-2]
                penultimate["text"] = f"{penultimate['text']} {last['text']}"
                penultimate["end"] = last["end"]
                merged_chunks.pop()

        # 3. Enforce 100% time coverage (contiguous boundaries: 0.0 to total_duration)
        final_segments = []
        current_boundary = 0.0

        for i, chunk in enumerate(merged_chunks):
            is_last = (i == len(merged_chunks) - 1)
            # Next boundary is the start of the next chunk or total duration
            if is_last:
                seg_end = max(total_duration, chunk["end"])
            else:
                next_start = merged_chunks[i + 1]["start"]
                # Midpoint between this end and next start to eliminate any silent gap
                seg_end = round((chunk["end"] + next_start) / 2.0, 2)

            hint = None
            if predefined_scenes and i < len(predefined_scenes):
                hint = predefined_scenes[i].get("visual_hint")

            final_segments.append(
                SceneSegment(
                    scene_index=i,
                    text=chunk["text"],
                    start_time=current_boundary,
                    end_time=seg_end,
                    visual_hint=hint,
                ).to_dict()
            )
            current_boundary = seg_end

        return final_segments

scene_segmenter = SceneSegmenter(
    min_scene_duration=settings.MIN_SCENE_DURATION_SECONDS
)
