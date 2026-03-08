"""
Download and cache the Mar Thoma North America Diocese lectionary PDF.
The PDF is typically posted at marthomana.org each January.
"""
from __future__ import annotations

import os
import re
import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# Known PDF URLs keyed by year. Update each January when the new PDF is posted.
LECTIONARY_URLS: dict[int, str] = {
    2024: "https://marthomana.org/wp-content/uploads/2024/01/2024-Lectionary.pdf",
    2025: "https://marthomana.org/wp-content/uploads/2025/03/2025-Lectionary-for-the-Diocese-of-North-America-of-the-MTC.pdf",
}

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "lectionary"


def get_pdf_path(year: int) -> Path:
    return DATA_DIR / f"{year}_lectionary.pdf"


def download_lectionary_pdf(year: int, force: bool = False) -> Path:
    """Download the lectionary PDF for *year* and return the local path.

    Skips the download if the file already exists, unless *force* is True.
    Raises ValueError if no URL is known for *year*.
    """
    pdf_path = get_pdf_path(year)
    if pdf_path.exists() and not force:
        logger.info("Lectionary PDF already cached at %s", pdf_path)
        return pdf_path

    url = LECTIONARY_URLS.get(year)
    if not url:
        raise ValueError(
            f"No lectionary URL known for {year}. "
            "Add it to src/lectionary/fetcher.py LECTIONARY_URLS."
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading lectionary PDF from %s", url)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    pdf_path.write_bytes(response.content)
    logger.info("Saved lectionary PDF to %s", pdf_path)
    return pdf_path
