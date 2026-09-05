import re

EDU_RANK = {"none": 0, "bachelor": 1, "master": 2, "phd": 3}


def infer_education(text: str) -> str:
    t = text.lower()
    if re.search(r"\b(ph\.?d|doctorate|doctoral)\b", t):
        return "phd"
    if re.search(r"\b(master'?s?|msc|mba|m\.s\.?|m\.a\.?)\b", t):
        return "master"
    if re.search(r"\b(bachelor'?s?|bsc|b\.s\.?|b\.a\.?|\bba\b|\bbs\b)\b", t):
        return "bachelor"
    return "none"


def infer_years(text: str) -> float | None:
    found: list[float] = []
    for m in re.finditer(r"(\d+)\+?\s+years", text.lower()):
        found.append(float(m.group(1)))
    for m in re.finditer(
        r"(19|20)(\d{2})\s*[-–]\s*((?:19|20)\d{2}|present|now)",
        text.lower(),
    ):
        start = int(m.group(1) + m.group(2))
        end_raw = m.group(3)
        end = 2026 if end_raw in ("present", "now") else int(end_raw)
        found.append(float(max(0, end - start)))
    if not found:
        return None
    return min(40.0, max(found))


def keyword_score(text: str, job) -> tuple[float, dict]:
    t = text.lower()
    skills = list(job.required_skills or [])
    if not skills:
        skills_s = 1.0
    else:
        hits = 0
        for skill in skills:
            if re.search(rf"\b{re.escape(skill.lower())}\b", t):
                hits += 1
        skills_s = hits / len(skills)
    nice = list(job.nice_to_have or [])
    nice_hits = []
    for skill in nice:
        if re.search(rf"\b{re.escape(skill.lower())}\b", t):
            nice_hits.append(skill)
    min_years = int(job.min_years or 0)
    resume_years = infer_years(text)
    if min_years <= 0:
        years_s = 1.0
    elif resume_years is None:
        years_s = 0.0
    elif resume_years >= min_years:
        years_s = 1.0
    else:
        years_s = resume_years / min_years
    need = EDU_RANK.get(getattr(job, "education", "none") or "none", 0)
    got = EDU_RANK.get(infer_education(text), 0)
    edu_s = 1.0 if got >= need else 0.0
    score = 0.6 * skills_s + 0.25 * years_s + 0.15 * edu_s
    return score, {
        "skills": skills_s,
        "years": years_s,
        "education": edu_s,
        "nice_to_have": nice_hits,
        "resume_years": resume_years,
    }
