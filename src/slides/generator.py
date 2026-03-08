"""
Main slide generation orchestrator.

Takes a ServiceConfig → builds SlideContent list → renders PPTX.
"""
from __future__ import annotations

import logging
import re
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import yaml
from pptx import Presentation
from pptx.util import Inches

from ..lectionary.lookup import parse_reference
from ..worship_order.models import (
    ServiceConfig,
    ServiceType,
    SlideContent,
    SlideType,
)
from .slide_builder import (
    add_blank_slide,
    add_info_slide,
    add_liturgy_slide,
    add_scripture_slide,
    add_section_divider,
    add_song_slide,
    add_title_slide,
)
from .theme import Theme, get_theme

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "output"

BIBLE_API_URL = "https://bible-api.com/{ref}?translation=kjv"
MAX_LINES_PER_SLIDE = 10
MAX_SONG_LINES_PER_SLIDE = 8


# ─────────────────────────────────────────────────────────────────────────────
# Lectionary / Bible text helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_scripture_text(reference: str) -> List[str]:
    """Fetch verse text from bible-api.com. Returns list of line strings."""
    if not reference or reference.startswith("["):
        return []
    try:
        url = BIBLE_API_URL.format(ref=requests.utils.quote(reference))
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        verses = data.get("verses", [])
        if verses:
            lines = []
            for v in verses:
                verse_num = v.get("verse", "")
                text = v.get("text", "").strip()
                lines.append(f"{verse_num}. {text}")
            return lines
        # Fallback: plain text
        text = data.get("text", "").strip()
        return text.splitlines() if text else []
    except Exception as e:
        logger.warning("Could not fetch scripture %r: %s", reference, e)
        return []


def _chunk_lines(lines: List[str], max_per_slide: int) -> List[List[str]]:
    """Split a list of lines into chunks of at most max_per_slide lines."""
    chunks = []
    for i in range(0, max(len(lines), 1), max_per_slide):
        chunk = lines[i : i + max_per_slide]
        if chunk:
            chunks.append(chunk)
    return chunks or [[]]


# ─────────────────────────────────────────────────────────────────────────────
# Service YAML loader
# ─────────────────────────────────────────────────────────────────────────────

_service_yaml_cache: Optional[Dict[str, Any]] = None


def _get_service_yaml() -> Dict[str, Any]:
    global _service_yaml_cache
    if _service_yaml_cache is None:
        with open(CONFIG_DIR / "service.yaml", encoding="utf-8") as f:
            _service_yaml_cache = yaml.safe_load(f)
    return _service_yaml_cache


def _resolve_yaml_section(key: str, config: ServiceConfig) -> List[SlideContent]:
    """
    Load a section from service.yaml and return SlideContent objects.
    Template placeholders like {book}, {chapter}, {verse_start} are NOT applied here —
    those are for the intro slides rendered dynamically in the generator.
    """
    data = _get_service_yaml()
    section = data.get(key)
    if not section:
        logger.warning("Section key %r not found in service.yaml", key)
        return []

    title = section.get("title", key.replace("_", " ").title())
    subtitle = section.get("subtitle", "")
    result: List[SlideContent] = []

    # Add a section divider first
    result.append(SlideContent(
        slide_type=SlideType.SECTION_DIVIDER,
        title=title,
        subtitle=subtitle,
    ))

    for slide_data in section.get("slides", []):
        raw_lines = slide_data.get("lines", [])
        # Check if any line has P:/C: markers
        is_responsive = any(
            ln.startswith("P:") or ln.startswith("C:") for ln in raw_lines
        )
        result.append(SlideContent(
            slide_type=SlideType.LITURGY,
            title=title,
            lines=raw_lines,
            is_responsive=is_responsive,
        ))

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Main generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_presentation(config: ServiceConfig, output_path: Optional[Path] = None) -> Path:
    """
    Generate the full worship order PPTX for *config*.
    Returns the path to the saved file.
    """
    from ..worship_order.divine_worship import build_service_slides as dw_build
    from ..worship_order.holy_qurbana import build_service_slides as qb_build

    theme = get_theme()

    # 1. Build the ordered list of SlideContent objects
    if config.service_type == ServiceType.HOLY_QURBANA:
        raw_slides = qb_build(config)
    else:
        raw_slides = dw_build(config)

    # 2. Create a new Presentation
    prs = Presentation()
    prs.slide_width = theme.slide_width
    prs.slide_height = theme.slide_height

    # 3. Render each SlideContent
    for sc in raw_slides:
        _render_slide(prs, sc, config, theme)

    # 4. Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        stype = "divine_worship" if config.service_type == ServiceType.DIVINE_WORSHIP else "holy_qurbana"
        output_path = OUTPUT_DIR / f"{config.date}_{stype}.pptx"

    prs.save(str(output_path))
    logger.info("Saved presentation to %s", output_path)
    return output_path


def _render_slide(
    prs: Presentation,
    sc: SlideContent,
    config: ServiceConfig,
    theme: Theme,
) -> None:
    """Render a single SlideContent to the presentation."""

    if sc.slide_type == SlideType.TITLE:
        add_title_slide(
            prs,
            congregation_name=sc.title,
            service_type=sc.subtitle,
            date_str=sc.lines[0] if sc.lines else "",
            theme=theme,
        )
        return

    if sc.slide_type == SlideType.SECTION_DIVIDER:
        add_section_divider(prs, sc.title, sc.subtitle, theme=theme)
        return

    if sc.slide_type == SlideType.BLANK:
        add_blank_slide(prs, theme=theme)
        return

    if sc.slide_type == SlideType.INFO:
        add_info_slide(prs, sc.title, sc.lines, theme=theme)
        return

    if sc.slide_type == SlideType.SONG:
        # Lines may already be chunked (each item in sc.lines is one slide)
        # or may be a flat list. Chunk if needed.
        flat_lines = sc.lines
        chunks = _chunk_lines(flat_lines, MAX_SONG_LINES_PER_SLIDE)
        for chunk in chunks:
            add_song_slide(prs, sc.title, chunk, theme=theme)
        return

    if sc.slide_type == SlideType.SCRIPTURE:
        if sc.lines == ["__FETCH__"]:
            ref = sc.scripture_ref
            verse_lines = _fetch_scripture_text(ref) if ref else []
            if not verse_lines:
                verse_lines = [f"[{ref}]", "(scripture text unavailable)"]
        else:
            verse_lines = sc.lines

        chunks = _chunk_lines(verse_lines, MAX_LINES_PER_SLIDE)
        for chunk in chunks:
            add_scripture_slide(prs, sc.scripture_ref, chunk, theme=theme)
        return

    if sc.slide_type == SlideType.LITURGY:
        # Check for __YAML__ sentinel — resolve from service.yaml
        if sc.lines == ["__YAML__"]:
            resolved = _resolve_yaml_section(sc.title, config)
            for resolved_sc in resolved:
                _render_slide(prs, resolved_sc, config, theme)
            return

        # Plain liturgy slide — render directly
        chunks = _chunk_lines(sc.lines, MAX_LINES_PER_SLIDE)
        for chunk in chunks:
            add_liturgy_slide(prs, sc.title, chunk, theme=theme)
        return
