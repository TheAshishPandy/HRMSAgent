from pathlib import Path


def parse_resume(path: str) -> str:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".txt":
        return p.read_text(encoding="utf-8", errors="replace")
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(p))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)
    if suffix == ".docx":
        from docx import Document

        doc = Document(str(p))
        return "\n".join(para.text for para in doc.paragraphs)
    raise ValueError("unsupported")
