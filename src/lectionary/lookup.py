"""
High-level interface: look up lectionary readings for a given date.

Usage:
    from src.lectionary.lookup import get_readings
    entry = get_readings("2026-03-08")
    print(entry.gospel)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .parser import load_lectionary_json

logger = logging.getLogger(__name__)


@dataclass
class LectionaryEntry:
    date: str           # ISO "YYYY-MM-DD"
    theme: str = ""
    first_lesson: str = ""
    epistle: str = ""
    second_lesson: str = ""
    gospel: str = ""
    evening: str = ""

    @property
    def is_empty(self) -> bool:
        return not any([self.first_lesson, self.epistle, self.second_lesson, self.gospel])

    def display(self) -> str:
        lines = []
        if self.theme:
            lines.append(f"  Theme:          {self.theme}")
        if self.first_lesson:
            lines.append(f"  1st Lesson:     {self.first_lesson}")
        if self.epistle:
            lines.append(f"  Epistle:        {self.epistle}")
        if self.second_lesson:
            lines.append(f"  2nd Lesson:     {self.second_lesson}")
        if self.gospel:
            lines.append(f"  Gospel:         {self.gospel}")
        return "\n".join(lines)


def get_readings(date_str: str) -> LectionaryEntry:
    """Return a LectionaryEntry for *date_str* (ISO format).

    Loads from pre-parsed JSON lectionary files.
    """
    # Load from cached JSON files
    try:
        year = int(date_str[:4])
    except (ValueError, IndexError):
        year = datetime.today().year

    data = None
    for try_year in [year, year - 1, year + 1]:
        try:
            data = load_lectionary_json(try_year)
            if date_str in data:
                break
        except FileNotFoundError:
            continue
    
    if data is None:
        logger.warning("Lectionary data not found for %d – returning empty entry.", year)
        return LectionaryEntry(date=date_str)

    if date_str in data:
        row = data[date_str]
        return LectionaryEntry(
            date=date_str,
            theme=row.get("theme", ""),
            first_lesson=row.get("first_lesson", ""),
            epistle=row.get("epistle", ""),
            second_lesson=row.get("second_lesson", ""),
            gospel=row.get("gospel", ""),
        )

    # Fallback: find the nearest Sunday on or before the given date
    logger.info("Exact date %s not in lectionary; searching nearest Sunday.", date_str)
    target = datetime.strptime(date_str, "%Y-%m-%d").date()
    best_key: Optional[str] = None
    best_delta = 999

    for key in data:
        try:
            d = datetime.strptime(key, "%Y-%m-%d").date()
            delta = (target - d).days
            if 0 <= delta < best_delta:
                best_delta = delta
                best_key = key
        except ValueError:
            continue

    if best_key:
        row = data[best_key]
        entry = LectionaryEntry(
            date=best_key,
            theme=row.get("theme", ""),
            first_lesson=row.get("first_lesson", ""),
            epistle=row.get("epistle", ""),
            second_lesson=row.get("second_lesson", ""),
            gospel=row.get("gospel", ""),
            evening=row.get("evening", ""),
        )
        logger.info("Using lectionary entry for %s (nearest to %s)", best_key, date_str)
        return entry

    logger.warning("No lectionary entry found near %s.", date_str)
    return LectionaryEntry(date=date_str)


def parse_reference(ref: str) -> dict[str, str]:
    """Parse a reference like 'Luke 15:11-32' into component parts.

    Returns dict with keys: book, chapter, verse_start, verse_end, full
    """
    ref = ref.strip()
    # Pattern: "Book Name Chapter:VerseStart[-VerseEnd]"
    import re
    m = re.match(
        r"^([\w\s]+?)\s+(\d+):(\d+)(?:[–\-](\d+))?$",
        ref
    )
    if not m:
        return {"book": ref, "chapter": "", "verse_start": "", "verse_end": "", "full": ref}

    book = m.group(1).strip()
    chapter = m.group(2)
    verse_start = m.group(3)
    verse_end = m.group(4) or verse_start

    return {
        "book": book,
        "chapter": chapter,
        "verse_start": verse_start,
        "verse_end": verse_end,
        "full": ref,
    }
