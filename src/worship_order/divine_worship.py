"""
Defines the ordered sequence of sections for the English Divine Worship service.

Each section is a string key that maps to a section in config/service.yaml,
OR a special sentinel for dynamic content (songs, scripture, sermon, etc.).

The build_service_slides() function is the main entry point — it receives a
ServiceConfig and returns a list of SlideContent objects.
"""
from __future__ import annotations

from typing import List

from .models import ServiceConfig, ServiceType, SlideContent, SlideType


def build_service_slides(config: ServiceConfig) -> List[SlideContent]:
    """Build the full ordered list of SlideContent for a Divine Worship service."""
    slides: List[SlideContent] = []

    _add_title(slides, config)

    if config.songs.pre_worship:
        _add_section_divider(slides, "Before Worship")
        _add_song(slides, config.songs.pre_worship)

    _add_yaml_section(slides, "call_to_worship")
    _add_yaml_section(slides, "kauma")
    _add_yaml_section(slides, "trisagion")
    _add_yaml_section(slides, "promeon")
    _add_yaml_section(slides, "sedra")
    _add_yaml_section(slides, "etra")

    _add_scripture_reading(slides, "First Lesson", config.first_lesson)

    if config.songs.between_lessons:
        _add_section_divider(slides, "Hymn")
        _add_song(slides, config.songs.between_lessons)

    _add_scripture_reading(slides, "Second Lesson", config.second_lesson)
    _add_scripture_reading(slides, "The Epistle", config.epistle)
    _add_scripture_reading(slides, "The Holy Gospel", config.gospel, stand=True)

    _add_yaml_section(slides, "birthday_anniversary")
    if config.songs.birthday_anniversary:
        _add_song(slides, config.songs.birthday_anniversary)

    if config.songs.special_prayer.enabled:
        topic = config.songs.special_prayer.topic or "Special Prayer"
        _add_section_divider(slides, f"Special Prayer: {topic}")
        if config.songs.special_prayer.song:
            _add_song(slides, config.songs.special_prayer.song)

    _add_yaml_section(slides, "offertory")
    if config.songs.offertory:
        _add_song(slides, config.songs.offertory)

    _add_announcements(slides)
    _add_sermon(slides, config)
    _add_yaml_section(slides, "confession")
    _add_yaml_section(slides, "nicene_creed")
    _add_yaml_section(slides, "intercessions")

    _add_doxology(slides, config)
    _add_yaml_section(slides, "benediction")

    return slides


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _add_title(slides: List[SlideContent], config: ServiceConfig) -> None:
    slides.append(SlideContent(
        slide_type=SlideType.TITLE,
        title=config.congregation_name,
        subtitle=config.service_type_display,
        lines=[config.date_display],
    ))


def _add_section_divider(slides: List[SlideContent], title: str, subtitle: str = "") -> None:
    slides.append(SlideContent(
        slide_type=SlideType.SECTION_DIVIDER,
        title=title,
        subtitle=subtitle,
    ))


def _add_yaml_section(slides: List[SlideContent], section_key: str) -> None:
    """Append a placeholder that the generator will resolve against service.yaml."""
    slides.append(SlideContent(
        slide_type=SlideType.LITURGY,
        title=section_key,   # generator resolves this key
        lines=["__YAML__"],  # sentinel: generator will replace with yaml content
    ))


def _add_song(slides: List[SlideContent], song) -> None:
    if not song:
        return
    if song.has_lyrics:
        for chunk in song.lyrics:
            lines = chunk.split("\n") if isinstance(chunk, str) else chunk
            slides.append(SlideContent(
                slide_type=SlideType.SONG,
                title=song.title,
                lines=lines,
            ))
    else:
        # Placeholder
        slides.append(SlideContent(
            slide_type=SlideType.SONG,
            title=song.title,
            lines=[f"[{song.title}]", "(lyrics not found in database)"],
        ))


def _add_scripture_reading(
    slides: List[SlideContent],
    label: str,
    reference: str,
    stand: bool = False,
) -> None:
    subtitle = "Please rise" if stand else ""
    if not reference:
        slides.append(SlideContent(
            slide_type=SlideType.SECTION_DIVIDER,
            title=label,
            subtitle="(no reading assigned)",
        ))
        return

    # Section divider announcing the reading
    slides.append(SlideContent(
        slide_type=SlideType.SECTION_DIVIDER,
        title=label,
        subtitle=reference + (" — Please rise" if stand else ""),
    ))

    # The actual scripture text (fetched at render time by generator)
    slides.append(SlideContent(
        slide_type=SlideType.SCRIPTURE,
        title=label,
        scripture_ref=reference,
        lines=["__FETCH__"],  # sentinel: generator will fetch & fill
    ))


def _add_sermon(slides: List[SlideContent], config: ServiceConfig) -> None:
    _add_section_divider(slides, "The Sermon")
    info = config.sermon
    lines = []
    if info.title:
        lines.append(info.title)
    if info.preacher:
        lines.append(f"— {info.preacher}")
    if info.scripture:
        lines.append(f"\n{info.scripture}")
    slides.append(SlideContent(
        slide_type=SlideType.INFO,
        title="Sermon",
        lines=lines,
    ))


def _add_announcements(slides: List[SlideContent]) -> None:
    slides.append(SlideContent(
        slide_type=SlideType.SECTION_DIVIDER,
        title="Announcements",
    ))


def _add_doxology(slides: List[SlideContent], config: ServiceConfig) -> None:
    if config.songs.doxology and config.songs.doxology.has_lyrics:
        _add_section_divider(slides, "Doxology")
        _add_song(slides, config.songs.doxology)
    else:
        _add_yaml_section(slides, "doxology_default")
