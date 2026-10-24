#!/usr/bin/env python3
"""Fetch the optional character art for this checkout; never executes downloads."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from memminning.artwork import fetch_artwork

if __name__ == '__main__':
    try:
        paths = fetch_artwork(Path(__file__).resolve().parents[1] / 'assets')
        print(f'Verified {len(paths)} local character images. See assets/README.md for credits.')
    except Exception as exc:
        sys.exit(f'Artwork download failed: {exc}')
