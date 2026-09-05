from io import BytesIO
from unittest.mock import MagicMock, patch


def test_screen_out_creates_rejection_message(client, tmp_path, monkeypatch):
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
        files={"resume": ("cv.txt", BytesIO(b"hello"), "text/plain")},
    ).json()
    client.post(
        f"/api/applications/{app['id']}/reject",
        headers={"Authorization": f"Bearer {hr['token']}"},
    )
    login = client.post("/api/auth/login", json={"email": "ada@example.com", "password": "password"})
    mail = client.get("/api/messages", headers={"Authorization": f"Bearer {login.json()['token']}"})
    assert any(m["template_key"] == "rejection" for m in mail.json())
    assert all(m["smtp_sent_at"] is None for m in mail.json())


def test_smtp_retry_mocked(client, tmp_path, monkeypatch):
    monkeypatch.setenv("RESUME_DIR", str(tmp_path))
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
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
    with patch("smtplib.SMTP") as smtp_cls:
        inst = MagicMock()
        smtp_cls.return_value.__enter__.return_value = inst
        app = client.post(
            f"/api/jobs/{job['id']}/apply",
            data={"email": "ada@example.com", "password": "password", "name": "Ada"},
            files={"resume": ("cv.txt", BytesIO(b"hello"), "text/plain")},
        ).json()
        client.post(
            f"/api/applications/{app['id']}/reject",
            headers={"Authorization": f"Bearer {hr['token']}"},
        )
        login = client.post("/api/auth/login", json={"email": "ada@example.com", "password": "password"})
        mail = client.get("/api/messages", headers={"Authorization": f"Bearer {login.json()['token']}"})
        mid = mail.json()[0]["id"]
        client.post(f"/api/messages/{mid}/retry-smtp", headers={"Authorization": f"Bearer {hr['token']}"})
        assert smtp_cls.called
