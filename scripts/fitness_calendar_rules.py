#!/usr/bin/env python3
"""Program-readable planned-calendar rules for the fitness dashboard.

Do not parse `home-bodyweight-military-plan.md` directly: that Markdown file is the
human-readable source of intent, while this module is the executable rule config.
When changing the weekly structure here, review/update the Markdown plan in the
same change so human docs and generator behavior stay aligned.
"""
from __future__ import annotations

from datetime import date

# Monday=0 ... Sunday=6. Strength labels use the A/B block selected by
# week-of-month. Conditioning/ruck/recovery labels are stable every week.
WEEKDAY_TEMPLATE: dict[int, str] = {
    0: "{block}1",
    1: "C1",
    2: "{block}2",
    3: "C2",
    4: "{block}3",
    5: "Z2",
    6: "恢復",
}

REST_WEEKDAYS = {6}
PLANNED_BLOCKS = "ABCZ"


def week_of_month(day: date) -> int:
    """Return 1-based week-of-month aligned with the dashboard/check script."""
    first = day.replace(day=1)
    offset = first.weekday()  # Monday=0
    return (day.day + offset - 1) // 7 + 1


def ab_block(day: date) -> str:
    """Odd week-of-month = A, even week-of-month = B."""
    return "A" if week_of_month(day) % 2 == 1 else "B"


def planned_label(day: date) -> str:
    return WEEKDAY_TEMPLATE[day.weekday()].format(block=ab_block(day))


def planned_state(day: date) -> str:
    return "rest" if day.weekday() in REST_WEEKDAYS else "planned"
