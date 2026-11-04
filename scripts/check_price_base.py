#!/usr/bin/env python
"""Compare optimisation.price_base.GDP_DEFLATOR with the live ONS series. Exit 1 on a difference.

    python scripts/check_price_base.py
"""
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from optimisation.price_base import GDP_DEFLATOR  # noqa: E402

URL = "https://www.ons.gov.uk/economy/grossdomesticproductgdp/timeseries/ybgb/qna/data"


def main() -> int:
    data = requests.get(URL, timeout=60, headers={"User-Agent": "Mozilla/5.0"}).json()
    live = {int(y["year"]): float(y["value"]) for y in data["years"]}
    print(f"ONS YBGB, release {data['description'].get('releaseDate', '')[:10]}")
    moved = {y: (v, live.get(y)) for y, v in GDP_DEFLATOR.items() if live.get(y) != v}
    for y, (held, now) in moved.items():
        print(f"  {y}: held {held}, ONS now {now}")
    print("moved" if moved else "held figures match")
    return 1 if moved else 0


if __name__ == "__main__":
    sys.exit(main())
