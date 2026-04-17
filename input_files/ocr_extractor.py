"""
input_files/ocr_extractor.py
Extracts text from image files using Tesseract OCR,
chunks the text into ≤9500-word pieces, and saves them to extracted_data/.
"""

from pathlib import Path
from typing import Tuple, List
import tempfile

try:
    from PIL import Image
    import pytesseract
except ImportError:
    pytesseract = None  # Handled gracefully in extract_text_from_image()

CHUNK_SIZE = 9500          # Maximum words per chunk
OUTPUT_DIR = Path("extracted_data")


# ── Public API ────────────────────────────────────────────────────────────────

def process_ocr_file(uploaded_file) -> Tuple[bool, str]:
    """
    Full pipeline: receive a Streamlit UploadedFile (image),
    extract text, chunk it, and save chunks to disk.

    Returns:
        (True, success_message)  on success
        (False, error_message)   on failure
    """
    if pytesseract is None:
        return False, "❌ pytesseract / Pillow is not installed. Run: pip install pytesseract pillow"

    try:
        # 1. Extract text
        raw_text = extract_text_from_image(uploaded_file)
        if not raw_text.strip():
            return False, "⚠️ No text could be extracted from the image."

        # 2. Chunk text
        chunks = split_into_chunks(raw_text, max_words=CHUNK_SIZE)

        # 3. Save chunks
        stem = Path(uploaded_file.name).stem          # e.g. "scan_report"
        saved_paths = save_chunks(chunks, stem)

        return True, f"✅ OCR complete — saved {len(saved_paths)} chunk(s) for '{uploaded_file.name}'."

    except Exception as exc:
        return False, f"❌ OCR processing failed: {exc}"


# ── Internal helpers ──────────────────────────────────────────────────────────

def extract_text_from_image(uploaded_file) -> str:
    """Open the uploaded image and run Tesseract OCR on it."""
    image = Image.open(uploaded_file)
    text = pytesseract.image_to_string(image)
    return text


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