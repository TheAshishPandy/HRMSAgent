from io import BytesIO


def test_export_own_applications_only(client, tmp_path, monkeypatch):
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
    client.post(
        f"/api/jobs/{job['id']}/apply",
        data={"email": "ada@example.com", "password": "password", "name": "Ada"},
        files={"resume": ("cv.txt", BytesIO(b"python"), "text/plain")},
    )
    client.post(
        f"/api/jobs/{job['id']}/apply",
        data={"email": "bob@example.com", "password": "password", "name": "Bob"},
        files={"resume": ("cv.txt", BytesIO(b"python"), "text/plain")},
    )
    ada = client.post("/api/auth/login", json={"email": "ada@example.com", "password": "password"}).json()
    exp = client.get("/api/me/export", headers={"Authorization": f"Bearer {ada['token']}"}).json()
    assert exp["profile"]["email"] == "ada@example.com"
    assert len(exp["applications"]) == 1


def test_delete_anonymizes(client, tmp_path, monkeypatch):
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
    ada = client.post("/api/auth/login", json={"email": "ada@example.com", "password": "password"}).json()
    d = client.delete("/api/me", headers={"Authorization": f"Bearer {ada['token']}"})
    assert d.status_code == 200
    login = client.post("/api/auth/login", json={"email": "ada@example.com", "password": "password"})
    assert login.status_code == 401
    listed = client.get(
        f"/api/applications/{app['id']}",
        headers={"Authorization": f"Bearer {hr['token']}"},
    ).json()
    assert listed["candidate_name"].startswith("deleted:")
