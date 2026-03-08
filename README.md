# Mar Thoma Church – Worship Order Generator

Generates a ready-to-project PowerPoint presentation for the weekly Sunday service of the **Malankara Mar Thoma Syrian Church**. Pulls the lectionary automatically, inserts congregation songs, and renders every liturgical section in the official MTC visual style (burgundy gradient, gold headings, white text).

Supports:
- **English Divine Worship** (non-communion Sunday)
- **English Holy Qurbana** (communion Sunday)

---

## Quick Start

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. (Optional) Add the MTC logo

Place the Mar Thoma Church cross logo as `assets/logo.png`.
It will appear in the top-right corner of every slide.
If the file is absent, slides are generated without it.

### 3. (Optional) Fetch the lectionary

The lectionary is read from a local JSON cache in `data/lectionary/`.
Download and parse the current year's PDF with:

```bash
python data/fetch_lectionary.py           # uses current year
python data/fetch_lectionary.py --year 2025
```

If the cache is absent, readings can be entered manually during generation.

### 4. Generate a presentation

**Interactive mode** (recommended for weekly use):
```bash
python generate.py
```

**From a YAML config file** (reproducible, good for version control):
```bash
python generate.py --config examples/sample_divine_worship.yaml
python generate.py --config examples/sample_holy_qurbana.yaml
```

**Specify a date, then answer prompts:**
```bash
python generate.py --date 2026-03-15
```

Output is saved to `output/<date>_<type>.pptx`.

---

## Service Structure

### English Divine Worship

| # | Section | Notes |
|---|---------|-------|
| 1 | Title slide | Date + service type |
| 2 | Pre-worship song | Optional |
| 3 | Call to Worship | Psalm 100 responsive |
| 4 | Kauma | Gloria/Adoration |
| 5 | Trisagion | Threefold "Holy art Thou" |
| 6 | Promeon | Prayer for grace |
| 7 | Sedra | Prayer of supplication |
| 8 | Etra | Incense prayer |
| 9 | First Lesson | OT reading (lectionary) |
| 10 | Song between lessons | User input |
| 11 | Second Lesson | NT/Acts reading (lectionary) |
| 12 | Epistle | (lectionary) |
| 13 | Holy Gospel | Congregation stands (lectionary) |
| 14 | Birthday & Anniversary | Prayers + song |
| 15 | Special Prayer | Optional |
| 16 | Hymn & Offertory | User input |
| 17 | Announcements | Divider slide |
| 18 | Sermon | Title, preacher, scripture |
| 19 | Confession | Responsive |
| 20 | Nicene Creed | |
| 21 | Intercessions | |
| 22 | Doxology | User input or standard |
| 23 | Benediction | |

### English Holy Qurbana

All of the above, plus after the Intercessions:

| # | Section |
|---|---------|
| 24 | Kiss of Peace |
| 25 | Sursum Corda |
| 26 | Eucharistic Prayer / Anaphora |
| 27 | Sanctification (Epiclesis) |
| 28 | Lord's Prayer |
| 29 | Fraction |
| 30 | Communion Invitation + Songs |
| 31 | Post-Communion Thanksgiving |

---

## Adding Songs

Songs are looked up by title from `data/songs/hymns.yaml`. If a song is not found, a **placeholder slide** is generated so you know to fill it in.

To add a song, edit `data/songs/hymns.yaml`:

```yaml
hymns:
  - title: "My Song Title"
    lyrics: |
      Verse 1 line 1
      Verse 1 line 2
      Verse 1 line 3

      Verse 2 line 1
      Verse 2 line 2

      Chorus line 1
      Chorus line 2
```

- Blank lines between stanzas create slide breaks.
- Sections longer than 8 lines are automatically split across slides.
- Titles are **fuzzy-matched**, so minor typos still find the right song.

---

## Weekly YAML Config

For repeatable generation, use a config file (see `examples/`):

```yaml
date: "2026-03-15"
service_type: divine_worship     # or: holy_qurbana
congregation_name: "Mar Thoma Church"

sermon:
  title: "The Good Shepherd"
  preacher: "Rev. John Mathew"
  scripture: "John 10:11-18"

songs:
  pre_worship: ""                 # leave blank to skip
  between_lessons: "Song Title"
  birthday_anniversary: "Happy Birthday"
  special_prayer:
    enabled: false
    topic: ""
    song: ""
  offertory: "Song Title"
  communion:                      # Holy Qurbana only
    - "Song Title 1"
    - "Song Title 2"
  doxology: "Praise God from Whom All Blessings Flow"

# Override auto-fetched lectionary if needed:
lectionary_overrides:
  first_lesson: "Isaiah 40:1-11"
  epistle: ""
  second_lesson: ""
  gospel: ""
```

---

## Lectionary

The generator fetches readings from a cached JSON file built from the **Mar Thoma North America Diocese** annual lectionary PDF (marthomana.org).

Update the cache at the start of each year:
```bash
python data/fetch_lectionary.py --year 2026
```

If the cache is missing or the date isn't found, you'll be prompted to enter readings manually during interactive mode.

---

## Visual Theme

| Element | Value |
|---------|-------|
| Background | Burgundy gradient `#6B0020` → `#1A0005` |
| Section headers | Gold `#D4AF37` |
| Body text | White `#FFFFFF` |
| Scripture references | Cream `#F5DEB3` |
| Priest lines (`P:`) | Gold |
| Congregation lines (`C:`) | White |
| Logo | `assets/logo.png` — top-right corner |
| Aspect ratio | 16:9 widescreen (13.33" × 7.5") |
| Body font size | 30–36pt |
| Heading font size | 48pt |

All values are configurable in `config/theme.yaml`.

---

## Project Structure

```
mtc-worship-order/
├── generate.py               # Entry point
├── requirements.txt
├── config/
│   ├── service.yaml          # All liturgical text
│   └── theme.yaml            # Visual design settings
├── data/
│   ├── fetch_lectionary.py   # Download + parse lectionary PDF
│   ├── lectionary/           # Cached JSON lectionary files
│   └── songs/
│       └── hymns.yaml        # Your song/hymn database
├── assets/
│   └── logo.png              # MTC logo (add manually)
├── src/
│   ├── cli.py                # Click-based CLI
│   ├── lectionary/           # Fetch, parse, lookup
│   ├── worship_order/        # Service section models + ordering
│   ├── slides/               # PPTX generation
│   └── songs/                # Song manager
├── examples/
│   ├── sample_divine_worship.yaml
│   └── sample_holy_qurbana.yaml
└── output/                   # Generated .pptx files (git-ignored)
```

---

## Future Plans

- Malayalam Holy Qurbana and Divine Worship service types
- Wedding and special occasion orders
- Web UI for weekly input
- Auto-schedule (generate each Friday for the upcoming Sunday)
