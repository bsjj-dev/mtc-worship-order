"""
Parse the Mar Thoma lectionary PDF into a structured JSON cache.

The PDF contains a table with columns:
  Date | Theme/Feast | 1st Lesson (OT) | Epistle | 2nd Lesson (Acts/NT) | Gospel | Evening

We use pdfplumber to extract the table rows. The parsed data is written to
data/lectionary/<year>.json as a dict keyed by ISO date string ("YYYY-MM-DD").
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "lectionary"


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(text.split())


def _parse_date(raw: str, year: int) -> str | None:
    """Try to parse a date string like 'January 5' or 'Jan 5' into 'YYYY-MM-DD'."""
    raw = _clean(raw)
    if not raw:
        return None
    # Try with year appended
    for fmt in ("%B %d %Y", "%b %d %Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            dt = datetime.strptime(f"{raw} {year}", fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Try formats that already contain the year
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    logger.warning("Could not parse date: %r", raw)
    return None


def parse_lectionary_pdf(pdf_path: Path, year: int) -> dict[str, dict[str, str]]:
    """Extract lectionary entries from *pdf_path* and return a dict keyed by date."""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber is required: pip install pdfplumber")

    entries: dict[str, dict[str, str]] = {}

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or len(row) < 4:
                        continue
                    # Skip header rows
                    first = _clean(row[0] or "").lower()
                    if any(h in first for h in ("date", "sunday", "week", "month")):
                        continue

                    date_str = _parse_date(_clean(row[0] or ""), year)
                    if not date_str:
                        continue

                    # Map columns defensively — PDFs vary slightly year to year
                    def _get(idx: int) -> str:
                        if idx < len(row):
                            return _clean(row[idx] or "")
                        return ""

                    entries[date_str] = {
                        "date": date_str,
                        "theme": _get(1),
                        "first_lesson": _get(2),
                        "epistle": _get(3),
                        "second_lesson": _get(4),
                        "gospel": _get(5),
                        "evening": _get(6) if len(row) > 6 else "",
                    }

    return entries


def save_lectionary_json(entries: dict[str, Any], year: int) -> Path:
    out_path = DATA_DIR / f"{year}.json"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    logger.info("Wrote %d entries to %s", len(entries), out_path)
    return out_path


def load_lectionary_json(year: int) -> dict[str, Any]:
    path = DATA_DIR / f"{year}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Lectionary JSON not found for {year} at {path}. "
            "Run: python data/fetch_lectionary.py"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)
