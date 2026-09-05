from pydantic import BaseModel


class ParsedTextIn(BaseModel):
    text: str


class OverrideIn(BaseModel):
    decision: str
