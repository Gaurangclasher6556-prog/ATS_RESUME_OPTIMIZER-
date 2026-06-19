"""
jd_utils.py — Job-description ingestion and robust PDF text extraction.

Two helpers:
  • fetch_jd_from_url(url): pull a job posting from a URL and return clean text,
    so users can paste a link instead of copy-pasting the whole description.
  • extract_pdf_text(file_bytes): extract text from a PDF, automatically falling
    back to OCR for image-based / scanned resumes (which fitz.get_text() returns
    empty for).
"""

from __future__ import annotations

import re
import urllib.request
import urllib.error

import fitz  # PyMuPDF

_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_ANGLE_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\n\s*\n\s*\n+")

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def _html_to_text(html: str) -> str:
    html = _TAG_RE.sub(" ", html)          # drop <script>/<style> blocks
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</(p|div|li|h[1-6])>", "\n", html, flags=re.IGNORECASE)
    text = _ANGLE_RE.sub("", html)          # strip remaining tags
    # Unescape a few common entities.
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                 ("&gt;", ">"), ("&#39;", "'"), ("&quot;", '"')):
        text = text.replace(a, b)
    text = _WS_RE.sub("\n\n", text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def fetch_jd_from_url(url: str, timeout: int = 15) -> str:
    """
    Fetch a job posting from a URL and return readable text.

    Note: many large job boards render content with JavaScript or block bots,
    in which case the returned text may be partial — the caller should let the
    user review/edit it. Raises ValueError on a clearly failed fetch.
    """
    if not re.match(r"^https?://", url.strip(), re.IGNORECASE):
        url = "https://" + url.strip()
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            html = resp.read().decode(charset, errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        raise ValueError(f"Could not fetch the URL ({e}). Paste the text manually.")
    text = _html_to_text(html)
    if len(text) < 50:
        raise ValueError("The page returned little readable text (it may require "
                         "JavaScript). Please paste the job description manually.")
    return text


def extract_pdf_text(file_bytes: bytes) -> str:
    """
    Extract text from a PDF. If the PDF is image-based (no embedded text), fall
    back to OCR via pytesseract when available, so scanned resumes still work.
    """
    if not file_bytes:
        return ""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = "".join(page.get_text() for page in doc)
    if text.strip():
        return text

    # No embedded text — attempt OCR (best-effort; requires pytesseract + tesseract).
    try:
        import pytesseract
        from PIL import Image
        import io as _io

        ocr_text = []
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.open(_io.BytesIO(pix.tobytes("png")))
            ocr_text.append(pytesseract.image_to_string(img))
        return "\n".join(ocr_text)
    except Exception:
        # OCR unavailable — return empty so the UI shows its existing guidance.
        return ""
