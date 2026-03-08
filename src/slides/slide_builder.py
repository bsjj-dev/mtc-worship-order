"""
Low-level slide construction functions.

Each function receives a python-pptx Presentation, adds one slide, and returns it.
All positioning uses the Theme object for consistent styling.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt
from pptx.dml.color import RGBColor
import lxml.etree as etree

from .theme import Theme, get_theme


# ─────────────────────────────────────────────────────────────────────────────
# Background helpers
# ─────────────────────────────────────────────────────────────────────────────

def _apply_gradient_background(slide, color1: RGBColor, color2: RGBColor) -> None:
    """Apply a left-to-right linear gradient background to *slide*."""
    fill = slide.background.fill
    fill.gradient()
    fill.gradient_angle = 135  # diagonal top-left → bottom-right

    stops = fill.gradient_stops
    stops[0].position = 0.0
    stops[0].color.rgb = color1
    stops[1].position = 1.0
    stops[1].color.rgb = color2


def _apply_solid_background(slide, color: RGBColor) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def _apply_background(slide, theme: Theme) -> None:
    if theme.bg_type == "gradient":
        _apply_gradient_background(slide, theme.bg_color1, theme.bg_color2)
    else:
        _apply_solid_background(slide, theme.bg_color1)


# ─────────────────────────────────────────────────────────────────────────────
# Text box helpers
# ─────────────────────────────────────────────────────────────────────────────

def _add_textbox(
    slide,
    text: str,
    left: Emu,
    top: Emu,
    width: Emu,
    height: Emu,
    font_name: str,
    font_size: Pt,
    color: RGBColor,
    bold: bool = False,
    italic: bool = False,
    align: PP_ALIGN = PP_ALIGN.LEFT,
    word_wrap: bool = True,
):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = word_wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = font_name
    run.font.size = font_size
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.italic = italic
    return txBox


def _add_multiline_textbox(
    slide,
    lines: List[str],
    left: Emu,
    top: Emu,
    width: Emu,
    height: Emu,
    font_name: str,
    font_size: Pt,
    default_color: RGBColor,
    align: PP_ALIGN = PP_ALIGN.LEFT,
    word_wrap: bool = True,
    theme: Optional[Theme] = None,
):
    """Add a textbox with multiple lines, supporting P:/C: color coding."""
    t = theme or get_theme()
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = word_wrap

    first = True
    for line in lines:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.alignment = align

        # Blank line — just add empty paragraph
        if not line.strip():
            p.add_run()
            continue

        # Determine color based on P: / C: prefix
        color = default_color
        display_text = line
        if theme:
            if line.startswith("P:"):
                color = t.priest_color
                display_text = line  # keep the label
            elif line.startswith("C:"):
                color = t.congregation_color
                display_text = line

        run = p.add_run()
        run.text = display_text
        run.font.name = font_name
        run.font.size = font_size
        run.font.color.rgb = color

    return txBox


# ─────────────────────────────────────────────────────────────────────────────
# Logo helper
# ─────────────────────────────────────────────────────────────────────────────

def _add_logo(slide, theme: Theme) -> None:
    logo_path = theme.logo_path
    if not logo_path.exists():
        return  # silently skip if logo not present
    left = theme.slide_width - theme.logo_right_margin - theme.logo_width
    top = theme.logo_top
    slide.shapes.add_picture(str(logo_path), left, top, width=theme.logo_width)


# ─────────────────────────────────────────────────────────────────────────────
# Gold separator line
# ─────────────────────────────────────────────────────────────────────────────

def _add_gold_line(slide, theme: Theme, top_offset: Emu) -> None:
    """Draw a thin horizontal gold line across the content area."""
    from pptx.util import Emu
    line = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.LINE is not directly importable; use connector
        theme.margin_left,
        top_offset,
        theme.content_width,
        Emu(0),
    )
    line.line.color.rgb = theme.gold
    line.line.width = Pt(1.5)


# ─────────────────────────────────────────────────────────────────────────────
# Public slide-building functions
# ─────────────────────────────────────────────────────────────────────────────

def _blank_slide(prs: Presentation, theme: Theme):
    """Add a blank slide with background applied."""
    blank_layout = prs.slide_layouts[6]  # completely blank
    slide = prs.slides.add_slide(blank_layout)
    _apply_background(slide, theme)
    _add_logo(slide, theme)
    return slide


def add_title_slide(
    prs: Presentation,
    congregation_name: str,
    service_type: str,
    date_str: str,
    theme: Optional[Theme] = None,
) -> None:
    t = theme or get_theme()
    slide = _blank_slide(prs, t)

    # Church name — large, centered, top third
    _add_textbox(
        slide,
        congregation_name,
        left=t.margin_left,
        top=Inches(1.2),
        width=t.content_width,
        height=Inches(1.2),
        font_name=t.title_font,
        font_size=t.pt("title_slide_church"),
        color=t.cream,
        align=PP_ALIGN.CENTER,
    )

    # Service type — large gold
    _add_textbox(
        slide,
        service_type,
        left=t.margin_left,
        top=Inches(2.6),
        width=t.content_width,
        height=Inches(1.4),
        font_name=t.title_font,
        font_size=t.pt("title_slide_service"),
        color=t.gold,
        bold=True,
        align=PP_ALIGN.CENTER,
    )

    # Date — smaller, cream, below
    _add_textbox(
        slide,
        date_str,
        left=t.margin_left,
        top=Inches(4.2),
        width=t.content_width,
        height=Inches(0.8),
        font_name=t.title_font,
        font_size=t.pt("title_slide_date"),
        color=t.cream,
        align=PP_ALIGN.CENTER,
    )


def add_section_divider(
    prs: Presentation,
    title: str,
    subtitle: str = "",
    theme: Optional[Theme] = None,
) -> None:
    t = theme or get_theme()
    slide = _blank_slide(prs, t)

    title_top = Inches(2.8) if not subtitle else Inches(2.4)

    _add_textbox(
        slide,
        title,
        left=t.margin_left,
        top=title_top,
        width=t.content_width,
        height=Inches(1.2),
        font_name=t.title_font,
        font_size=t.pt("section_divider"),
        color=t.gold,
        bold=True,
        align=PP_ALIGN.CENTER,
    )

    if subtitle:
        _add_textbox(
            slide,
            subtitle,
            left=t.margin_left,
            top=Inches(3.9),
            width=t.content_width,
            height=Inches(0.7),
            font_name=t.body_font,
            font_size=t.pt("liturgy_body"),
            color=t.cream,
            italic=True,
            align=PP_ALIGN.CENTER,
        )


def add_liturgy_slide(
    prs: Presentation,
    section_title: str,
    lines: List[str],
    theme: Optional[Theme] = None,
) -> None:
    """Render one screen-worth of liturgical text (with P:/C: color coding)."""
    t = theme or get_theme()
    slide = _blank_slide(prs, t)

    # Small section label at top
    _add_textbox(
        slide,
        section_title,
        left=t.margin_left,
        top=Inches(0.25),
        width=t.content_width,
        height=Inches(0.5),
        font_name=t.title_font,
        font_size=Pt(18),
        color=t.gold,
        italic=True,
    )

    _add_multiline_textbox(
        slide,
        lines,
        left=t.margin_left,
        top=Inches(0.85),
        width=t.content_width,
        height=Inches(5.9),
        font_name=t.body_font,
        font_size=t.pt("liturgy_body"),
        default_color=t.white,
        align=PP_ALIGN.LEFT,
        theme=t,
    )


def add_song_slide(
    prs: Presentation,
    song_title: str,
    lines: List[str],
    theme: Optional[Theme] = None,
) -> None:
    t = theme or get_theme()
    slide = _blank_slide(prs, t)

    # Song title — small gold at top
    _add_textbox(
        slide,
        song_title,
        left=t.margin_left,
        top=Inches(0.2),
        width=t.content_width,
        height=Inches(0.5),
        font_name=t.title_font,
        font_size=Pt(20),
        color=t.gold,
        italic=True,
    )

    _add_multiline_textbox(
        slide,
        lines,
        left=t.margin_left,
        top=Inches(0.85),
        width=t.content_width,
        height=Inches(6.0),
        font_name=t.body_font,
        font_size=t.pt("song_body"),
        default_color=t.white,
        align=PP_ALIGN.CENTER,
        theme=t,
    )


def add_scripture_slide(
    prs: Presentation,
    reference: str,
    verses: List[str],
    theme: Optional[Theme] = None,
) -> None:
    """One slide per screen-worth of scripture text."""
    t = theme or get_theme()
    slide = _blank_slide(prs, t)

    # Reference label
    _add_textbox(
        slide,
        reference,
        left=t.margin_left,
        top=Inches(0.2),
        width=t.content_width,
        height=Inches(0.5),
        font_name=t.scripture_font,
        font_size=t.pt("scripture_ref"),
        color=t.gold,
        bold=True,
    )

    _add_multiline_textbox(
        slide,
        verses,
        left=t.margin_left,
        top=Inches(0.85),
        width=t.content_width,
        height=Inches(6.0),
        font_name=t.scripture_font,
        font_size=t.pt("scripture_body"),
        default_color=t.white,
        align=PP_ALIGN.LEFT,
        theme=t,
    )


def add_info_slide(
    prs: Presentation,
    heading: str,
    lines: List[str],
    theme: Optional[Theme] = None,
) -> None:
    t = theme or get_theme()
    slide = _blank_slide(prs, t)

    _add_textbox(
        slide,
        heading,
        left=t.margin_left,
        top=Inches(0.6),
        width=t.content_width,
        height=Inches(1.0),
        font_name=t.title_font,
        font_size=t.pt("info_heading"),
        color=t.gold,
        bold=True,
        align=PP_ALIGN.CENTER,
    )

    _add_multiline_textbox(
        slide,
        lines,
        left=t.margin_left,
        top=Inches(1.8),
        width=t.content_width,
        height=Inches(5.0),
        font_name=t.body_font,
        font_size=t.pt("info_body"),
        default_color=t.white,
        align=PP_ALIGN.CENTER,
        theme=t,
    )


def add_blank_slide(prs: Presentation, theme: Optional[Theme] = None) -> None:
    t = theme or get_theme()
    _blank_slide(prs, t)
