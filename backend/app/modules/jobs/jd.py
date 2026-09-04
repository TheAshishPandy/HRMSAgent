def generate_jd(job_fields: dict, apply_url: str) -> str:
    required = job_fields.get("required_skills") or []
    nice = job_fields.get("nice_to_have") or []
    required_md = "\n".join(f"- {s}" for s in required) if required else "-"
    nice_md = "\n".join(f"- {s}" for s in nice) if nice else "-"
    years = job_fields.get("min_years", 0)
    return "\n".join([
        "## Title",
        str(job_fields.get("title", "")),
        "",
        "## Team",
        str(job_fields.get("team", "")),
        "",
        "## Location",
        str(job_fields.get("location", "")),
        "",
        "## Seniority",
        str(job_fields.get("seniority", "")),
        "",
        "## Role summary",
        str(job_fields.get("narrative", "")),
        "",
        "## Required skills",
        required_md,
        "",
        "## Nice to have",
        nice_md,
        "",
        "## Experience",
        f"{years} years",
        "",
        "## Education",
        str(job_fields.get("education", "")),
        "",
        "## How to apply",
        apply_url,
        "",
    ])
