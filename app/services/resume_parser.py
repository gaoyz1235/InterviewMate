import logging
from io import BytesIO

from fastapi import UploadFile
from pypdf import PdfReader

logger = logging.getLogger(__name__)


async def parse_resume_file(file: UploadFile) -> str:
    """Extract text from an uploaded PDF resume.

    OCR is intentionally left as a later enhancement; the UI also supports
    pasted text so the core demo is not blocked by PDF extraction failures.
    """
    content = await file.read()
    logger.info(
        "resume_parser.read filename=%s content_type=%s bytes=%s",
        file.filename or "<empty>",
        file.content_type or "<unknown>",
        len(content),
    )
    if not content:
        logger.warning("resume_parser.empty filename=%s", file.filename or "<empty>")
        return ""

    if not (file.filename or "").lower().endswith(".pdf"):
        text = content.decode("utf-8", errors="ignore")
        logger.info("resume_parser.text_file.done filename=%s chars=%s", file.filename or "<empty>", len(text))
        return text

    reader = PdfReader(BytesIO(content))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    text = "\n\n".join(page for page in pages if page)
    logger.info("resume_parser.pdf.done filename=%s pages=%s chars=%s", file.filename or "<empty>", len(reader.pages), len(text))
    return text
