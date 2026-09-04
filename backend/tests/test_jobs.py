def _hr(client):
    r = client.post("/api/auth/register", json={
        "email": "hr@example.com", "password": "password", "name": "Pat", "role": "hr"
    })
    return r.json()["token"]


def test_jd_contains_sections(client):
    token = _hr(client)
    r = client.post("/api/jobs", json={
        "title": "Backend Engineer",
        "team": "Platform",
        "location": "Remote",
        "seniority": "mid",
        "required_skills": ["python", "sql"],
        "nice_to_have": ["aws"],
        "min_years": 3,
        "education": "bachelor",
        "narrative": "Build recruitment APIs.",
    }, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    md = r.json()["jd_markdown"]
    for part in ["Backend Engineer", "Platform", "Remote", "python", "Build recruitment APIs", "How to apply"]:
        assert part in md
    assert r.json()["status"] == "draft"


def test_public_lists_only_open(client):
    token = _hr(client)
    created = client.post("/api/jobs", json={
        "title": "X", "team": "T", "location": "L", "seniority": "j",
        "required_skills": ["go"], "nice_to_have": [], "min_years": 0,
        "education": "none", "narrative": "n",
    }, headers={"Authorization": f"Bearer {token}"}).json()
    pub = client.get("/api/jobs")
    assert pub.json() == [] or all(j["status"] == "open" for j in pub.json())
    client.post(f"/api/jobs/{created['id']}/publish", headers={"Authorization": f"Bearer {token}"})
    pub2 = client.get("/api/jobs")
    assert any(j["id"] == created["id"] for j in pub2.json())


def test_candidate_cannot_create_job(client):
    r = client.post("/api/auth/register", json={
        "email": "c@example.com", "password": "password", "name": "C", "role": "candidate"
    })
    j = client.post("/api/jobs", json={"title": "X", "team": "t", "location": "l", "seniority": "j",
        "required_skills": [], "nice_to_have": [], "min_years": 0, "education": "none", "narrative": "n"},
        headers={"Authorization": f"Bearer {r.json()['token']}"})
    assert j.status_code == 403


def test_hr_lists_drafts_and_public_omits_hr_fields(client):
    token = _hr(client)
    created = client.post("/api/jobs", json={
        "title": "X", "team": "T", "location": "L", "seniority": "j",
        "required_skills": ["go"], "nice_to_have": [], "min_years": 0,
        "education": "none", "narrative": "secret narrative",
    }, headers={"Authorization": f"Bearer {token}"}).json()
    hr_list = client.get("/api/jobs", headers={"Authorization": f"Bearer {token}"})
    assert any(j["id"] == created["id"] and j["status"] == "draft" for j in hr_list.json())
    client.post(f"/api/jobs/{created['id']}/publish", headers={"Authorization": f"Bearer {token}"})
    pub = client.get("/api/jobs").json()
    job = next(j for j in pub if j["id"] == created["id"])
    assert "narrative" not in job
    assert "screen_threshold" not in job
    assert "created_by" not in job


def test_patch_close_and_export(client):
    token = _hr(client)
    created = client.post("/api/jobs", json={
        "title": "X", "team": "T", "location": "L", "seniority": "j",
        "required_skills": ["go"], "nice_to_have": [], "min_years": 0,
        "education": "none", "narrative": "n",
    }, headers={"Authorization": f"Bearer {token}"}).json()
    job_id = created["id"]
    patched = client.patch(
        f"/api/jobs/{job_id}",
        json={"title": "Updated"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "Updated"
    assert "Updated" in patched.json()["jd_markdown"]
    md = client.get(f"/api/jobs/{job_id}/export.md", headers={"Authorization": f"Bearer {token}"})
    assert md.status_code == 200
    assert "markdown" in md.headers["content-type"]
    assert "Updated" in md.text
    pdf = client.get(f"/api/jobs/{job_id}/export.pdf", headers={"Authorization": f"Bearer {token}"})
    assert pdf.status_code == 200
    assert "pdf" in pdf.headers["content-type"]
    assert pdf.content[:4] == b"%PDF"
    client.post(f"/api/jobs/{job_id}/publish", headers={"Authorization": f"Bearer {token}"})
    closed = client.post(f"/api/jobs/{job_id}/close", headers={"Authorization": f"Bearer {token}"})
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
    pub = client.get("/api/jobs")
    assert all(j["id"] != job_id for j in pub.json())


def test_generate_jd_sections():
    from app.modules.jobs.jd import generate_jd

    md = generate_jd(
        {
            "title": "Backend Engineer",
            "team": "Platform",
            "location": "Remote",
            "seniority": "mid",
            "required_skills": ["python", "sql"],
            "nice_to_have": ["aws"],
            "min_years": 3,
            "education": "bachelor",
            "narrative": "Build recruitment APIs.",
        },
        "http://127.0.0.1:5173/jobs/abc",
    )
    for heading in [
        "Title", "Team", "Location", "Seniority", "Role summary",
        "Required skills", "Nice to have", "Experience", "Education", "How to apply",
    ]:
        assert heading in md
    assert "http://127.0.0.1:5173/jobs/abc" in md
