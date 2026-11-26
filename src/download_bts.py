"""Download monthly BTS On-Time Performance archives.

Usage:
    python src/download_bts.py --year 2024 --months 1 2 3

Raw files are intentionally gitignored. The URL pattern is the official BTS
PREZIP endpoint and may occasionally be slow.
"""

from __future__ import annotations

import argparse
import pathlib
import urllib.request


URL = (
    "https://transtats.bts.gov/PREZIP/"
    "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"
)


def download(year: int, month: int, output_dir: pathlib.Path) -> pathlib.Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"bts_{year}_{month:02d}.zip"
    if destination.exists() and destination.stat().st_size > 1_000_000:
        print(f"skip existing: {destination}")
        return destination
    url = URL.format(year=year, month=month)
    print(f"download: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=180) as response, destination.open("wb") as out:
        while chunk := response.read(1024 * 1024):
            out.write(chunk)
    print(f"saved: {destination} ({destination.stat().st_size:,} bytes)")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--months", type=int, nargs="+", default=list(range(1, 13)))
    parser.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path("data/raw"))
    args = parser.parse_args()
    for month in args.months:
        if month not in range(1, 13):
            raise ValueError(f"invalid month: {month}")
        download(args.year, month, args.output_dir)


if __name__ == "__main__":
    main()

