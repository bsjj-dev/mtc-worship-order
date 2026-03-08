"""
Core data models for the worship order generator.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ServiceType(Enum):
    DIVINE_WORSHIP = "divine_worship"
    HOLY_QURBANA = "holy_qurbana"


class SlideType(Enum):
    TITLE = "title"
    SECTION_DIVIDER = "section_divider"
    LITURGY = "liturgy"
    SCRIPTURE = "scripture"
    SONG = "song"
    INFO = "info"
    BLANK = "blank"


@dataclass
class Song:
    title: str
    lyrics: List[str] = field(default_factory=list)
    # Each string in lyrics is one slide's worth of text (already chunked)
    # If empty, a placeholder slide is shown instead.

    @property
    def has_lyrics(self) -> bool:
        return bool(self.lyrics)


@dataclass
class SpecialPrayer:
    enabled: bool = False
    topic: str = ""
    song: Optional[Song] = None


@dataclass
class SermonInfo:
    title: str = ""
    preacher: str = ""
    scripture: str = ""


@dataclass
class SongSelections:
    """All user-selected songs for a service."""
    pre_worship: Optional[Song] = None
    between_lessons: Optional[Song] = None
    birthday_anniversary: Optional[Song] = None
    special_prayer: SpecialPrayer = field(default_factory=SpecialPrayer)
    offertory: Optional[Song] = None
    communion: List[Song] = field(default_factory=list)
    doxology: Optional[Song] = None


@dataclass
class ServiceConfig:
    """Complete configuration for a single service."""
    date: str                          # ISO "YYYY-MM-DD"
    service_type: ServiceType
    congregation_name: str = "Mar Thoma Church"
    sermon: SermonInfo = field(default_factory=SermonInfo)
    songs: SongSelections = field(default_factory=SongSelections)

    # Lectionary readings (populated from lectionary lookup)
    lectionary_theme: str = ""
    first_lesson: str = ""
    epistle: str = ""
    second_lesson: str = ""
    gospel: str = ""

    @property
    def date_display(self) -> str:
        """Human-readable date, e.g. 'March 8, 2026'."""
        from datetime import datetime
        try:
            return datetime.strptime(self.date, "%Y-%m-%d").strftime("%B %-d, %Y")
        except (ValueError, AttributeError):
            return self.date

    @property
    def service_type_display(self) -> str:
        if self.service_type == ServiceType.DIVINE_WORSHIP:
            return "English Divine Worship"
        return "English Holy Qurbana"


@dataclass
class SlideContent:
    """Represents a single slide to be rendered."""
    slide_type: SlideType
    title: str = ""
    subtitle: str = ""
    lines: List[str] = field(default_factory=list)
    # For section dividers, just title is used.
    # For liturgy slides, lines contain "P: ..." / "C: ..." / plain text.
    # For song slides, lines contain lyric text.
    # For scripture slides, lines contain verse text; title = reference.
    scripture_ref: str = ""   # e.g. "Luke 15:11-32"
    is_responsive: bool = False  # True if lines have P:/C: prefixes
