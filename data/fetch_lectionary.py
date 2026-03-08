#!/usr/bin/env python3
"""
Fetch and parse the Mar Thoma North America Diocese lectionary PDF into JSON.

Run this once per year (or whenever the new PDF is published):
    python data/fetch_lectionary.py           # current year
    python data/fetch_lectionary.py --year 2025
    python data/fetch_lectionary.py --year 2025 --force  # re-download even if cached
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.lectionary.fetcher import download_lectionary_pdf
from src.lectionary.parser import parse_lectionary_pdf, save_lectionary_json

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Fetch and parse the MTC lectionary PDF.")
    parser.add_argument("--year", type=int, default=datetime.today().year)
    parser.add_argument("--force", action="store_true", help="Re-download even if cached.")
    args = parser.parse_args()

    print(f"Fetching {args.year} lectionary PDF...")
    try:
        pdf_path = download_lectionary_pdf(args.year, force=args.force)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Download failed: {e}")
        print("You can manually place the PDF at:")
        print(f"  data/lectionary/{args.year}_lectionary.pdf")
        print("Then re-run this script.")
        sys.exit(1)

    print(f"Parsing {pdf_path.name}...")
    entries = parse_lectionary_pdf(pdf_path, args.year)

    if not entries:
        print("Warning: no entries parsed. The PDF table format may have changed.")
        print("Check src/lectionary/parser.py and adjust column mapping if needed.")
        sys.exit(1)

    out = save_lectionary_json(entries, args.year)
    print(f"Done — {len(entries)} entries written to {out}")
    print()
    print("Sample entries:")
    for key in sorted(entries)[:3]:
        e = entries[key]
        print(f"  {key}: {e.get('theme', '')} | Gospel: {e.get('gospel', '')}")


if __name__ == "__main__":
    main()
