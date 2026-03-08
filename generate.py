#!/usr/bin/env python3
"""Entry point for the Mar Thoma Church worship order generator.

Usage:
    python generate.py                          # interactive
    python generate.py --date 2026-03-15        # specific date
    python generate.py --config weekly.yaml     # from YAML file
    python generate.py --help                   # show all options
"""
from src.cli import main

if __name__ == "__main__":
    main()
