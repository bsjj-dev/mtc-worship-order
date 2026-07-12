"""
Fetch lectionary readings from marthomana.org (North America Diocese).

This scrapes the live lectionary page which has data embedded as JavaScript.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Optional

import requests

logger = logging.getLogger(__name__)

LECTIONARY_URL = "https://marthomana.org/lectionary/"


def fetch_readings_for_date(date_str: str) -> Optional[dict[str, str]]:
    """Fetch lectionary readings for a specific date from marthomana.org.
    
    Args:
        date_str: ISO date string "YYYY-MM-DD"
        
    Returns:
        Dict with keys: date, theme, first_lesson, epistle, second_lesson, gospel
        Returns None if date not found or fetch fails.
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        logger.error("Invalid date format: %s", date_str)
        return None
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        response = requests.get(LECTIONARY_URL, headers=headers, timeout=15)
        response.raise_for_status()
        
        html = response.text
        
        # The lectionary data is embedded as JavaScript object literals
        # Pattern: '2026-03-08': { day: 'Sunday', theme: '...', first: '...', epistle: '...', gospel: '...' }
        pattern = rf"'{re.escape(date_str)}':\s*\{{([^}}]+)\}}"
        match = re.search(pattern, html)
        
        if not match:
            logger.warning("Date %s not found on marthomana.org", date_str)
            return None
        
        # Extract the JavaScript object content
        obj_content = match.group(1)
        
        # Parse the JavaScript object fields
        result = {
            "date": date_str,
            "theme": "",
            "first_lesson": "",
            "epistle": "",
            "second_lesson": "",
            "gospel": "",
        }
        
        # Extract theme
        theme_match = re.search(r"theme:\s*['\"]([^'\"]+)['\"]", obj_content)
        if theme_match:
            result["theme"] = theme_match.group(1).strip()
        
        # Extract first lesson (OT reading)
        first_match = re.search(r"first:\s*['\"]([^'\"]+)['\"]", obj_content)
        if first_match:
            # The 'first' field may contain multiple readings separated by semicolon
            first_text = first_match.group(1).strip()
            # Take the first reading before semicolon
            result["first_lesson"] = first_text.split(';')[0].strip()
        
        # Extract epistle
        epistle_match = re.search(r"epistle:\s*['\"]([^'\"]+)['\"]", obj_content)
        if epistle_match:
            # May contain multiple readings separated by semicolon
            epistle_text = epistle_match.group(1).strip()
            # Take the first reading as epistle
            result["epistle"] = epistle_text.split(';')[0].strip()
            # If there's a second reading, use it as second_lesson
            parts = epistle_text.split(';')
            if len(parts) > 1:
                result["second_lesson"] = parts[1].strip()
        
        # Extract gospel
        gospel_match = re.search(r"gospel:\s*['\"]([^'\"]+)['\"]", obj_content)
        if gospel_match:
            gospel_text = gospel_match.group(1).strip()
            # Take the first reading before semicolon
            result["gospel"] = gospel_text.split(';')[0].strip()
        
        logger.info("Fetched readings for %s from marthomana.org", date_str)
        return result
        
    except requests.RequestException as e:
        logger.error("Failed to fetch from marthomana.org: %s", e)
        return None
    except Exception as e:
        logger.error("Error parsing marthomana.org lectionary: %s", e)
        return None
