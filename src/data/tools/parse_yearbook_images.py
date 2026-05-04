from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.yearbook_ocr import parse_yearbook_images


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse official NBS yearbook JPG tables into project CSV data.")
    parser.add_argument("--year", type=int, default=2023, help="Data year, e.g. 2023")
    parser.add_argument("--refresh-sources", action="store_true", help="Download yearbook images again before parsing")
    args = parser.parse_args()

    df = parse_yearbook_images(args.year, refresh_sources=args.refresh_sources)
    print(f"Parsed {df.shape[0]} provinces x {df.shape[1]} indicators for {args.year}.")
    print(df.head().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
