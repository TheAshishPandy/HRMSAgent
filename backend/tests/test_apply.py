from io import BytesIO


def _open_job(client, skills=None):
    token = client.post("/api/auth/register", json={
        "email": "hr@example.com", "password": "password", "name": "Pat", "role": "hr"
    }).json()["token"]
    job = client.post("/api/jobs", json={
        "title": "X", "team": "T", "location": "L", "seniority": "j",
        "required_skills": skills or ["python"], "nice_to_have": [], "min_years": 0,
        "education": "none", "narrative": "n",
    }, headers={"Authorization": f"Bearer {token}"}).json()
    client.post(f"/api/jobs/{job['id']}/publish", headers={"Authorization": f"Bearer {token}"})
    return token, job["id"]


def test_apply_creates_candidate_and_application(client, tmp_path, monkeypatch):
    monkeypatch.setenv("RESUME_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()
    token, job_id = _open_job(client)
    files = {"resume": ("cv.txt", BytesIO(b"python developer with 4 years"), "text/plain")}
    r = client.post(
        f"/api/jobs/{job_id}/apply",
        data={"email": "ada@example.com", "password": "password", "name": "Ada"},
        files=files,
    )
    assert r.status_code == 200
    assert r.json()["status"] in ("applied", "screened")
    assert r.json()["job_id"] == job_id


def test_duplicate_apply_409(client, tmp_path, monkeypatch):
    monkeypatch.setenv("RESUME_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()
    token, job_id = _open_job(client)
    files = {"resume": ("cv.txt", BytesIO(b"python developer with 4 years"), "text/plain")}
    data = {"email": "ada@example.com", "password": "password", "name": "Ada"}
    first = client.post(f"/api/jobs/{job_id}/apply", data=data, files=files)
    assert first.status_code == 200
    second = client.post(
        f"/api/jobs/{job_id}/apply",
        data=data,
        files={"resume": ("cv.txt", BytesIO(b"python developer with 4 years"), "text/plain")},
    )
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "duplicate_application"


def test_unsupported_type_415(client, tmp_path, monkeypatch):
    monkeypatch.setenv("RESUME_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()
    token, job_id = _open_job(client)
    r = client.post(
        f"/api/jobs/{job_id}/apply",
        data={"email": "ada@example.com", "password": "password", "name": "Ada"},
        files={"resume": ("cv.exe", BytesIO(b"xx"), "application/octet-stream")},
    )
    assert r.status_code == 415
