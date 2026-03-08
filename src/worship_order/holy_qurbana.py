"""
Defines the ordered sequence of sections for the English Holy Qurbana service.

Extends the Divine Worship order by inserting Eucharistic sections after
the intercessions and before the Doxology/Benediction.
"""
from __future__ import annotations

from typing import List

from .models import ServiceConfig, SlideContent, SlideType
from .divine_worship import (
    build_service_slides as _dw_build,
    _add_section_divider,
    _add_yaml_section,
    _add_song,
    _add_doxology,
)


def build_service_slides(config: ServiceConfig) -> List[SlideContent]:
    """Build the full slide list for a Holy Qurbana service."""
    # Start with the Divine Worship base, but strip the final Doxology+Benediction
    # (we re-add them after the Eucharistic sections).
    dw_slides = _dw_build(config)

    # Find and remove trailing doxology + benediction slides so we can insert
    # the Eucharistic sections between them.
    tail_keys = {"doxology_default", "benediction"}
    cut_index = len(dw_slides)
    for i in range(len(dw_slides) - 1, -1, -1):
        s = dw_slides[i]
        if s.slide_type == SlideType.LITURGY and s.title in tail_keys:
            cut_index = i
        elif s.slide_type == SlideType.SECTION_DIVIDER and s.title == "Doxology":
            cut_index = i
        elif s.slide_type == SlideType.SONG and s.title == (
            config.songs.doxology.title if config.songs.doxology else ""
        ):
            cut_index = i
        else:
            break

    base_slides = dw_slides[:cut_index]
    tail_slides = dw_slides[cut_index:]

    # Eucharistic sections
    eucharist: List[SlideContent] = []
    _add_yaml_section(eucharist, "kiss_of_peace")
    _add_yaml_section(eucharist, "sursum_corda")
    _add_yaml_section(eucharist, "eucharistic_prayer")
    _add_yaml_section(eucharist, "epiclesis")
    _add_yaml_section(eucharist, "lords_prayer")
    _add_yaml_section(eucharist, "fraction")
    _add_yaml_section(eucharist, "communion_invitation")

    # Communion songs
    if config.songs.communion:
        _add_section_divider(eucharist, "Communion Songs")
        for song in config.songs.communion:
            _add_song(eucharist, song)

    _add_yaml_section(eucharist, "post_communion")

    return base_slides + eucharist + tail_slides
