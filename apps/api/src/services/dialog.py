from __future__ import annotations

from typing import List, Dict, Any


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


def _pick_requirement_to_probe(history: List[Dict[str, str]], requirements_config: Dict[str, Any]) -> Dict[str, Any] | None:
    reqs = requirements_config.get("requirements") or []
    if not reqs:
        return None
    user_text = "\n".join([h["text"] for h in history if h.get("role") == "user"]).lower()
    # Score each requirement by missing coverage (fewer hits -> higher priority)
    best_req = None
    best_score = -1.0
    for r in reqs:
        kws = [str(k).lower() for k in (r.get("keywords") or []) if k]
        if not kws:
            continue
        hits = sum(1 for k in kws if k in user_text)
        coverage = hits / max(1, len(kws))
        priority = 1.0 - coverage
        # weight can bias importance
        weight = float(r.get("weight") or 0.0)
        score = priority + (0.1 * (weight / 100.0))
        if score > best_score:
            best_score = score
            best_req = r
    return best_req


def _followup_for_requirement(req: Dict[str, Any], last_user_keywords: List[str]) -> str:
    followups = req.get("followups") or []
    if not followups:
        # generic probes; if we know the requirement label, make it targeted
        label = (req.get("label") or "").strip()
        if label:
            return f"{label} ile ilgili somut bir örnek ve sonuçlarınızı paylaşabilir misiniz?"
        return "Bu konuyla ilgili somut bir örnek ve sonuçlarınızı paylaşabilir misiniz?"
    # pick the first with keyword overlap, else first
    low_kws = set(k.lower() for k in last_user_keywords)
    for f in followups:
        low_f = str(f).lower()
        if any(k in low_f for k in low_kws):
            return str(f)
    return str(followups[0])


def generate_next_question(history: List[Dict[str, str]], requirements_config: Dict[str, Any]) -> Dict[str, Any]:
    dialog_cfg = (requirements_config.get("dialog") or {}) if isinstance(requirements_config, dict) else {}
    max_q = int(dialog_cfg.get("max_questions") or 7)
    initial_q = dialog_cfg.get("initial_question") or None

    asked = sum(1 for t in history if t.get("role") == "assistant")
    if asked == 0:
        # Tailor the first question using the highest-weight requirement label if available
        if not initial_q:
            reqs = (requirements_config.get("requirements") or []) if isinstance(requirements_config, dict) else []
            top = None
            try:
                top = sorted(reqs, key=lambda r: float(r.get("weight") or 0), reverse=True)[0] if reqs else None
            except Exception:
                top = reqs[0] if reqs else None
            if top and top.get("label"):
                label = str(top.get("label")).strip()
                initial_q = f"İlana uygunluk açısından {label} alanındaki deneyiminizi kısaca anlatır mısınız?"
            else:
                initial_q = "Kendinizi ve son iş deneyiminizi kısaca anlatır mısınız?"
        return {"question": initial_q, "done": False}
    if asked >= max_q:
        return {"question": None, "done": True}

    # Use last user answer to reflect and choose next probe
    last_user_text = next((t.get("text", "") for t in reversed(history) if t.get("role") == "user"), "")
    req = _pick_requirement_to_probe(history, requirements_config)
    if not req:
        # generic follow-up
        q = "Bu deneyiminizde üstlendiğiniz sorumlulukları biraz açar mısınız?"
        return {"question": q.strip(), "done": False}

    follow = _followup_for_requirement(req, extract_keywords(last_user_text))
    # Use the selected follow-up as-is; requirement label is used internally only
    q = str(follow)
    return {"question": q.strip(), "done": False}


