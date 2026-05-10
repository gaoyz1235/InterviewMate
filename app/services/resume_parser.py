from io import BytesIO

from fastapi import UploadFile
from pypdf import PdfReader


async def parse_resume_file(file: UploadFile) -> str:
    """Extract text from an uploaded PDF resume.

    OCR is intentionally left as a later enhancement; the UI also supports
    pasted text so the core demo is not blocked by PDF extraction failures.
    """
    content = await file.read()
    if not content:
        return ""

    if not (file.filename or "").lower().endswith(".pdf"):
        return content.decode("utf-8", errors="ignore")

    reader = PdfReader(BytesIO(content))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n\n".join(page for page in pages if page)
