"""
input_files/csv_extractor.py

CSV pipeline for news articles:
  1. Read uploaded CSV (must have an 'article_link' column)
  2. Scrape full article content from each URL using BeautifulSoup
  3. Combine heading + content_summary + scraped content per article
  4. Incrementally chunk while processing (≤9500 words per chunk)
  5. Save chunks to extracted_data/<csv_stem>_part01.txt, _part02.txt, …
  6. Add "\n\n\n\n" after each article
"""

import time
from pathlib import Path
from typing import Tuple, List

try:
    import requests
    from bs4 import BeautifulSoup
    import pandas as pd
    from tqdm import tqdm
    _DEPS_OK = True
except ImportError as _e:
    _DEPS_OK = False
    _MISSING = str(_e)

CHUNK_SIZE = 9500
OUTPUT_DIR = Path("extracted_data")
DELAY = 1
HEADERS = {"User-Agent": "Mozilla/5.0"}
EXTRACT_DATA_LIMIT = 20


# ── Public API ────────────────────────────────────────────────────────────────

def process_csv_file(uploaded_file) -> Tuple[bool, str]:
    if not _DEPS_OK:
        return False, f"❌ Missing dependency: {_MISSING}. Run: pip install requests beautifulsoup4 pandas tqdm"

    try:
        # 1. Load CSV
        df, err = _load_csv(uploaded_file)
        if err:
            return False, err

        # 2. Limit rows
        df = df.iloc[:EXTRACT_DATA_LIMIT, :]

        # 3. Process + Chunk incrementally
        stem = Path(uploaded_file.name).stem
        saved_files = _process_and_chunk_articles(df, stem)

        return True, (
            f"✅ CSV processed — scraped {len(df)} articles, "
            f"saved {len(saved_files)} chunk(s)."
        )

    except Exception as exc:
        return False, f"❌ CSV processing failed: {exc}"


# ── CSV Loader ───────────────────────────────────────────────────────────────

def _load_csv(uploaded_file) -> Tuple[object, str]:
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        return None, f"❌ Could not read CSV: {e}"

    if "article_link" not in df.columns:
        cols = ", ".join(df.columns.tolist())
        return None, (
            f"❌ CSV must have an 'article_link' column. "
            f"Found columns: {cols}"
        )

    df = df.dropna(subset=["article_link"]).reset_index(drop=True)

    if df.empty:
        return None, "❌ No valid URLs found in 'article_link' column."

    return df, None


# ── Incremental Chunking Logic ───────────────────────────────────────────────

def _process_and_chunk_articles(df: "pd.DataFrame", stem: str) -> List[Path]:
    OUTPUT_DIR.mkdir(exist_ok=True)

    current_chunk_words = []
    current_word_count = 0

    chunk_index = 1
    saved_files = []

    tqdm.pandas(desc="Scraping articles")

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Processing articles"):
        url = row["article_link"]

        # Scrape article
        time.sleep(DELAY)
        content = _scrape_article(url)

        heading = str(row.get("heading", "")).strip()
        summary = str(row.get("content_summary", "")).strip()

        # Build article text
        article_parts = [p for p in [heading, summary, content] if p and p != "nan"]
        if not article_parts:
            continue

        article_text = "\n".join(article_parts) + "\n\n\n\n"
        article_words = article_text.split()
        article_word_count = len(article_words)

        # 🚨 Check if adding exceeds limit
        if current_word_count + article_word_count > CHUNK_SIZE:
            if current_chunk_words:
                path = OUTPUT_DIR / f"{stem}_part{chunk_index:02d}.txt"
                path.write_text(" ".join(current_chunk_words), encoding="utf-8")
                saved_files.append(path)

                chunk_index += 1
                current_chunk_words = []
                current_word_count = 0

        # Add article to current chunk
        current_chunk_words.extend(article_words)
        current_word_count += article_word_count

    # Save last chunk
    if current_chunk_words:
        path = OUTPUT_DIR / f"{stem}_part{chunk_index:02d}.txt"
        path.write_text(" ".join(current_chunk_words), encoding="utf-8")
        saved_files.append(path)

    return saved_files


# ── Scraping helpers ─────────────────────────────────────────────────────────

def _scrape_article(url: str) -> str:
    html = _fetch_html(url)
    if html:
        return _parse_article(html)
    return ""


def _fetch_html(url: str) -> str:
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return response.text
        return None
    except Exception:
        return None


def _parse_article(html: str) -> str:
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Try specific div
        content_div = soup.find("div", class_="_s30J clearfix")
        if content_div:
            return content_div.get_text(separator=" ", strip=True)

        # Fallback: article tag
        article_tag = soup.find("article")
        if article_tag:
            return article_tag.get_text(separator=" ", strip=True)

        # Fallback: paragraphs
        paragraphs = soup.find_all("p")
        if paragraphs:
            return " ".join(p.get_text(strip=True) for p in paragraphs)

        return ""
    except Exception:
        return ""