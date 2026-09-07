from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import ChatConversation, ChatMessage, KnowledgeDocument, User
from app.modules.chat.context import resolve_user_context
from app.modules.chat.rag import index_document
from app.modules.chat.supervisor import handle_message
from app.modules.workforce import assert_org

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatIn(BaseModel):
    message: str
    conversation_id: str | None = None


class DocIn(BaseModel):
    title: str
    body: str
    category: str = "faq"
    version: str = "1.0"
    employee_visible: bool = True
    candidate_visible: bool = False


@router.get("/context")
def chat_context(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return resolve_user_context(db, user)


@router.get("/conversations")
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(ChatConversation)
        .filter(ChatConversation.user_id == user.id)
        .order_by(ChatConversation.updated_at.desc())
        .limit(40)
        .all()
    )
    return [
        {
            "id": c.id,
            "title": c.title,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in rows
    ]


@router.get("/conversations/{cid}")
def get_conversation(cid: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(ChatConversation).filter(ChatConversation.id == cid, ChatConversation.user_id == user.id).first()
    if conv is None:
        raise HTTPException(status_code=404, detail="Not found")
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conv.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return {
        "id": conv.id,
        "title": conv.title,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "agents": m.agents,
                "sources": m.sources,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs
        ],
    }


@router.post("/messages")
def post_message(body: ChatIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    text = (body.message or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="message required")
    if len(text) > 4000:
        raise HTTPException(status_code=422, detail="message too long")
    return handle_message(db, user, text, body.conversation_id)


@router.get("/documents")
def list_docs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in ("hr", "super_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    org_id = user.organization_id
    q = db.query(KnowledgeDocument)
    if user.role != "super_admin":
        if not org_id:
            return []
        q = q.filter(KnowledgeDocument.organization_id == org_id)
    rows = q.order_by(KnowledgeDocument.title).all()
    return [
        {
            "id": d.id,
            "title": d.title,
            "category": d.category,
            "version": d.version,
            "employee_visible": bool(d.employee_visible),
            "candidate_visible": bool(d.candidate_visible),
        }
        for d in rows
    ]


@router.post("/documents")
def create_doc(body: DocIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in ("hr", "super_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    org_id = user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="User has no organization")
    if user.role != "super_admin":
        assert_org(user, org_id)
    doc = KnowledgeDocument(
        organization_id=org_id,
        title=body.title.strip(),
        body=body.body,
        category=body.category,
        version=body.version,
        employee_visible=1 if body.employee_visible else 0,
        candidate_visible=1 if body.candidate_visible else 0,
        status="published",
    )
    db.add(doc)
    db.flush()
    index_document(db, doc)
    db.commit()
    db.refresh(doc)
    return {"id": doc.id, "title": doc.title, "category": doc.category}
