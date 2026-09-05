from urllib.parse import urlencode

import httpx

from app.config import get_settings


def configured() -> bool:
    s = get_settings()
    return bool(s.google_client_id and s.google_client_secret)


def auth_url(state: str) -> str:
    s = get_settings()
    q = urlencode({
        "client_id": s.google_client_id,
        "redirect_uri": s.google_redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/calendar.readonly",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    })
    return f"https://accounts.google.com/o/oauth2/v2/auth?{q}"


def exchange_code(code: str) -> str | None:
    s = get_settings()
    try:
        r = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": s.google_client_id,
                "client_secret": s.google_client_secret,
                "redirect_uri": s.google_redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=20.0,
        )
        r.raise_for_status()
        return r.json().get("refresh_token") or r.json().get("access_token")
    except Exception:
        return None
