from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.nbs_yearbook import download_yearbook_tables, find_yearbook_tables


def main() -> int:
    parser = argparse.ArgumentParser(description="Download official NBS yearbook table images.")
    parser.add_argument("--year", type=int, default=2023, help="Data year, e.g. 2023")
    args = parser.parse_args()

    links = find_yearbook_tables(args.year)
    if not links:
        print(f"No yearbook tables found for {args.year}.")
        return 1

    print("Found tables:")
    for indicator, url in links.items():
        print(f"  {indicator}: {url}")

    downloaded = download_yearbook_tables(args.year)
    print("\nDownloaded:")
    for indicator, path in downloaded.items():
        print(f"  {indicator}: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
