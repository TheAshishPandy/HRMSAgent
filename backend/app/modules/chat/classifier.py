import re

IDENTITY_ASK = re.compile(
    r"what is your (employee|candidate) id|which (company|department)|what is your name",
    re.I,
)

OTHER_PERSON = re.compile(
    r"\b(employee|emp|candidate)\s+(id\s+)?[A-Za-z0-9@._-]+|show me .+ salary|other@|salary of\b",
    re.I,
)

FOLLOW_UP = re.compile(
    r"^(how many are|what about|and the|those|that one|casual\??$|sick\??$)",
    re.I,
)


def classify(message: str, user_type: str, history: list[dict] | None = None) -> list[str]:
    q = (message or "").lower()
    hist = " ".join((m.get("content") or "") for m in (history or [])[-6:]).lower()
    combined = q + " " + hist
    agents: list[str] = []

    if FOLLOW_UP.search(q.strip()) and any(k in hist for k in ("leave", "balance", "casual", "sick", "annual")):
        agents.append("employee_data")
        agents.append("leave")

    leave_kw = ("leave", "pto", "time off", "casual", "sick leave", "annual leave", "holiday", "carry forward", "days off")
    att_kw = ("attendance", "check in", "check-in", "checked in", "days did i work", "present", "late", "absent")
    pay_kw = ("salary", "payslip", "pay slip", "payroll", "deduction", "gross", "net pay", "compensation", "tax")
    profile_kw = ("employee number", "employee id", "my manager", "department", "designation", "joining date", "who am i")
    cand_kw = ("application", "interview", "recruiter", "what stage", "applied", "candidate id", "job did i")
    policy_kw = (
        "policy", "handbook", "notice period", "documents", "joining", "code of conduct",
        "rules", "benefits", "insurance", "carry forward", "required for", "guideline",
        "circular", "announcement",
    )

    if user_type in ("employee", "staff"):
        if any(k in q for k in leave_kw):
            agents.extend(["employee_data", "leave"])
        if any(k in q for k in att_kw):
            agents.extend(["employee_data", "attendance"])
        if any(k in q for k in pay_kw):
            agents.extend(["employee_data", "payroll"])
        if any(k in q for k in profile_kw) or "my department" in q or "my designation" in q:
            agents.append("employee_data")
        if any(k in q for k in policy_kw):
            agents.extend(["rag", "hr_policy"])
        if "can i take" in q or "eligible" in q:
            agents.extend(["employee_data", "leave", "rag", "hr_policy"])
    if user_type == "candidate":
        if any(k in q for k in cand_kw) or "status" in q:
            agents.append("candidate_data")
        if any(k in q for k in policy_kw) or "reschedule" in q or "joining" in q:
            agents.extend(["rag", "recruitment"])
        if not agents:
            agents.append("candidate_data")
    if not agents:
        if user_type == "candidate":
            agents.append("candidate_data")
        else:
            agents.extend(["employee_data", "rag"])

    seen = []
    for a in agents:
        if a not in seen:
            seen.append(a)
    if "rag" not in seen and any(k in combined for k in policy_kw):
        seen.append("rag")
    return seen


def wants_other_person_data(message: str) -> bool:
    return bool(OTHER_PERSON.search(message or ""))
