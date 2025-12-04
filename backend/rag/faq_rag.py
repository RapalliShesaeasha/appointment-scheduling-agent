import json
from pathlib import Path
import re

FAQ_FILE = Path("data/clinic_info.json")
FAQS = []


def initialize_faq_index():
    global FAQS
    with open(FAQ_FILE, "r") as f:
        FAQS = json.load(f)


def _normalize(text: str):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return text


def _tokenize(text: str):
    return set(_normalize(text).split())


def _similarity_score(user_tokens, faq_tokens):
    """
    Counts how many meaningful words overlap between question and user query.
    Removes useless small words ('what', 'is', 'do', 'you', etc).
    """
    STOP_WORDS = {
        "what", "is", "are", "do", "you", "your", "the", "a", "an",
        "i", "we", "my", "of", "for", "to", "please", "can", "tell"
    }

    u = user_tokens - STOP_WORDS
    f = faq_tokens - STOP_WORDS

    if not u or not f:
        return 0

    return len(u.intersection(f))


def answer_faq(question: str):
    """
    Improved scoring-based FAQ matching.
    Always returns ONLY the single best matching FAQ (per PDF).
    """
    user_tokens = _tokenize(question)

    scores = []
    for faq in FAQS:
        faq_tokens = _tokenize(faq["question"])
        score = _similarity_score(user_tokens, faq_tokens)
        scores.append((score, faq))

    # Sort by highest score first
    scores.sort(key=lambda x: x[0], reverse=True)

    # If highest score is zero → fallback to first FAQ
    best_score, best_faq = scores[0]

    if best_score == 0:
        best_faq = FAQS[0]  # fallback to first

    return {
        "answer": best_faq["answer"],
        "sources": [best_faq]
    }
