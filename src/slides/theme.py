"""
Load theme settings from config/theme.yaml and expose typed helpers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


def _hex_to_rgb(hex_str: str) -> RGBColor:
    h = hex_str.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return RGBColor(r, g, b)


class Theme:
    """Typed wrapper around theme.yaml."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._c = config

    # ── Slide dimensions ──────────────────────────────────────────────────────

    @property
    def slide_width(self) -> Inches:
        return Inches(self._c["slide"]["width_inches"])

    @property
    def slide_height(self) -> Inches:
        return Inches(self._c["slide"]["height_inches"])

    # ── Colors ────────────────────────────────────────────────────────────────

    @property
    def bg_color1(self) -> RGBColor:
        return _hex_to_rgb(self._c["background"]["color1"])

    @property
    def bg_color2(self) -> RGBColor:
        return _hex_to_rgb(self._c["background"]["color2"])

    @property
    def bg_type(self) -> str:
        return self._c["background"].get("type", "solid")

    def color(self, name: str) -> RGBColor:
        return _hex_to_rgb(self._c["colors"][name])

    @property
    def white(self) -> RGBColor:
        return self.color("white")

    @property
    def gold(self) -> RGBColor:
        return self.color("gold")

    @property
    def cream(self) -> RGBColor:
        return self.color("cream")

    @property
    def priest_color(self) -> RGBColor:
        return self.color("priest")

    @property
    def congregation_color(self) -> RGBColor:
        return self.color("congregation")

    # ── Fonts ─────────────────────────────────────────────────────────────────

    @property
    def title_font(self) -> str:
        return self._c["fonts"]["title"]

    @property
    def body_font(self) -> str:
        return self._c["fonts"]["body"]

    @property
    def scripture_font(self) -> str:
        return self._c["fonts"]["scripture"]

    # ── Sizes (returned as Pt) ────────────────────────────────────────────────

    def pt(self, name: str) -> Pt:
        return Pt(self._c["sizes"][name])

    # ── Logo ──────────────────────────────────────────────────────────────────

    @property
    def logo_path(self) -> Path:
        root = Path(__file__).resolve().parent.parent.parent
        return root / self._c["logo"]["path"]

    @property
    def logo_width(self) -> Inches:
        return Inches(self._c["logo"]["width_inches"])

    @property
    def logo_top(self) -> Inches:
        return Inches(self._c["logo"]["top_inches"])

    @property
    def logo_right_margin(self) -> Inches:
        return Inches(self._c["logo"]["right_margin_inches"])

    # ── Content margins ───────────────────────────────────────────────────────

    @property
    def margin_left(self) -> Inches:
        return Inches(self._c["margins"]["left_inches"])

    @property
    def margin_right(self) -> Inches:
        return Inches(self._c["margins"]["right_inches"])

    @property
    def margin_top(self) -> Inches:
        return Inches(self._c["margins"]["top_inches"])

    @property
    def margin_bottom(self) -> Inches:
        return Inches(self._c["margins"]["bottom_inches"])

    @property
    def content_width(self) -> Inches:
        return Inches(
            self._c["slide"]["width_inches"]
            - self._c["margins"]["left_inches"]
            - self._c["margins"]["right_inches"]
        )

    @property
    def content_height(self) -> Inches:
        return Inches(
            self._c["slide"]["height_inches"]
            - self._c["margins"]["top_inches"]
            - self._c["margins"]["bottom_inches"]
        )


_theme_instance: Theme | None = None


def get_theme() -> Theme:
    global _theme_instance
    if _theme_instance is None:
        path = CONFIG_DIR / "theme.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        _theme_instance = Theme(data)
    return _theme_instance
