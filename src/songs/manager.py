"""
Song manager: fuzzy-search hymns.yaml by title, chunk lyrics into slides.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import yaml
from rapidfuzz import fuzz, process

from ..worship_order.models import Song

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "songs"
HYMNS_FILE = DATA_DIR / "hymns.yaml"

MAX_LINES_PER_SLIDE = 8

_hymns_cache: Optional[List[dict]] = None


def _load_hymns() -> List[dict]:
    global _hymns_cache
    if _hymns_cache is None:
        if not HYMNS_FILE.exists():
            _hymns_cache = []
        else:
            with open(HYMNS_FILE, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            _hymns_cache = data.get("hymns", [])
    return _hymns_cache


def _chunk_lyrics(raw_lyrics: str, max_lines: int = MAX_LINES_PER_SLIDE) -> List[str]:
    """
    Split a multi-line lyrics string into slide-sized chunks.
    Each chunk is a string of ≤ max_lines non-empty lines joined by newlines.
    Empty lines are treated as verse/section separators — preferred chunk break points.
    """
    lines = raw_lyrics.split("\n")

    chunks: List[str] = []
    current: List[str] = []

    for line in lines:
        if not line.strip():
            # Empty line = natural break
            if current:
                chunks.append("\n".join(current))
                current = []
        else:
            current.append(line)
            if len(current) >= max_lines:
                chunks.append("\n".join(current))
                current = []

    if current:
        chunks.append("\n".join(current))

    return chunks or [""]


def find_song(title: str, threshold: int = 70) -> Optional[Song]:
    """
    Fuzzy-search hymns.yaml for *title*.
    Returns a Song with chunked lyrics, or None if no match above *threshold*.
    """
    hymns = _load_hymns()
    if not hymns:
        return Song(title=title, lyrics=[])

    titles = [h.get("title", "") for h in hymns]
    result = process.extractOne(title, titles, scorer=fuzz.WRatio)

    if result is None or result[1] < threshold:
        logger.info("No hymn match for %r (best score: %s)", title, result)
        return Song(title=title, lyrics=[])

    matched_title, score, idx = result
    hymn = hymns[idx]
    logger.info("Matched %r → %r (score %d)", title, matched_title, score)

    raw_lyrics = hymn.get("lyrics", "")
    chunks = _chunk_lyrics(raw_lyrics)

    return Song(title=hymn.get("title", title), lyrics=chunks)


def get_song_or_placeholder(title: str) -> Song:
    """Return a matched Song, or a placeholder Song (empty lyrics) if not found."""
    if not title or not title.strip():
        return Song(title="", lyrics=[])
    song = find_song(title.strip())
    if song is None or not song.has_lyrics:
        return Song(title=title.strip(), lyrics=[])
    return song


def add_hymn(title: str, lyrics: str) -> None:
    """Add a new hymn to hymns.yaml (runtime addition)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if HYMNS_FILE.exists():
        with open(HYMNS_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}

    hymns = data.get("hymns", [])
    hymns.append({"title": title, "lyrics": lyrics})
    data["hymns"] = hymns

    with open(HYMNS_FILE, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    # Invalidate cache
    global _hymns_cache
    _hymns_cache = None
    logger.info("Added hymn %r to database.", title)
