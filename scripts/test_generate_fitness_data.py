#!/usr/bin/env python3
"""Fixture tests for the planned-only fitness data generator."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import generate_fitness_data as gen  # noqa: E402


def load_live_data() -> dict:
    return json.loads((ROOT / "public" / "data.json").read_text())


def assert_counts() -> None:
    expected = {
        "2026-06": {"A": 7, "B": 6, "C": 9, "Z": 4},
        "2026-07": {"A": 8, "B": 6, "C": 9, "Z": 4},
        "2026-08": {"A": 6, "B": 7, "C": 8, "Z": 5},
    }
    for month, counts in expected.items():
        year, mon = gen.parse_month(month)
        rows = gen.generated_month_rows(year, mon)
        actual = gen.planned_counts(rows)
        got = {k: actual.get(k, 0) for k in "ABCZ"}
        assert got == counts, f"{month}: expected {counts}, got {got}"
    print("fixture_counts PASS", expected)


def assert_actual_immutable() -> None:
    data = load_live_data()
    before = gen.actual_signature(data)
    result = gen.plan(copy.deepcopy(data), "2026-07", gen.parse_date("2026-07-07"), allow_past_planned_update=False)
    after = gen.actual_signature(result.data)
    assert before == after, "actual signature changed"
    assert result.actual_changes == 0, result.actual_changes
    print(f"actual_immutable PASS actual_entries={len(before)}")


def assert_july_dry_run_matches_live() -> None:
    data = load_live_data()
    result = gen.plan(copy.deepcopy(data), "2026-07", gen.parse_date("2026-07-07"), allow_past_planned_update=False)
    assert result.additions == 0, result.additions
    assert result.modifications == 0, result.modifications
    assert result.actual_changes == 0, result.actual_changes
    assert result.errors == [], result.errors
    # Re-running July should be idempotent with the manual July data already committed.
    assert result.diff == "", "2026-07 dry-run differs from committed data"
    print("july_regression PASS dry-run matches committed July calendar")


def assert_rotation_checks() -> None:
    # Use generated fixtures so the rotation gate validates the generator rules
    # for each requested month independent of historical hand-edited June data.
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "data.json"
        rows = []
        for month in ("2026-06", "2026-07", "2026-08"):
            year, mon = gen.parse_month(month)
            rows.extend(gen.generated_month_rows(year, mon))
        path.write_text(gen.json_text({"calendar": rows}))
        for month in ("2026-06", "2026-07", "2026-08"):
            cp = subprocess.run(
                [sys.executable, str(SCRIPTS / "check_calendar_rotation.py"), "--data", str(path), "--month", month],
                check=True,
                text=True,
                capture_output=True,
            )
            print(f"rotation_check {month} PASS")
            print(cp.stdout.strip())


def assert_write_mode_tempfile() -> None:
    data = load_live_data()
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "data.json"
        path.write_text(gen.json_text(data))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = gen.main(["--data", str(path), "--month", "2026-08", "--today", "2026-07-07", "--write"])
        out = buf.getvalue()
        assert code == 0
        written = json.loads(path.read_text())
        august = [row for row in written["calendar"] if row["date"].startswith("2026-08-")]
        assert len(august) == 31
        assert not any("actual_label" in row for row in august)
        assert "PASS gates" in out
    print("write_mode_tempfile PASS month=2026-08 rows=31 actual_labels=0")


def assert_main_dry_run_output() -> None:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = gen.main(["--month", "2026-08", "--today", "2026-07-07"])
    out = buf.getvalue()
    assert code == 0
    assert "Fitness data generator dry-run" in out
    assert "calendar additions=31" in out
    assert "actual_changes=0" in out
    assert "planned_counts A=6 B=7 C=8 Z=5" in out
    print("main_dry_run_output PASS")


def main() -> int:
    assert_counts()
    assert_actual_immutable()
    assert_july_dry_run_matches_live()
    assert_rotation_checks()
    assert_write_mode_tempfile()
    assert_main_dry_run_output()
    print("ALL TESTS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
