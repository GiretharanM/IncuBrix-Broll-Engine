"""
Prompt Expansion Engine
-----------------------
Transforms a single user prompt idea (e.g. "cat walking", "ocean waves") into
a storyboard of N varied scenes ($N \\approx duration_seconds / 4$) with 100% time coverage.

Each scene generates:
  - text: Narrative sentence for TTS narration or subtitles
  - visual_hint: Specific camera angle and setting
  - search_queries: 3 variants from specific to generic
    (e.g. ["cat walking on sidewalk", "cat walking", "cat"])

Deterministic fallback mode uses seed-driven shot angle sequences and modifiers
when the LLM adapter is unavailable, guaranteeing 100% reliable execution.
"""

import random
import re
from typing import Dict, Any, List, Optional
from app.pipeline.named_entity_detector import named_entity_detector
from app.pipeline.prompt_moderation import prompt_moderator

# Concise visual modifiers for cinematic stock footage indexing
SHOT_STYLES = [
    {
        "name": "establishing_wide",
        "hint": "wide panoramic establishing shot",
        "specific_mod": "landscape nature",
        "medium_mod": "outdoors",
    },
    {
        "name": "medium_motion",
        "hint": "medium dynamic action shot",
        "specific_mod": "running motion",
        "medium_mod": "action",
    },
    {
        "name": "close_up_detail",
        "hint": "macro close-up detail shot",
        "specific_mod": "close up",
        "medium_mod": "portrait",
    },
    {
        "name": "slow_motion_atmospheric",
        "hint": "slow motion atmospheric shot with golden lighting",
        "specific_mod": "slow motion light",
        "medium_mod": "slow motion",
    },
    {
        "name": "ground_level_tracking",
        "hint": "low-angle tracking camera movement",
        "specific_mod": "playing walking",
        "medium_mod": "outdoors",
    },
    {
        "name": "cinematic_reveal",
        "hint": "cinematic reveal with soft bokeh depth of field",
        "specific_mod": "cinematic sunlight",
        "medium_mod": "cinematic",
    },
]

class PromptExpansionEngine:
    def expand_prompt(
        self,
        prompt: str,
        duration_seconds: int = 20,
        narration: bool = False,
        seed: Optional[int] = None,
        avoid_tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Expands user prompt into N scenes with 3 cascading queries per scene.
        """
        # 1. Moderation & Translation
        cleaned_prompt = prompt_moderator.validate_and_moderate(prompt)
        english_search_base, detected_lang, is_translated = prompt_moderator.detect_and_translate_for_search(cleaned_prompt)

        warnings: List[str] = []
        if is_translated:
            warnings.append(f"Prompt in '{detected_lang}' translated to English for stock retrieval: '{english_search_base}'")

        # 2. Named Entity & Safety Check
        entity_info = named_entity_detector.detect_and_resolve(english_search_base)
        if entity_info.get("safety_warning"):
            warnings.append(entity_info["safety_warning"])

        # Determine effective core entity query
        if entity_info["is_protected"] and entity_info["replacement_query"]:
            core_query = entity_info["replacement_query"]
        elif entity_info["is_fruit"] and entity_info["replacement_query"]:
            core_query = entity_info["replacement_query"]
        elif entity_info["is_code"] and entity_info["replacement_query"]:
            core_query = entity_info["replacement_query"]
        else:
            core_query = english_search_base

        # 3. Calculate Scene Count N (each scene ~3-5s)
        # 8s -> 2 scenes; 20s -> 5 scenes; 60s -> 15 scenes
        scene_count = max(2, min(15, round(duration_seconds / 4.0)))
        scene_duration = round(duration_seconds / scene_count, 2)

        # Initialize RNG with seed if provided
        rng = random.Random(seed if seed is not None else 42)

        # 4. Generate Varied Scenes
        scenes = []
        start_t = 0.0

        # Rotate through shot styles with shuffle based on seed
        available_styles = list(SHOT_STYLES)
        rng.shuffle(available_styles)

        # Clean prompt words for base entity
        raw_words = re.findall(r"\b[a-zA-Z0-9-]+\b", core_query.lower())
        generic_entity = " ".join(raw_words[:2]) if raw_words else "nature"

        for i in range(scene_count):
            style = available_styles[i % len(available_styles)]
            end_t = round(start_t + scene_duration, 2)
            if i == scene_count - 1:
                end_t = float(duration_seconds)
            actual_scene_dur = round(end_t - start_t, 2)

            # Scene description text
            if narration:
                narrative_text = f"Experience {cleaned_prompt} in this stunning {style['name'].replace('_', ' ')} view."
            else:
                narrative_text = f"{cleaned_prompt.capitalize()} ({style['hint']})"

            # 3 Cascading Search Queries: Specific -> Medium -> Generic
            # Query 1: Specific (prompt + setting + shot angle)
            q_specific = f"{core_query} {style['specific_mod']}"
            # Query 2: Medium (prompt + simple modifier)
            q_medium = f"{core_query} {style['medium_mod']}"
            # Query 3: Generic fallback
            q_generic = core_query if core_query != generic_entity else generic_entity

            # Filter out avoid tags from queries
            avoid = avoid_tags or []
            clean_queries = []
            for q in [q_specific, q_medium, q_generic]:
                words = [w for w in q.split() if w.lower() not in avoid]
                clean_queries.append(" ".join(words))

            scenes.append({
                "scene_index": i,
                "text": narrative_text,
                "visual_hint": f"{style['hint']} of {cleaned_prompt}",
                "search_queries": clean_queries,
                "start_time": start_t,
                "end_time": end_t,
                "duration": actual_scene_dur,
                "shot_type": style["name"],
            })
            start_t = end_t

        warnings.append("PROMPT_EXPANSION_FALLBACK")

        return {
            "original_prompt": cleaned_prompt,
            "search_base": core_query,
            "duration_seconds": duration_seconds,
            "scene_count": scene_count,
            "expansion_method": "fallback",
            "seed": seed,
            "scenes": scenes,
            "warnings": warnings,
        }

prompt_expander = PromptExpansionEngine()
