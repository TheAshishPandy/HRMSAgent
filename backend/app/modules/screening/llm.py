from app.config import get_settings


def maybe_llm_rank(text: str, job) -> tuple[int, str] | None:
    settings = get_settings()
    if not settings.user_llm_api_key:
        return None
    base = (settings.user_llm_base_url or "").rstrip("/")
    if not base:
        return None
    import httpx

    prompt = (
        "Score this resume 0-100 for the job. Reply as JSON "
        '{"score": <int>, "rationale": "<one sentence>"}.\n'
        f"Job: {job.title} skills={job.required_skills}\nResume:\n{text[:6000]}"
    )
    try:
        r = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {settings.user_llm_api_key}"},
            json={
                "model": settings.user_llm_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            },
            timeout=20.0,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        import json
        import re

        m = re.search(r"\{.*\}", content, re.S)
        data = json.loads(m.group(0) if m else content)
        score = int(data["score"])
        score = max(0, min(100, score))
        rationale = str(data.get("rationale") or "")[:500]
        return score, rationale
    except Exception:
        return None
