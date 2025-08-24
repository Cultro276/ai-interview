from __future__ import annotations

from typing import List


_TR_STOPWORDS = {
    "ve", "veya", "ile", "için", "ama", "fakat", "de", "da", "mi", "mu", "mü", "mı",
    "bir", "bu", "şu", "o", "çok", "az", "gibi", "olan", "olanlar", "olarak", "en", "değil",
}


def _normalize(text: str) -> List[str]:
    tokens = [t.strip(".,;:!?()[]{}\"'`).-_ ").lower() for t in text.split()]
    return [t for t in tokens if t and t not in _TR_STOPWORDS]


def extract_keywords(text: str) -> List[str]:
    tokens = _normalize(text)
    uniq: List[str] = []
    for t in tokens:
        if t not in uniq:
            uniq.append(t)
    return uniq[:10]


def reflect(user_answer: str) -> str:
    # Intentional no-echo: avoid repeating candidate's words; keep questions concise
    return ""


# Removed requirement-based probing and followups


def generic_followup(last_user_keywords: List[str]) -> str:
    return "Bu deneyiminizde somut bir örnek ve çıktılarınızı paylaşabilir misiniz?"


def generate_next_question_generic(history: List[dict]) -> dict:
    asked = sum(1 for t in history if t.get("role") == "assistant")
    if asked == 0:
        return {"question": "Kendinizi ve son iş deneyiminizi kısaca anlatır mısınız?", "done": False}
    if asked >= 7:
        return {"question": None, "done": True}
    last_user_text = next((t.get("text", "") for t in reversed(history) if t.get("role") == "user"), "")
    q = generic_followup(extract_keywords(last_user_text))
    return {"question": q.strip(), "done": False}


