"""
Flask web application for the Mar Thoma Church worship order generator.

Run locally:
    python web/app.py

Or with gunicorn (production):
    gunicorn -w 2 -b 0.0.0.0:8000 'web.app:create_app()'
"""
from __future__ import annotations

import logging
import os
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

# ── Make sure the repo root is on the path ──────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from flask import Flask, jsonify, render_template, request, send_file

from src.lectionary.lookup import get_readings
from src.slides.generator import generate_presentation
from src.songs.manager import get_song_or_placeholder
from src.worship_order.models import (
    SermonInfo,
    ServiceConfig,
    ServiceType,
    Song,
    SongSelections,
    SpecialPrayer,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# App factory
# ─────────────────────────────────────────────────────────────────────────────

def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # 4 MB request limit

    # ── Routes ────────────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        today = date.today().isoformat()
        return render_template("index.html", today=today)

    @app.route("/api/lectionary")
    def lectionary_api():
        date_str = request.args.get("date", "").strip()
        if not date_str:
            return jsonify({"error": "date parameter required"}), 400
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "date must be YYYY-MM-DD"}), 400

        entry = get_readings(date_str)
        return jsonify({
            "found": not entry.is_empty,
            "matched_date": entry.date,
            "theme": entry.theme,
            "first_lesson": entry.first_lesson,
            "epistle": entry.epistle,
            "second_lesson": entry.second_lesson,
            "gospel": entry.gospel,
        })

    @app.route("/api/generate", methods=["POST"])
    def generate_api():
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        try:
            config = _build_config(data)
        except (KeyError, ValueError) as exc:
            return jsonify({"error": f"Invalid request: {exc}"}), 400

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                stype = "divine_worship" if config.service_type == ServiceType.DIVINE_WORSHIP else "holy_qurbana"
                filename = f"{config.date}_{stype}.pptx"
                out_path = Path(tmpdir) / filename
                generate_presentation(config, out_path)

                return send_file(
                    str(out_path),
                    as_attachment=True,
                    download_name=filename,
                    mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                )
        except Exception as exc:
            logger.exception("Generation failed")
            return jsonify({"error": f"Generation failed: {exc}"}), 500

    @app.route("/api/songs")
    def songs_api():
        """Return a list of hymn titles from the local database (for autocomplete)."""
        import yaml
        hymns_path = ROOT / "data" / "songs" / "hymns.yaml"
        try:
            with open(hymns_path, encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            titles = [h["title"] for h in (raw.get("hymns") or []) if h.get("title")]
        except Exception:
            titles = []
        return jsonify({"titles": titles})

    return app


# ─────────────────────────────────────────────────────────────────────────────
# Config builder
# ─────────────────────────────────────────────────────────────────────────────

def _song(title: str | None) -> Song | None:
    if not title or not title.strip():
        return None
    return get_song_or_placeholder(title.strip())


def _build_config(data: dict) -> ServiceConfig:
    # Service type
    stype_raw = data.get("service_type", "divine_worship")
    stype = ServiceType.HOLY_QURBANA if stype_raw == "holy_qurbana" else ServiceType.DIVINE_WORSHIP

    # Songs
    songs_data = data.get("songs", {})

    sp_data = songs_data.get("special_prayer", {})
    special_prayer = SpecialPrayer(
        enabled=bool(sp_data.get("enabled", False)),
        topic=sp_data.get("topic", ""),
        song=_song(sp_data.get("song", "")),
    )

    communion_titles = songs_data.get("communion", [])
    if isinstance(communion_titles, str):
        communion_titles = [communion_titles]
    communion_songs = [s for t in communion_titles if (s := _song(t))]

    songs = SongSelections(
        pre_worship=_song(songs_data.get("pre_worship")),
        between_lessons=_song(songs_data.get("between_lessons")),
        birthday_anniversary=_song(songs_data.get("birthday_anniversary")),
        special_prayer=special_prayer,
        offertory=_song(songs_data.get("offertory")),
        communion=communion_songs,
        doxology=_song(songs_data.get("doxology")),
    )

    sermon_data = data.get("sermon", {})
    sermon = SermonInfo(
        title=sermon_data.get("title", ""),
        preacher=sermon_data.get("preacher", ""),
        scripture=sermon_data.get("scripture", ""),
    )

    config = ServiceConfig(
        date=data.get("date", date.today().isoformat()),
        service_type=stype,
        congregation_name=data.get("congregation_name", "Mar Thoma Church"),
        sermon=sermon,
        songs=songs,
        lectionary_theme=data.get("lectionary_theme", ""),
        first_lesson=data.get("first_lesson", ""),
        epistle=data.get("epistle", ""),
        second_lesson=data.get("second_lesson", ""),
        gospel=data.get("gospel", ""),
    )
    return config


# ─────────────────────────────────────────────────────────────────────────────
# Dev server
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  Mar Thoma Worship Generator running at http://localhost:{port}/\n")
    app.run(host="0.0.0.0", port=port, debug=True)
