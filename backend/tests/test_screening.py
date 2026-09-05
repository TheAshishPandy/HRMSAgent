from types import SimpleNamespace
from io import BytesIO

from app.modules.screening.score import keyword_score, infer_years, infer_education


def test_all_skills_hit():
    job = SimpleNamespace(required_skills=["python", "sql"], min_years=0, education="none", nice_to_have=[])
    score, breakdown = keyword_score("python and sql engineer", job)
    assert breakdown["skills"] == 1.0
    assert score >= 0.6


def test_years_ratio():
    job = SimpleNamespace(required_skills=[], min_years=4, education="none", nice_to_have=[])
    score, breakdown = keyword_score("2 years of work", job)
    assert breakdown["years"] == 0.5


def test_education_rank():
    job = SimpleNamespace(required_skills=[], min_years=0, education="master", nice_to_have=[])
    _, b = keyword_score("phd in cs", job)
    assert b["education"] == 1.0
    _, b2 = keyword_score("bachelor of arts", job)
    assert b2["education"] == 0.0


def test_infer_years_cap():
    assert infer_years("99 years") == 40
    assert infer_education("Master of Science") == "master"


def _hr_job(client, skills, min_years=0, education="none"):
    token = client.post("/api/auth/register", json={
        "email": "hr@example.com", "password": "password", "name": "Pat", "role": "hr"
    }).json()["token"]
    job = client.post("/api/jobs", json={
        "title": "X", "team": "T", "location": "L", "seniority": "j",
        "required_skills": skills, "nice_to_have": [], "min_years": min_years,
        "education": education, "narrative": "n",
    }, headers={"Authorization": f"Bearer {token}"}).json()
    client.post(f"/api/jobs/{job['id']}/publish", headers={"Authorization": f"Bearer {token}"})
    return token, job["id"]


def test_threshold_promotes(client, tmp_path, monkeypatch):
    monkeypatch.setenv("RESUME_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()
    token, job_id = _hr_job(client, ["python", "sql"])
    r = client.post(
        f"/api/jobs/{job_id}/apply",
        data={"email": "ada@example.com", "password": "password", "name": "Ada"},
        files={"resume": ("cv.txt", BytesIO(b"python sql engineer with 5 years bachelor"), "text/plain")},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "screened"


def test_below_threshold_stays_applied(client, tmp_path, monkeypatch):
    monkeypatch.setenv("RESUME_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()
    token, job_id = _hr_job(client, ["python", "sql", "kubernetes"], min_years=8, education="phd")
    r = client.post(
        f"/api/jobs/{job_id}/apply",
        data={"email": "ada@example.com", "password": "password", "name": "Ada"},
        files={"resume": ("cv.txt", BytesIO(b"retail associate"), "text/plain")},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "applied"


def test_llm_skipped_without_key(monkeypatch):
    monkeypatch.setenv("USER_LLM_API_KEY", "")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.modules.screening.llm import maybe_llm_rank
    job = SimpleNamespace(title="X", required_skills=["python"])
    assert maybe_llm_rank("python", job) is None
