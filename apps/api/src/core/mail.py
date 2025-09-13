from __future__ import annotations

import httpx

import logging
from typing import List, Dict, Any, Optional
from src.core.config import settings


async def send_email_resend(to_email: str, subject: str, body_text: str, attachments: Optional[List[Dict[str, Any]]] = None) -> None:
    """Send an email via Resend if configured; otherwise print a mock log.

    Non-blocking errors are swallowed to avoid breaking user flows.
    """
    api_key = getattr(settings, "resend_api_key", None)
    mail_from = getattr(settings, "mail_from", None) or "noreply@example.com"
    mail_from_name = getattr(settings, "mail_from_name", None) or "Hirevision"
    if not api_key:
        logging.getLogger(__name__).info("[MAIL MOCK] To: %s Subject: %s", to_email, subject)
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            payload = {
                "from": f"{mail_from_name} <{mail_from}>",
                "to": [to_email],
                "subject": subject,
                "text": body_text,
            }
            # Resend attachments: list of { filename, content (base64), content_type? }
            if attachments:
                safe_atts: list[dict] = []
                for att in attachments:
                    if not isinstance(att, dict):
                        continue
                    fn = att.get("filename") or att.get("fileName")
                    content = att.get("content")
                    if not fn or not content:
                        continue
                    entry = {
                        "filename": str(fn),
                        "content": str(content),
                    }
                    # Optional content type (Resend tolerates absence)
                    ct = att.get("content_type") or att.get("type")
                    if ct:
                        entry["content_type"] = str(ct)
                    safe_atts.append(entry)
                if safe_atts:
                    payload["attachments"] = safe_atts
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            resp = await client.post("https://api.resend.com/emails", json=payload, headers=headers)
            if resp.status_code >= 400:
                logging.getLogger(__name__).error("[MAIL ERROR] Resend status %s %s", resp.status_code, resp.text)
    except Exception as e:  # best-effort only
        logging.getLogger(__name__).exception("[MAIL ERROR]")


