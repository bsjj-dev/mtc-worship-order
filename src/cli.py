"""
Interactive CLI for the Mar Thoma Church worship order generator.

Usage:
    python generate.py                        # interactive prompts
    python generate.py --config weekly.yaml   # load from YAML config
    python generate.py --date 2026-03-15      # specify date, still prompts
"""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import click
import yaml

from .lectionary.lookup import LectionaryEntry, get_readings
from .slides.generator import generate_presentation
from .songs.manager import get_song_or_placeholder
from .worship_order.models import (
    SermonInfo,
    ServiceConfig,
    ServiceType,
    Song,
    SongSelections,
    SpecialPrayer,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _prompt_song(prompt: str, default: str = "", required: bool = False) -> Optional[Song]:
    """Prompt for a song title and return a Song (with looked-up lyrics)."""
    suffix = f" [{default}]" if default else " (press Enter to skip)"
    value = click.prompt(f"  {prompt}{suffix}", default=default or "", show_default=False)
    value = value.strip()
    if not value:
        return None
    song = get_song_or_placeholder(value)
    if not song.has_lyrics:
        click.echo(f"    ⚠  '{value}' not found in hymn database — placeholder slide will be used.")
        click.echo("       To add lyrics: edit data/songs/hymns.yaml")
    return song


def _apply_lectionary(config: ServiceConfig, entry: LectionaryEntry) -> None:
    config.lectionary_theme = entry.theme
    config.first_lesson = entry.first_lesson
    config.epistle = entry.epistle
    config.second_lesson = entry.second_lesson
    config.gospel = entry.gospel


# ─────────────────────────────────────────────────────────────────────────────
# YAML config loader
# ─────────────────────────────────────────────────────────────────────────────

def _load_from_yaml(path: Path) -> ServiceConfig:
    """Build a ServiceConfig from a weekly YAML config file."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    date_str = str(raw.get("date", date.today().isoformat()))
    stype_raw = raw.get("service_type", "divine_worship").lower()
    stype = ServiceType.HOLY_QURBANA if "qurbana" in stype_raw else ServiceType.DIVINE_WORSHIP

    sermon_raw = raw.get("sermon", {})
    sermon = SermonInfo(
        title=sermon_raw.get("title", ""),
        preacher=sermon_raw.get("preacher", ""),
        scripture=sermon_raw.get("scripture", ""),
    )

    songs_raw = raw.get("songs", {})

    def _song(key: str, default: str = "") -> Optional[Song]:
        title = songs_raw.get(key, default)
        return get_song_or_placeholder(title) if title else None

    sp_raw = songs_raw.get("special_prayer", {})
    special_prayer = SpecialPrayer(
        enabled=bool(sp_raw.get("enabled", False)),
        topic=sp_raw.get("topic", ""),
        song=get_song_or_placeholder(sp_raw.get("song", "")) if sp_raw.get("song") else None,
    )

    communion_raw = songs_raw.get("communion", [])
    if isinstance(communion_raw, str):
        communion_raw = [communion_raw]
    communion_songs = [get_song_or_placeholder(t) for t in communion_raw if t]

    songs = SongSelections(
        pre_worship=_song("pre_worship"),
        between_lessons=_song("between_lessons"),
        birthday_anniversary=_song("birthday_anniversary"),
        special_prayer=special_prayer,
        offertory=_song("offertory"),
        communion=communion_songs,
        doxology=_song("doxology"),
    )

    config = ServiceConfig(
        date=date_str,
        service_type=stype,
        congregation_name=raw.get("congregation_name", "Mar Thoma Church"),
        sermon=sermon,
        songs=songs,
    )

    # Fetch lectionary, allow overrides from YAML
    entry = get_readings(date_str)
    _apply_lectionary(config, entry)

    overrides = raw.get("lectionary_overrides", {})
    if overrides.get("first_lesson"):
        config.first_lesson = overrides["first_lesson"]
    if overrides.get("epistle"):
        config.epistle = overrides["epistle"]
    if overrides.get("second_lesson"):
        config.second_lesson = overrides["second_lesson"]
    if overrides.get("gospel"):
        config.gospel = overrides["gospel"]

    return config


# ─────────────────────────────────────────────────────────────────────────────
# Interactive prompts
# ─────────────────────────────────────────────────────────────────────────────

def _interactive(date_str: str) -> ServiceConfig:
    click.echo()
    click.echo("═" * 52)
    click.echo("  Mar Thoma Church – Worship Order Generator")
    click.echo("═" * 52)

    # Service type
    click.echo()
    click.echo("Service type:")
    click.echo("  1. English Divine Worship")
    click.echo("  2. English Holy Qurbana")
    stype_choice = click.prompt("  Choice", default="1", show_default=False)
    stype = ServiceType.HOLY_QURBANA if stype_choice.strip() == "2" else ServiceType.DIVINE_WORSHIP

    congregation = click.prompt("\nCongregation name", default="Mar Thoma Church")

    # Lectionary
    click.echo(f"\nFetching lectionary for {date_str}...")
    entry = get_readings(date_str)
    if entry.is_empty:
        click.echo("  ⚠  No lectionary data found. You can enter readings manually below.")
    else:
        click.echo(entry.display())

    click.echo("\nPress Enter to accept lectionary readings, or type to override:")
    first_lesson = click.prompt("  1st Lesson", default=entry.first_lesson or "")
    second_lesson = click.prompt("  2nd Lesson", default=entry.second_lesson or "")
    epistle = click.prompt("  Epistle", default=entry.epistle or "")
    gospel = click.prompt("  Gospel", default=entry.gospel or "")

    # Songs
    click.echo("\n── Song Selections ──────────────────────────────")
    pre_worship = _prompt_song("Before worship song (optional)")
    between = _prompt_song("Song between lessons")
    bday = _prompt_song("Birthday & Anniversary song", default="Happy Birthday")
    offertory = _prompt_song("Offertory hymn")

    # Special prayer
    click.echo()
    has_special = click.confirm("  Special Prayer this week?", default=False)
    special_prayer = SpecialPrayer(enabled=False)
    if has_special:
        topic = click.prompt("  Special Prayer topic")
        sp_song = _prompt_song("  Special Prayer song (optional)")
        special_prayer = SpecialPrayer(enabled=True, topic=topic, song=sp_song)

    # Communion songs (only if Qurbana)
    communion_songs = []
    if stype == ServiceType.HOLY_QURBANA:
        click.echo()
        click.echo("  Communion songs (press Enter with empty title when done):")
        while True:
            cs = _prompt_song(f"  Communion song {len(communion_songs)+1} (or Enter to finish)")
            if cs is None:
                break
            communion_songs.append(cs)

    doxology = _prompt_song("Doxology", default="Praise God from Whom All Blessings Flow")

    # Sermon
    click.echo("\n── Sermon Details ───────────────────────────────")
    sermon_title = click.prompt("  Sermon title", default="")
    preacher = click.prompt("  Preacher name", default="")
    sermon_scripture = click.prompt("  Sermon scripture", default=gospel)

    config = ServiceConfig(
        date=date_str,
        service_type=stype,
        congregation_name=congregation,
        sermon=SermonInfo(
            title=sermon_title,
            preacher=preacher,
            scripture=sermon_scripture,
        ),
        songs=SongSelections(
            pre_worship=pre_worship,
            between_lessons=between,
            birthday_anniversary=bday,
            special_prayer=special_prayer,
            offertory=offertory,
            communion=communion_songs,
            doxology=doxology,
        ),
        lectionary_theme=entry.theme,
        first_lesson=first_lesson,
        epistle=epistle,
        second_lesson=second_lesson,
        gospel=gospel,
    )
    return config


# ─────────────────────────────────────────────────────────────────────────────
# Click entry point
# ─────────────────────────────────────────────────────────────────────────────

@click.command()
@click.option(
    "--date", "date_str",
    default=None,
    help="Service date in YYYY-MM-DD format (default: today).",
)
@click.option(
    "--config", "config_path",
    default=None,
    type=click.Path(exists=True),
    help="Path to a weekly YAML config file (skips interactive prompts).",
)
@click.option(
    "--output", "output_path",
    default=None,
    type=click.Path(),
    help="Output .pptx file path (default: output/<date>_<type>.pptx).",
)
def main(date_str: Optional[str], config_path: Optional[str], output_path: Optional[str]):
    """Generate a weekly worship order PowerPoint for the Mar Thoma Church."""

    # Resolve date
    if date_str is None:
        date_str = date.today().isoformat()
    else:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            click.echo(f"Error: date must be YYYY-MM-DD, got: {date_str}", err=True)
            sys.exit(1)

    # Build config
    if config_path:
        click.echo(f"Loading config from {config_path}...")
        service_config = _load_from_yaml(Path(config_path))
    else:
        service_config = _interactive(date_str)

    # Generate
    click.echo("\nGenerating presentation...")
    out = generate_presentation(
        service_config,
        output_path=Path(output_path) if output_path else None,
    )
    click.echo(f"\n✓ Saved: {out}")
    click.echo("  Open in PowerPoint or LibreOffice Impress to review.")
