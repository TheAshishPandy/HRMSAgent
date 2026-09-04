from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    title: str
    team: str
    location: str
    seniority: str
    required_skills: list[str]
    nice_to_have: list[str]
    min_years: int = Field(ge=0)
    education: str
    narrative: str
    screen_threshold: float | None = None


class JobUpdate(BaseModel):
    title: str | None = None
    team: str | None = None
    location: str | None = None
    seniority: str | None = None
    required_skills: list[str] | None = None
    nice_to_have: list[str] | None = None
    min_years: int | None = Field(default=None, ge=0)
    education: str | None = None
    narrative: str | None = None
    jd_markdown: str | None = None
    screen_threshold: float | None = None
