#!/usr/bin/env python3
"""Planned-only generator for the fitness dashboard data file.

Phase 1 scope is intentionally narrow:
- generate planned calendar rows from `scripts/fitness_calendar_rules.py`
- update summary/progress from calendar facts
- never parse training logs
- never create, delete, or modify `actual_label`

Do not parse `home-bodyweight-military-plan.md` directly. That Markdown file is
the human-readable source of intent; `fitness_calendar_rules.py` is the executable
rule config. Review/update both when the weekly structure changes.
"""
from __future__ import annotations

import argparse
import calendar
import copy
import difflib
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from fitness_calendar_rules import PLANNED_BLOCKS, planned_label, planned_state
except ModuleNotFoundError:  # pragma: no cover - allows import from repo root in tests
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from fitness_calendar_rules import PLANNED_BLOCKS, planned_label, planned_state

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "public" / "data.json"
CHECK_SCRIPT = ROOT / "scripts" / "check_calendar_rotation.py"
ANY_RE = re.compile(r"^([ABCZ])")


@dataclass(frozen=True)
class PlanResult:
    data: dict[str, Any]
    additions: int
    modifications: int
    actual_changes: int
    planned_counts: Counter[str]
    summary_updates: dict[str, Any]
    progress_updates: dict[str, Any]
    diff: str
    errors: list[str]


def parse_month(value: str) -> tuple[int, int]:
    try:
        year, month = map(int, value.split("-"))
        date(year, month, 1)
    except Exception as exc:  # noqa: BLE001
        raise argparse.ArgumentTypeError(f"invalid month {value!r}; expected YYYY-MM") from exc
    return year, month


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def month_key(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def iter_month_days(year: int, month: int):
    for d in range(1, calendar.monthrange(year, month)[1] + 1):
        yield date(year, month, d)


def generated_month_rows(year: int, month: int) -> list[dict[str, str]]:
    return [
        {"date": day.isoformat(), "state": planned_state(day), "planned_label": planned_label(day)}
        for day in iter_month_days(year, month)
    ]


def planned_counts(rows: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        if m := ANY_RE.match(row.get("planned_label", "")):
            counts[m.group(1)] += 1
    return counts


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def week_label(start: date) -> str:
    return f"{start.month}/{start.day}"


def is_training_row(row: dict[str, Any]) -> bool:
    return row.get("state") != "rest"


def is_done_row(row: dict[str, Any]) -> bool:
    return bool(row.get("actual_label")) and row.get("state") == "done"


def update_summary_and_progress(data: dict[str, Any], today: date) -> tuple[dict[str, Any], dict[str, Any]]:
    calendar_rows = data.get("calendar", [])
    current_start = week_start(today)
    current_end = current_start + timedelta(days=6)
    current_rows = [
        row for row in calendar_rows
        if current_start <= parse_date(row["date"]) <= current_end and is_training_row(row)
    ]
    planned_this_week = len(current_rows)
    completed_this_week = sum(1 for row in current_rows if is_done_row(row))

    summary = data.setdefault("summary", {})
    old_summary = {
        "plannedThisWeek": summary.get("plannedThisWeek"),
        "completedThisWeek": summary.get("completedThisWeek"),
        "currentStreak": summary.get("currentStreak"),
    }
    summary["plannedThisWeek"] = planned_this_week
    summary["completedThisWeek"] = completed_this_week
    # Planned-only Phase 1 has no reliable actual parser; keep this deterministic
    # and conservative from current calendar facts.
    summary["currentStreak"] = completed_this_week if completed_this_week else 0
    new_summary = {k: summary.get(k) for k in old_summary}

    progress = data.setdefault("progress", {})
    old_weekly = copy.deepcopy(progress.get("weeklyCompletion", []))
    current_label = week_label(current_start)
    current_bucket = {"week": current_label, "planned": planned_this_week, "done": completed_this_week}
    weekly = copy.deepcopy(old_weekly)
    for i, row in enumerate(weekly):
        if row.get("week") == current_label:
            weekly[i] = current_bucket
            break
    else:
        weekly.append(current_bucket)
    progress["weeklyCompletion"] = weekly

    # Preserve historical cardio minutes. Add a current-week zero bucket only when
    # the chart has no matching row; do not invent future actual minutes.
    old_cardio = copy.deepcopy(progress.get("cardioMinutes", []))
    cardio = copy.deepcopy(old_cardio)
    if not any(row.get("week") == current_label for row in cardio):
        cardio.append({"week": current_label, "minutes": 0})
    progress["cardioMinutes"] = cardio

    return new_summary, {
        "weeklyCompletion_before": old_weekly,
        "weeklyCompletion_after": weekly,
        "cardioMinutes_before": old_cardio,
        "cardioMinutes_after": cardio,
    }

def actual_signature(data: dict[str, Any]) -> dict[str, Any]:
    return {row["date"]: row.get("actual_label") for row in data.get("calendar", []) if "actual_label" in row}


def json_text(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def plan(data: dict[str, Any], target_month: str, today: date, allow_past_planned_update: bool) -> PlanResult:
    year, month = parse_month(target_month)
    before = copy.deepcopy(data)
    after = copy.deepcopy(data)
    before_actual = actual_signature(before)

    generated = generated_month_rows(year, month)
    counts = planned_counts(generated)
    errors: list[str] = []
    if counts.get("B", 0) == 0:
        errors.append(f"planned B count is zero for {target_month}")

    existing_by_date = {row["date"]: copy.deepcopy(row) for row in after.get("calendar", [])}
    additions = 0
    modifications = 0
    for gen in generated:
        existing = existing_by_date.get(gen["date"])
        if existing is None:
            existing_by_date[gen["date"]] = copy.deepcopy(gen)
            additions += 1
            continue
        proposed = copy.deepcopy(existing)
        proposed["planned_label"] = gen["planned_label"]
        # Only planned rows are generated. Do not convert actual done/rest rows.
        if "actual_label" not in proposed:
            proposed["state"] = gen["state"]
        if proposed != existing:
            modifications += 1
            existing_by_date[gen["date"]] = proposed

    target_is_past = date(year, month, 1).replace(day=calendar.monthrange(year, month)[1]) < today.replace(day=1)
    if target_is_past and (additions or modifications) and not allow_past_planned_update:
        errors.append(f"refusing to change past month {target_month} without --allow-past-planned-update")

    after["calendar"] = [existing_by_date[d] for d in sorted(existing_by_date)]
    summary_updates, progress_updates = update_summary_and_progress(after, today)
    after_actual = actual_signature(after)
    actual_changes = 0 if before_actual == after_actual else 1
    if actual_changes:
        errors.append("actual_label changes detected; aborting")

    diff = "".join(difflib.unified_diff(
        json_text(before).splitlines(keepends=True),
        json_text(after).splitlines(keepends=True),
        fromfile="before/public/data.json",
        tofile="after/public/data.json",
    ))
    return PlanResult(after, additions, modifications, actual_changes, counts, summary_updates, progress_updates, diff, errors)


def print_report(result: PlanResult, target_month: str, today: date, dry_run: bool) -> None:
    mode = "dry-run" if dry_run else "write"
    print(f"Fitness data generator {mode}")
    print(f"month={target_month} today={today.isoformat()}")
    print(f"calendar additions={result.additions} modifications={result.modifications} actual_changes={result.actual_changes}")
    print("planned_counts " + " ".join(f"{k}={result.planned_counts.get(k,0)}" for k in PLANNED_BLOCKS))
    print(
        "would update summary "
        + " ".join(f"{k}={v}" for k, v in result.summary_updates.items())
    )
    after_weekly = result.progress_updates.get("weeklyCompletion_after") or []
    print("would update weeklyCompletion " + ", ".join(f"{r['week']}:{r['done']}/{r['planned']}" for r in after_weekly))
    if result.errors:
        print("FAIL")
        for err in result.errors:
            print(f"- {err}")
    else:
        print("PASS gates")
    if result.diff:
        print("--- diff ---")
        print(result.diff, end="" if result.diff.endswith("\n") else "\n")
    else:
        print("--- diff ---")
        print("(no changes)")


def run_write_gates(data_path: Path, target_month: str) -> None:
    subprocess.run([sys.executable, "-m", "json.tool", str(data_path)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, str(CHECK_SCRIPT), "--data", str(data_path), "--month", target_month], check=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Planned-only fitness dashboard data generator")
    ap.add_argument("--data", default=str(DEFAULT_DATA), help="Path to public/data.json")
    ap.add_argument("--month", required=True, help="YYYY-MM month to generate")
    ap.add_argument("--today", default=date.today().isoformat(), help="YYYY-MM-DD for current-week summary; default today")
    ap.add_argument("--write", action="store_true", help="Write changes; default is dry-run")
    ap.add_argument("--allow-past-planned-update", action="store_true", help="Allow planned changes to months before today's month")
    ns = ap.parse_args(argv)

    data_path = Path(ns.data)
    target_month = ns.month
    parse_month(target_month)  # validation
    today = parse_date(ns.today)
    data = json.loads(data_path.read_text())
    result = plan(data, target_month, today, ns.allow_past_planned_update)
    print_report(result, target_month, today, dry_run=not ns.write)
    if result.errors:
        return 1
    if ns.write:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(data_path.parent), prefix=".data.", suffix=".json") as tmp:
            tmp.write(json_text(result.data))
            tmp_path = Path(tmp.name)
        try:
            run_write_gates(tmp_path, target_month)
            data_path.write_text(tmp_path.read_text())
            run_write_gates(data_path, target_month)
        finally:
            tmp_path.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
