import json
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ChatConversation, ChatMessage, User
from app.modules.chat.classifier import classify, wants_other_person_data
from app.modules.chat.context import resolve_user_context
from app.modules.chat.rag import search_documents
from app.modules.chat.tools import (
    get_attendance,
    get_candidate_applications,
    get_employee_profile,
    get_leave_balances,
    get_leave_requests,
    get_payslips,
)

IDENTITY_PHRASES = (
    "what is your employee id",
    "what is your candidate id",
    "what is your name",
    "which department are you in",
    "which company do you belong to",
    "please provide your employee",
    "please provide your candidate",
)


def _maybe_llm(prompt: str) -> str | None:
    settings = get_settings()
    if not settings.user_llm_api_key:
        return None
    base = (settings.user_llm_base_url or "").rstrip("/")
    if not base:
        return None
    import httpx

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
        return r.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def _strip_identity_asks(text: str) -> str:
    low = text.lower()
    for p in IDENTITY_PHRASES:
        if p in low:
            text = re.sub(re.escape(p), "", text, flags=re.I)
    return text.strip()


def _fmt_money(n) -> str:
    try:
        v = float(n)
    except (TypeError, ValueError):
        return str(n)
    if v == int(v):
        return str(int(v))
    return f"{v:.2f}"


def synthesize(ctx: dict, message: str, facts: dict, sources: list[dict], agents: list[str], denied: bool) -> str:
    parts: list[str] = []
    profile = facts.get("profile")
    balances = facts.get("leave_balances") or []
    payslips = facts.get("payslips") or []
    apps = facts.get("applications") or []
    attendance = facts.get("attendance")
    requests = facts.get("leave_requests") or []
    q = message.lower()

    if denied:
        parts.append("I can only share your own records from this session. I am not allowed to retrieve another employee's data.")

    if profile and any(k in q for k in ("department", "designation", "joining", "manager", "who am i", "employee number", "employee id", "my name")):
        bits = [f"You are {profile['name']}"]
        if profile.get("designation"):
            bits.append(profile["designation"])
        if profile.get("department"):
            bits.append(f"in {profile['department']}")
        if ctx.get("organization_name"):
            bits.append(f"at {ctx['organization_name']}")
        parts.append(", ".join(bits) + ".")
        if profile.get("joining_date"):
            parts.append(f"Your joining date in the HR system is {profile['joining_date']}.")
        if profile.get("employee_id") and "employee" in q:
            parts.append(f"Your employee number from the HR system is {profile['employee_id']}.")
        if profile.get("manager"):
            parts.append(f"Your manager is {profile['manager']}.")

    if balances and any(k in q for k in ("leave", "pto", "casual", "sick", "annual", "how many", "balance", "days leave", "take 10", "take leave")):
        lines = [f"{b['leave_type']}: {b['remaining']} day(s) remaining" for b in balances if b.get("leave_type")]
        if lines:
            parts.append("Your current leave balance from the HR system is: " + "; ".join(lines) + ".")
        if "casual" in q:
            casual = next((b for b in balances if (b.get("leave_type") or "").lower() == "casual"), None)
            if casual:
                parts.append(f"Casual leave remaining is {casual['remaining']}.")
        if "can i take" in q or "10 days" in q:
            needed = 10
            m = re.search(r"(\d+)\s*days?", q)
            if m:
                needed = int(m.group(1))
            total = sum(float(b.get("remaining") or 0) for b in balances)
            annual = next((b for b in balances if (b.get("leave_type") or "").lower() == "annual"), None)
            pool = float(annual["remaining"]) if annual else total
            if pool < needed:
                parts.append(
                    f"You cannot take {needed} days leave because your available balance is {pool:g} day(s), which is insufficient."
                )
            else:
                parts.append(f"Your remaining balance of {pool:g} day(s) covers a {needed}-day request, subject to policy.")

    if requests and any(k in q for k in ("pending", "request", "approval")):
        pending = [r for r in requests if r.get("status") == "pending"]
        if pending:
            parts.append(f"You have {len(pending)} pending leave request(s) in the HR system.")
        else:
            parts.append("You have no pending leave requests.")

    if attendance and any(k in q for k in ("attendance", "worked", "check in", "present")):
        parts.append(f"Your attendance from the HR system shows {attendance.get('worked_days', 0)} worked day(s) in the recent records.")

    if "payslip" in q or "salary" in q or "payroll" in q or "deduction" in q:
        if payslips:
            latest = payslips[0]
            parts.append(
                f"Your latest payslip from the HR system is for {latest['period']}: "
                f"gross {_fmt_money(latest['gross'])}, tax {_fmt_money(latest['tax'])}, "
                f"other deductions {_fmt_money(latest['other_deductions'])}, net {_fmt_money(latest['net'])}."
            )
            if "why" in q or "deduct" in q:
                parts.append(
                    f"Tax of {_fmt_money(latest['tax'])} and other deductions of {_fmt_money(latest['other_deductions'])} "
                    f"were applied to gross {_fmt_money(latest['gross'])}."
                )
        elif any(k in q for k in ("payslip", "salary", "payroll")):
            parts.append("I could not retrieve your current payroll information. No payslip is available in the HR system.")

    if apps:
        latest = apps[0]
        parts.append(
            f"Your application for {latest.get('job_title') or 'the role'} is currently in the {latest.get('status')} stage."
        )
        if latest.get("interviews"):
            iv = latest["interviews"][0]
            if iv.get("start_at"):
                parts.append(f"Your interview is scheduled at {iv['start_at']} ({iv.get('timezone') or 'UTC'}).")
        if latest.get("recruiter"):
            parts.append(f"Your recruiter is {latest['recruiter']}.")

    if sources:
        quotes = []
        for s in sources[:3]:
            snippet = (s.get("text") or "").strip()
            if snippet:
                quotes.append(snippet[:400])
        if quotes:
            parts.append("According to " + sources[0]["title"] + ": " + quotes[0])

    if not parts:
        if ctx.get("user_type") == "candidate":
            parts.append("I could not find matching application records for your account.")
        else:
            parts.append("I could not find grounded information for that question in your HR records or published policies.")

    if sources:
        titles = ", ".join(sorted({s["title"] for s in sources}))
        parts.append("Sources: " + titles + "; live HR system data." if facts else "Sources: " + titles + ".")
    elif facts:
        parts.append("This answer uses live data from the HR system.")

    reply = "\n\n".join(p for p in parts if p)
    reply = _strip_identity_asks(reply)
    for p in IDENTITY_PHRASES:
        if p in reply.lower():
            reply = "I already have your identity from this login. " + reply
            break
    return reply


def _ensure_conversation(db: Session, user: User, ctx: dict, conversation_id: str | None, title: str) -> ChatConversation:
    if conversation_id:
        conv = (
            db.query(ChatConversation)
            .filter(ChatConversation.id == conversation_id, ChatConversation.user_id == user.id)
            .first()
        )
        if conv:
            return conv
    conv = ChatConversation(
        user_id=user.id,
        organization_id=ctx.get("organization_id"),
        title=title[:80] or "New chat",
    )
    db.add(conv)
    db.flush()
    return conv


def handle_message(db: Session, user: User, message: str, conversation_id: str | None = None) -> dict:
    ctx = resolve_user_context(db, user)
    conv = _ensure_conversation(db, user, ctx, conversation_id, message[:60])
    history_rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conv.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in history_rows[-8:]]
    agents = classify(message, ctx["user_type"], history)
    denied = wants_other_person_data(message)
    facts: dict = {}
    sources: list[dict] = []
    activity = ["Identified user as " + ctx["user_type"].title()]

    if "employee_data" in agents or "leave" in agents or "attendance" in agents or "payroll" in agents:
        profile = get_employee_profile(db, ctx)
        if profile:
            facts["profile"] = profile
            activity.append("Retrieved employee context")
        if "leave" in agents or "employee_data" in agents:
            facts["leave_balances"] = get_leave_balances(db, ctx)
            facts["leave_requests"] = get_leave_requests(db, ctx)
            activity.append("Checking live leave balance")
        if "attendance" in agents:
            facts["attendance"] = get_attendance(db, ctx)
            activity.append("Checking attendance records")
        if "payroll" in agents:
            facts["payslips"] = get_payslips(db, ctx)
            activity.append("Checking live payroll data")

    if "candidate_data" in agents or "recruitment" in agents:
        facts["applications"] = get_candidate_applications(db, ctx)
        activity.append("Retrieved candidate applications")

    if "rag" in agents or "hr_policy" in agents:
        activity.append("Searching HR knowledge base")
        sources = search_documents(db, ctx.get("organization_id"), message, ctx["user_type"])
        facts["policies"] = [{"title": s["title"], "text": s["text"]} for s in sources]

    prompt = (
        "Answer using ONLY the JSON facts and policy excerpts. Never invent numbers. "
        "Never ask for employee id, candidate id, name, department, or company. "
        "Identity is already known from the session.\n"
        f"User: {json.dumps({k: ctx[k] for k in ('user_type','name','department','organization_name') if ctx.get(k)})}\n"
        f"Question: {message}\n"
        f"Facts: {json.dumps(facts, default=str)[:6000]}\n"
        f"Policies: {json.dumps(sources, default=str)[:4000]}\n"
    )
    llm_text = _maybe_llm(prompt)
    reply = synthesize(ctx, message, facts, sources, agents, denied)
    if llm_text:
        cleaned = _strip_identity_asks(llm_text)
        if cleaned and all(p not in cleaned.lower() for p in IDENTITY_PHRASES):
            if "could not" not in reply.lower() or "could not" in cleaned.lower():
                reply = cleaned
                if sources and "source" not in reply.lower():
                    reply += "\n\nSources: " + ", ".join(sorted({s['title'] for s in sources})) + "."

    activity.append("Generating response")
    db.add(ChatMessage(conversation_id=conv.id, role="user", content=message))
    db.add(ChatMessage(
        conversation_id=conv.id,
        role="assistant",
        content=reply,
        agents=agents,
        sources=[{"title": s["title"], "section": s.get("section"), "document_id": s["document_id"]} for s in sources],
    ))
    conv.updated_at = datetime.now(timezone.utc)
    if conv.title == "New chat" or conv.title == message[:60]:
        conv.title = message[:60]
    db.commit()
    return {
        "conversation_id": conv.id,
        "reply": reply,
        "agents": agents,
        "sources": [
            {
                "title": s["title"],
                "section": s.get("section") or "",
                "category": s.get("category"),
                "version": s.get("version"),
                "document_id": s["document_id"],
            }
            for s in sources
        ],
        "cards": _cards(facts),
        "activity": activity,
        "context": {
            "user_type": ctx["user_type"],
            "employee_id": ctx.get("employee_id"),
            "candidate_id": ctx.get("candidate_id"),
            "organization_id": ctx.get("organization_id"),
            "name": ctx.get("name"),
            "department": ctx.get("department"),
        },
        "denied_cross_user": denied,
    }


def _cards(facts: dict) -> list[dict]:
    cards = []
    bals = facts.get("leave_balances") or []
    if bals:
        cards.append({
            "type": "leave_balance",
            "title": "Leave balance",
            "items": [{"label": b["leave_type"], "value": b["remaining"]} for b in bals],
        })
    slips = facts.get("payslips") or []
    if slips:
        s = slips[0]
        cards.append({
            "type": "payslip",
            "title": f"Payslip {s['period']}",
            "items": [
                {"label": "Net", "value": s["net"]},
                {"label": "Gross", "value": s["gross"]},
                {"label": "Tax", "value": s["tax"]},
                {"label": "Deductions", "value": s["other_deductions"]},
            ],
        })
    apps = facts.get("applications") or []
    if apps:
        a = apps[0]
        cards.append({
            "type": "application",
            "title": a.get("job_title") or "Application",
            "items": [{"label": "Status", "value": a.get("status")}],
        })
    return cards
