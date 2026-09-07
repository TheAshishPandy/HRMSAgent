import pytest
from io import BytesIO
from datetime import datetime, timezone

from app.modules.pipeline import transition, IllegalTransition


def test_illegal_offer_from_applied():
    with pytest.raises(IllegalTransition):
        transition("applied", "offer", has_feedback=False, has_interview=False)


def test_offer_needs_feedback():
    with pytest.raises(IllegalTransition):
        transition("interview", "offer", has_feedback=False, has_interview=True)


def _setup_screened(client, tmp_path, monkeypatch):
    monkeypatch.setenv("RESUME_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()
    hr = client.post("/api/auth/register", json={
        "email": "hr@example.com", "password": "password", "name": "Pat", "role": "hr"
    }).json()
    job = client.post("/api/jobs", json={
        "title": "Backend", "team": "T", "location": "L", "seniority": "j",
        "required_skills": ["python"], "nice_to_have": [], "min_years": 0,
        "education": "none", "narrative": "n",
    }, headers={"Authorization": f"Bearer {hr['token']}"}).json()
    client.post(f"/api/jobs/{job['id']}/publish", headers={"Authorization": f"Bearer {hr['token']}"})
    app = client.post(
        f"/api/jobs/{job['id']}/apply",
        data={"email": "ada@example.com", "password": "password", "name": "Ada"},
        files={"resume": ("cv.txt", BytesIO(b"python engineer"), "text/plain")},
    ).json()
    if app["status"] == "applied":
        client.post(
            f"/api/applications/{app['id']}/override",
            json={"decision": "pass"},
            headers={"Authorization": f"Bearer {hr['token']}"},
        )
        app = client.get(
            f"/api/applications/{app['id']}",
            headers={"Authorization": f"Bearer {hr['token']}"},
        ).json()
    return hr, app


def test_override_fail_rejects(client, tmp_path, monkeypatch):
    monkeypatch.setenv("RESUME_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()
    hr = client.post("/api/auth/register", json={
        "email": "hr@example.com", "password": "password", "name": "Pat", "role": "hr"
    }).json()
    job = client.post("/api/jobs", json={
        "title": "Backend", "team": "T", "location": "L", "seniority": "j",
        "required_skills": ["unobtainium"], "nice_to_have": [], "min_years": 0,
        "education": "none", "narrative": "n",
    }, headers={"Authorization": f"Bearer {hr['token']}"}).json()
    client.post(f"/api/jobs/{job['id']}/publish", headers={"Authorization": f"Bearer {hr['token']}"})
    app = client.post(
        f"/api/jobs/{job['id']}/apply",
        data={"email": "ada@example.com", "password": "password", "name": "Ada"},
        files={"resume": ("cv.txt", BytesIO(b"retail"), "text/plain")},
    ).json()
    r = client.post(
        f"/api/applications/{app['id']}/override",
        json={"decision": "fail"},
        headers={"Authorization": f"Bearer {hr['token']}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_offer_without_feedback_rejected(client, tmp_path, monkeypatch):
    hr, app = _setup_screened(client, tmp_path, monkeypatch)
    start = datetime(2026, 9, 4, 15, 0, tzinfo=timezone.utc)
    client.post(
        "/api/interviews",
        json={"application_id": app["id"], "start_at": start.isoformat()},
        headers={"Authorization": f"Bearer {hr['token']}"},
    )
    r = client.post(
        f"/api/applications/{app['id']}/offer",
        headers={"Authorization": f"Bearer {hr['token']}"},
    )
    assert r.status_code == 409


def test_offer_after_feedback(client, tmp_path, monkeypatch):
    hr, app = _setup_screened(client, tmp_path, monkeypatch)
    start = datetime(2026, 9, 4, 15, 0, tzinfo=timezone.utc)
    iv = client.post(
        "/api/interviews",
        json={"application_id": app["id"], "start_at": start.isoformat()},
        headers={"Authorization": f"Bearer {hr['token']}"},
    ).json()
    client.post(
        f"/api/interviews/{iv['id']}/complete",
        headers={"Authorization": f"Bearer {hr['token']}"},
    )
    fb = client.post(
        "/api/feedback",
        json={"interview_id": iv["id"], "rating": 4, "notes": "solid"},
        headers={"Authorization": f"Bearer {hr['token']}"},
    )
    assert fb.status_code == 200
    r = client.post(
        f"/api/applications/{app['id']}/offer",
        headers={"Authorization": f"Bearer {hr['token']}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "offer"
    login = client.post("/api/auth/login", json={"email": "ada@example.com", "password": "password"})
    mail = client.get("/api/messages", headers={"Authorization": f"Bearer {login.json()['token']}"})
    assert any(m["template_key"] == "offer_letter" for m in mail.json())
    acc = client.post(
        f"/api/applications/{app['id']}/accept-offer",
        headers={"Authorization": f"Bearer {login.json()['token']}"},
    )
    assert acc.json()["status"] == "hired"


def test_shortlist_technical_hr_round(client, tmp_path, monkeypatch):
    hr, app = _setup_screened(client, tmp_path, monkeypatch)
    token = {"Authorization": f"Bearer {hr['token']}"}
    sl = client.post(f"/api/applications/{app['id']}/advance", json={"status": "shortlist"}, headers=token)
    assert sl.status_code == 200
    assert sl.json()["status"] == "shortlist"
    start = datetime(2026, 9, 4, 15, 0, tzinfo=timezone.utc)
    client.post("/api/interviews", json={"application_id": app["id"], "start_at": start.isoformat()}, headers=token)
    tech = client.post(f"/api/applications/{app['id']}/advance", json={"status": "technical"}, headers=token)
    assert tech.status_code == 200
    assert tech.json()["status"] == "technical"
    hr_round = client.post(f"/api/applications/{app['id']}/advance", json={"status": "hr_round"}, headers=token)
    assert hr_round.status_code == 200
    assert hr_round.json()["status"] == "hr_round"
    skip = client.post(f"/api/applications/{app['id']}/advance", json={"status": "shortlist"}, headers=token)
    assert skip.status_code == 409
