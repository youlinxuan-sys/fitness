#!/usr/bin/env python3
"""Validate fitness calendar planned A/B rotation for a month.

The live calendar stores both planned_label and actual_label. This check validates
planned strength labels. Use --from-date to skip already locked/current-week
exceptions while still verifying future full weeks.
"""
from __future__ import annotations

import argparse
import calendar
import json
import re
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data.json"
STRENGTH_RE = re.compile(r"^([AB])([123])")
ANY_RE = re.compile(r"^([ABCZ])")


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def expected_block(day: date) -> str:
    first = day.replace(day=1)
    offset = first.weekday()  # Monday=0, aligned with the dashboard JS formula.
    week_of_month = (day.day + offset - 1) // 7 + 1
    return "A" if week_of_month % 2 == 1 else "B"


def expected_suffix(day: date) -> str | None:
    return {0: "1", 2: "2", 4: "3"}.get(day.weekday())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DATA), help="calendar JSON path")
    ap.add_argument("--month", required=True, help="YYYY-MM month to validate")
    ap.add_argument("--from-date", help="YYYY-MM-DD; validate planned strength days on/after this date")
    ns = ap.parse_args()

    data = json.loads(Path(ns.data).read_text())
    year, month = map(int, ns.month.split("-"))
    from_date = parse_date(ns.from_date) if ns.from_date else date(year, month, 1)

    rows = []
    planned_counts: Counter[str] = Counter()
    actual_counts: Counter[str] = Counter()
    for item in data.get("calendar", []):
        d = parse_date(item["date"])
        if d.year != year or d.month != month:
            continue
        planned = item.get("planned_label") or item.get("label") or ""
        actual = item.get("actual_label") or ""
        if m := ANY_RE.match(planned):
            planned_counts[m.group(1)] += 1
        if m := ANY_RE.match(actual):
            actual_counts[m.group(1)] += 1
        rows.append((d, planned, actual, item.get("state", "planned")))

    errors: list[str] = []
    if planned_counts.get("B", 0) == 0:
        errors.append(f"planned B count is zero for {ns.month}")

    checked = 0
    skipped = 0
    last_day = calendar.monthrange(year, month)[1]
    for d, planned, actual, state in rows:
        if d < from_date:
            skipped += 1
            continue
        suffix = expected_suffix(d)
        if suffix is None:
            continue
        match = STRENGTH_RE.match(planned)
        if not match:
            errors.append(f"{d}: expected strength label, got planned_label={planned!r}")
            continue
        block, label_suffix = match.groups()
        exp_block = expected_block(d)
        if block != exp_block or label_suffix != suffix:
            errors.append(f"{d}: expected {exp_block}{suffix}, got planned_label={planned!r}")
        checked += 1

    print(f"calendar_rotation_check month={ns.month} from_date={from_date.isoformat()}")
    print("planned_counts " + " ".join(f"{k}={planned_counts.get(k,0)}" for k in "ABCZ"))
    print("actual_counts " + " ".join(f"{k}={actual_counts.get(k,0)}" for k in "ABCZ"))
    print(f"checked_future_strength_days={checked} skipped_before_from_date={skipped} month_last_day={last_day}")
    if errors:
        print("FAIL")
        for e in errors:
            print(f"- {e}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
