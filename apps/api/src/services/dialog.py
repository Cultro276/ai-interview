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


# --- Requirements targeting helpers ---

def pick_next_requirement_target(requirements_spec: dict, fit_matrix: list[dict], asked_counts: dict[str, int]) -> dict | None:
    """Pick the next requirement to probe based on must/weight and remaining gaps.

    - Prioritize must=true and meets in {"no","partial"}
    - Use weight as multiplier; lightly penalize repeated probing of same label
    """
    try:
        spec_items = (requirements_spec or {}).get("items") or []
        spec_by_label = {str(it.get("label", "")): it for it in spec_items if isinstance(it, dict)}
        scored: list[tuple[float, str, dict, dict]] = []
        for row in (fit_matrix or []):
            if not isinstance(row, dict):
                continue
            label = str(row.get("label", ""))
            meets = str(row.get("meets", "")).lower()
            if meets not in ("no", "partial"):
                continue
            spec = spec_by_label.get(label, {})
            weight = float(spec.get("weight", 0.5) or 0.5)
            must = bool(spec.get("must", False))
            asked = int(asked_counts.get(label, 0))
            base = (2.0 if must else 1.0) * weight
            penalty = 0.4 * max(0, asked - 1)
            score = base - penalty
            scored.append((score, label, spec, row))
        scored.sort(key=lambda x: x[0], reverse=True)
        if not scored:
            return None
        _score, label, spec, row = scored[0]
        kws = spec.get("keywords") or [label]
        templates = spec.get("question_templates") or [f"{label} ile ilgili somut bir örnek ve sonucu paylaşır mısınız?"]
        return {
            "label": label,
            "keywords": kws,
            "template": templates[0],
            "must": bool(spec.get("must", False)),
            "rubric": spec.get("success_rubric") or "Somut örnek ve ölçülebilir sonuç",
        }
    except Exception:
        return None


def build_requirements_ctx(req_spec: dict, fit: dict, target: dict | None) -> str:
    """Construct a compact, private context block steering the LLM toward gaps.

    This block MUST NOT be exposed verbatim to candidates; it's only passed as hidden context.
    """
    parts: list[str] = []
    try:
        items = (req_spec or {}).get("items") or []
        if items:
            ck = [
                f"- {'MUST ' if (it.get('must')) else ''}{it.get('label')} (kw: {', '.join((it.get('keywords') or [])[:3])})"
                for it in items[:12] if isinstance(it, dict)
            ]
            parts.append("RequirementsChecklist:\n" + "\n".join(ck))
    except Exception:
        pass
    try:
        matrix = fit.get("requirements_matrix") if isinstance(fit, dict) else None
        if matrix:
            state = [f"- {m.get('label')}: {m.get('meets')}" for m in matrix if isinstance(m, dict)]
            parts.append("CoverageState:\n" + "\n".join(state))
    except Exception:
        pass
    if target:
        parts.append(
            "NextTarget:\n"
            + f"- label: {target.get('label')}\n"
            + f"- focus_keywords: {', '.join((target.get('keywords') or [])[:5])}\n"
            + f"- ask_template: {target.get('template')}\n"
            + f"- rubric_hint: {target.get('rubric')}"
        )
    parts.append(
        "QuestionPolicy:\n"
        "- Amaç: NextTarget alanını doğal bir soruyla ölçmek; STAR eksikse kısa takip.\n"
        "- Sızdırma: İlan/CV’den bahsetme, alıntılama yapma.\n"
        "- Biçim: Türkçe, 1–2 cümle, gereksiz girişler yok.\n"
        "- Yeterli delil toplandıysa ve soru sayısı makulse FINISHED."
    )
    return "\n\n".join(parts)

