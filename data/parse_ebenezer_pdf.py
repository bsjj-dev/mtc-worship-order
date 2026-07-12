"""
Parse the Ebenezer Mar Thoma Church 2026 Lectionary PDF.
Only extracts Sunday entries with correct column mapping.
"""
import json
import re
from pathlib import Path
from datetime import datetime

import pdfplumber

def parse_lectionary_pdf(pdf_path: str, year: int = 2026) -> dict:
    """Parse the Ebenezer lectionary PDF and extract Sunday entries."""
    
    entries = {}
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if not text:
                continue
            
            lines = text.split('\n')
            
            for i, line in enumerate(lines):
                # Look for lines that start with a number followed by "Sunday"
                # Format: "4 Sunday Mission outside Kerala"
                match = re.match(r'^(\d{1,2})\s+Sunday\s+(.+)', line)
                if not match:
                    continue
                
                day = int(match.group(1))
                theme = match.group(2).strip()
                
                # Determine the month from context (look backwards for MONTH header)
                month_name = None
                for j in range(i-1, max(0, i-20), -1):
                    month_match = re.match(r'^([A-Z]+)\s+\d{4}', lines[j])
                    if month_match:
                        month_name = month_match.group(1)
                        break
                
                if not month_name:
                    continue
                
                # Convert month name to number
                try:
                    month_num = datetime.strptime(month_name, '%B').month
                except ValueError:
                    continue
                
                # Create date string
                date_str = f"{year}-{month_num:02d}-{day:02d}"
                
                # Extract readings from the next few lines
                # The structure is:
                # Line i: "4 Sunday Theme"
                # Line i+1: "1st Lesson" "Epistle" (sometimes with references)
                # Line i+2: "2nd Lesson" "Gospel"
                
                first_lesson = ""
                second_lesson = ""
                epistle = ""
                gospel = ""
                
                # Look at next 3 lines for scripture references
                for offset in range(1, 4):
                    if i + offset >= len(lines):
                        break
                    
                    next_line = lines[i + offset].strip()
                    
                    # Extract scripture references (e.g., "Genesis 12: 1-7", "1 John 4: 7-21")
                    # Pattern: Book name (possibly with number) followed by chapter:verse
                    refs = re.findall(r'(?:[1-3]\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\.?\s+\d+:\s*\d+(?:\s*-\s*\d+)?', next_line)
                    
                    if len(refs) >= 2:
                        if not first_lesson:
                            # First line with 2+ refs: 1st lesson and epistle
                            first_lesson = refs[0].strip()
                            epistle = refs[1].strip()
                        elif not second_lesson:
                            # Second line with 2+ refs: 2nd lesson and gospel
                            second_lesson = refs[0].strip()
                            gospel = refs[1].strip()
                            break  # We have all we need
                
                # Store the entry
                if first_lesson and gospel:  # At minimum we need these
                    # Clean up references - remove extra spaces around colons
                    def clean_ref(ref):
                        return re.sub(r'\s*:\s*', ':', ref).strip()
                    
                    entries[date_str] = {
                        "date": date_str,
                        "theme": theme,
                        "first_lesson": clean_ref(first_lesson),
                        "epistle": clean_ref(epistle),
                        "second_lesson": clean_ref(second_lesson),
                        "gospel": clean_ref(gospel),
                        "evening": ""
                    }
                    print(f"Parsed {date_str}: {theme[:50]}")
    
    return entries


if __name__ == "__main__":
    import sys
    
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/Lectionary-2026.pdf"
    year = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
    
    print(f"Parsing {pdf_path} for year {year}...")
    entries = parse_lectionary_pdf(pdf_path, year)
    
    print(f"\nExtracted {len(entries)} Sunday entries")
    
    # Save to JSON
    output_dir = Path(__file__).parent / "lectionary"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"{year}.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    
    print(f"Saved to {output_path}")
    
    # Show a sample entry
    if entries:
        sample_date = sorted(entries.keys())[0]
        print(f"\nSample entry ({sample_date}):")
        print(json.dumps(entries[sample_date], indent=2))
