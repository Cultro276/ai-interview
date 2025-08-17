from __future__ import annotations

import httpx

from src.core.config import settings


async def send_email_resend(to_email: str, subject: str, body_text: str) -> None:
    """Send an email via Resend if configured; otherwise print a mock log.

    Non-blocking errors are swallowed to avoid breaking user flows.
    """
    api_key = getattr(settings, "resend_api_key", None)
    mail_from = getattr(settings, "mail_from", None) or "noreply@example.com"
    mail_from_name = getattr(settings, "mail_from_name", None) or "Hirevision"
    if not api_key:
        print(f"[MAIL MOCK] To: {to_email}\nSubject: {subject}\nBody: {body_text}")
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            payload = {
                "from": f"{mail_from_name} <{mail_from}>",
                "to": [to_email],
                "subject": subject,
                "text": body_text,
            }
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            resp = await client.post("https://api.resend.com/emails", json=payload, headers=headers)
            if resp.status_code >= 400:
                print("[MAIL ERROR] Resend status", resp.status_code, resp.text)
    except Exception as e:  # best-effort only
        print("[MAIL ERROR]", e)


