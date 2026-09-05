from datetime import datetime, timezone
from io import BytesIO
import pytest

from app.modules.calendar.service import assert_weekday, WeekendNotAllowed


def test_saturday_rejected():
    with pytest.raises(WeekendNotAllowed):
        assert_weekday(datetime(2026, 9, 5, 15, 0, tzinfo=timezone.utc), "UTC")


def test_friday_ok():
    assert_weekday(datetime(2026, 9, 4, 15, 0, tzinfo=timezone.utc), "UTC")


def test_weekend_http_409(client, tmp_path, monkeypatch):
    monkeypatch.setenv("RESUME_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()
    hr = client.post("/api/auth/register", json={
        "email": "hr@example.com", "password": "password", "name": "Pat", "role": "hr"
    }).json()
    job = client.post("/api/jobs", json={
        "title": "X", "team": "T", "location": "L", "seniority": "j",
        "required_skills": ["python"], "nice_to_have": [], "min_years": 0,
        "education": "none", "narrative": "n",
    }, headers={"Authorization": f"Bearer {hr['token']}"}).json()
    client.post(f"/api/jobs/{job['id']}/publish", headers={"Authorization": f"Bearer {hr['token']}"})
    app = client.post(
        f"/api/jobs/{job['id']}/apply",
        data={"email": "ada@example.com", "password": "password", "name": "Ada"},
        files={"resume": ("cv.txt", BytesIO(b"python"), "text/plain")},
    ).json()
    if app["status"] == "applied":
        client.post(
            f"/api/applications/{app['id']}/override",
            json={"decision": "pass"},
            headers={"Authorization": f"Bearer {hr['token']}"},
        )
    r = client.post(
        "/api/interviews",
        json={"application_id": app["id"], "start_at": "2026-09-05T15:00:00+00:00"},
        headers={"Authorization": f"Bearer {hr['token']}"},
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "weekend_not_allowed"


def test_google_not_configured(client):
    hr = client.post("/api/auth/register", json={
        "email": "hr@example.com", "password": "password", "name": "Pat", "role": "hr"
    }).json()
    r = client.get("/api/calendar/google/connect", headers={"Authorization": f"Bearer {hr['token']}"}, follow_redirects=False)
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "google_not_configured"
