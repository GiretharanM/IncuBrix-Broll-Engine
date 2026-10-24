import re
from app.adapters.vision.vlm_scorer import VLMVisionScorer

# Let's test the current scorer vs an improved scorer with stemming and subject matching

def stem_word(w: str) -> str:
    w = w.lower().strip()
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"  # puppies -> puppy
    if w.endswith("es") and len(w) > 3 and not w.endswith("ees"):
        return w[:-2]  # beaches -> beach
    if w.endswith("s") and len(w) > 2 and not w.endswith("ss"):
        return w[:-1]  # dogs -> dog, mountains -> mountain
    return w

class ImprovedVLMScorer:
    def score(self, candidate_meta, scene_text, visual_hint=None):
        clean_query = f"{scene_text} {visual_hint or ''}".lower()
        raw_query_words = re.findall(r"\b\w{3,}\b", clean_query)
        query_stems = {stem_word(w) for w in raw_query_words}

        title_words = re.findall(r"\b\w{3,}\b", candidate_meta.get("title", "").lower())
        tags = [t.lower().strip() for t in candidate_meta.get("tags", [])]
        cand_words = set(title_words).union(set(tags))
        cand_stems = {stem_word(w) for w in cand_words}

        # Subject words (first 2 salient nouns/words of the query)
        stop_words = {"this", "that", "with", "from", "have", "they", "will", "what", "their", "there", "about", "into", "over", "under", "across", "running", "walking", "moving", "playing"}
        subject_stems = {stem_word(w) for w in raw_query_words if w not in stop_words}
        if not subject_stems:
            subject_stems = query_stems

        overlap = query_stems.intersection(cand_stems)
        subject_overlap = subject_stems.intersection(cand_stems)

        # If candidate has ZERO overlap with the subject (e.g. query is dog, but clip has no dog/puppy/canine), penalize heavily
        has_subject = len(subject_overlap) > 0

        # Lexical score
        lexical = min(1.0, len(overlap) / max(1, len(query_stems) * 0.5))

        base = 0.22 + (0.50 * lexical)
        if has_subject:
            base += 0.20  # Subject match bonus
        else:
            base *= 0.50  # Heavy penalty for missing subject

        return round(min(0.96, max(0.10, base)), 3)

cand_men_running = {
    'id': 'pixabay_27539',
    'title': 'Pixabay: running, bridge, mountains, men running, running in morning',
    'tags': ['running', 'bridge', 'mountains', 'men running']
}

cand_dog_beach = {
    'id': 'pixabay_24541',
    'title': 'Pixabay: summer, beach, sea, ocean, water, pet, dog, outdoor',
    'tags': ['summer', 'beach', 'sea', 'ocean', 'pet', 'dog']
}

cand_puppy_grass = {
    'id': 'pixabay_74257',
    'title': 'Pixabay: puppy, dog, young, canine, grass, cute',
    'tags': ['puppy', 'dog', 'young', 'canine', 'grass', 'cute']
}

scorer = ImprovedVLMScorer()
print("--- SCORING 'dogs running on a beach' ---")
print("Men running on bridge:", scorer.score(cand_men_running, 'dogs running on a beach'))
print("Dog on beach:", scorer.score(cand_dog_beach, 'dogs running on a beach'))

print("\n--- SCORING 'puppies running on grass' ---")
print("Men running on bridge:", scorer.score(cand_men_running, 'puppies running on grass'))
print("Puppy on grass:", scorer.score(cand_puppy_grass, 'puppies running on grass'))
