import math
import re
from collections import Counter

from sqlalchemy.orm import Session

from app.models import KnowledgeChunk, KnowledgeDocument

_WORD = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "is", "are", "was", "be",
    "on", "at", "by", "with", "this", "that", "it", "as", "from", "my", "what", "how",
}


def tokenize(text: str) -> list[str]:
    return [w for w in _WORD.findall((text or "").lower()) if w not in _STOP and len(w) > 1]


def chunk_text(body: str, title: str = "") -> list[tuple[str, str]]:
    parts = re.split(r"\n{2,}", (body or "").strip())
    out = []
    buf = []
    for part in parts:
        section = title
        line = part.strip()
        if not line:
            continue
        first = line.split("\n", 1)[0].strip()
        if len(first) < 80 and not first.endswith("."):
            section = first
        buf.append((section, line))
    if not buf:
        return [(title, body or "")]
    merged: list[tuple[str, str]] = []
    acc_sec, acc = "", ""
    for sec, text in buf:
        if len(acc) + len(text) > 700 and acc:
            merged.append((acc_sec or title, acc.strip()))
            acc, acc_sec = text, sec
        else:
            acc_sec = acc_sec or sec
            acc = (acc + "\n\n" + text).strip()
    if acc:
        merged.append((acc_sec or title, acc.strip()))
    return merged or [(title, body or "")]


def index_document(db: Session, doc: KnowledgeDocument) -> None:
    db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == doc.id).delete()
    for i, (section, text) in enumerate(chunk_text(doc.body, doc.title)):
        db.add(KnowledgeChunk(
            document_id=doc.id,
            organization_id=doc.organization_id,
            text=text,
            section=section,
            ordinal=i,
        ))


def _visible(doc: KnowledgeDocument, user_type: str) -> bool:
    if doc.status != "published":
        return False
    if user_type == "candidate":
        return bool(doc.candidate_visible)
    return bool(doc.employee_visible)


def _tf(tokens: list[str]) -> Counter:
    return Counter(tokens)


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    keys = set(a) | set(b)
    dot = sum(a[k] * b[k] for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _bm25(query: list[str], doc_tokens: list[str], avgdl: float, k1: float = 1.2, b: float = 0.75) -> float:
    if not query or not doc_tokens:
        return 0.0
    tf = Counter(doc_tokens)
    dl = len(doc_tokens)
    score = 0.0
    for term in query:
        f = tf.get(term, 0)
        if not f:
            continue
        idf = 1.5
        denom = f + k1 * (1 - b + b * dl / max(avgdl, 1))
        score += idf * (f * (k1 + 1)) / denom
    return score


def search_documents(
    db: Session,
    organization_id: str | None,
    query: str,
    user_type: str,
    limit: int = 5,
    category: str | None = None,
) -> list[dict]:
    if not organization_id:
        return []
    qdocs = db.query(KnowledgeDocument).filter(KnowledgeDocument.organization_id == organization_id)
    if category:
        qdocs = qdocs.filter(KnowledgeDocument.category == category)
    docs = {d.id: d for d in qdocs.all() if _visible(d, user_type)}
    if not docs:
        return []
    chunks = (
        db.query(KnowledgeChunk)
        .filter(
            KnowledgeChunk.organization_id == organization_id,
            KnowledgeChunk.document_id.in_(list(docs.keys())),
        )
        .all()
    )
    if not chunks:
        for d in docs.values():
            index_document(db, d)
        db.flush()
        chunks = (
            db.query(KnowledgeChunk)
            .filter(
                KnowledgeChunk.organization_id == organization_id,
                KnowledgeChunk.document_id.in_(list(docs.keys())),
            )
            .all()
        )
    q_tokens = tokenize(query)
    q_tf = _tf(q_tokens)
    tokenized = [(c, tokenize(c.text + " " + c.section)) for c in chunks]
    avgdl = sum(len(t) for _, t in tokenized) / max(len(tokenized), 1)
    scored = []
    seen_text = set()
    for chunk, toks in tokenized:
        lex = _bm25(q_tokens, toks, avgdl)
        vec = _cosine(q_tf, _tf(toks))
        kw = sum(1 for t in q_tokens if t in toks)
        fused = 0.45 * lex + 0.4 * vec * 10 + 0.15 * kw
        key = chunk.text[:200]
        if key in seen_text:
            continue
        seen_text.add(key)
        scored.append((fused, chunk, lex, vec, kw))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for fused, chunk, lex, vec, kw in scored[:limit]:
        if fused <= 0:
            continue
        doc = docs.get(chunk.document_id)
        if doc is None:
            continue
        out.append({
            "document_id": doc.id,
            "title": doc.title,
            "category": doc.category,
            "section": chunk.section,
            "text": chunk.text,
            "version": doc.version,
            "score": round(fused, 4),
        })
    return out
