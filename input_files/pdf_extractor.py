"""
input_files/pdf_extractor.py
Extracts text from PDF files using PyMuPDF (fitz),
chunks the text into ≤9500-word pieces, and saves them to extracted_data/.
"""

from pathlib import Path
from typing import Tuple, List
import io

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None  # Handled gracefully below

CHUNK_SIZE = 9500          # Maximum words per chunk
OUTPUT_DIR = Path("extracted_data")


# ── Public API ────────────────────────────────────────────────────────────────

def process_pdf_file(uploaded_file) -> Tuple[bool, str]:
    """
    Full pipeline: receive a Streamlit UploadedFile (PDF),
    extract text, chunk it, and save chunks to disk.

    Returns:
        (True, success_message)  on success
        (False, error_message)   on failure
    """
    if fitz is None:
        return False, "❌ PyMuPDF is not installed. Run: pip install pymupdf"

    try:
        # 1. Extract text
        raw_text = extract_text_from_pdf(uploaded_file)
        if not raw_text.strip():
            return False, "⚠️ No text could be extracted from the PDF (it may be scanned/image-only)."

        # 2. Chunk text
        chunks = split_into_chunks(raw_text, max_words=CHUNK_SIZE)

        # 3. Save chunks
        stem = Path(uploaded_file.name).stem          # e.g. "research_paper"
        saved_paths = save_chunks(chunks, stem)

        return True, f"✅ PDF processed — saved {len(saved_paths)} chunk(s) for '{uploaded_file.name}'."

    except Exception as exc:
        return False, f"❌ PDF processing failed: {exc}"


# ── Internal helpers ──────────────────────────────────────────────────────────

def extract_text_from_pdf(uploaded_file) -> str:
    """Read the PDF bytes and extract all text page by page."""
    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    pages_text = []
    for page in doc:
        pages_text.append(page.get_text())

    doc.close()
    return "\n".join(pages_text)


def split_into_chunks(text: str, max_words: int = CHUNK_SIZE) -> List[str]:
    """
    Split *text* into chunks where each chunk has at most *max_words* words.
    Word boundaries are preserved — no word is ever cut in half.
    """
    words = text.split()
    chunks = []

    for start in range(0, len(words), max_words):
        chunk_words = words[start : start + max_words]
        chunks.append(" ".join(chunk_words))

    return chunks


def save_chunks(chunks: List[str], stem: str) -> List[Path]:
    """
    Write each chunk to extracted_data/<stem>_part01.txt, _part02.txt, …
    Returns the list of paths that were written.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    saved = []

    for i, chunk in enumerate(chunks, start=1):
        filename = OUTPUT_DIR / f"{stem}_part{i:02d}.txt"
        filename.write_text(chunk, encoding="utf-8")
        saved.append(filename)

    return saved