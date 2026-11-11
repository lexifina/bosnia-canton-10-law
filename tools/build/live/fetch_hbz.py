"""Fetch the canton's gazette PDFs (see canton_fetch.py in scripts/bosnia-tuzla-canton-law/live)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'bosnia-tuzla-canton-law' / 'live'))
import canton_fetch  # noqa: E402

if __name__ == '__main__':
    canton_fetch.main("hbz")
