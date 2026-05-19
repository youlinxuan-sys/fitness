# Fitness UI Spec

Target start: 2026-06-01

## Goal

Provide a clear personal dashboard for workout/health tracking from June onward.

## First-version dashboard ideas

### Home / Overview

- This week completion: planned vs done sessions.
- Current streak / last workout date.
- Quick status: energy, soreness, sleep, bodyweight if tracked.
- Next recommended workout from coach program.

### Calendar View

- Month calendar with workout days marked.
- Color states: planned, completed, missed, rest, deload/injury.
- Click a day to see the session log.

### Workout Log View

- Session cards with:
  - Date
  - Program day/type
  - Exercises
  - Sets/reps/weight
  - Cardio duration/distance
  - Effort/RPE
  - Notes

### Progress View

- Exercise progression charts.
- Cardio time/distance trend.
- Weekly training frequency.
- Optional bodyweight trend.

### Coach Program View

- Clean version of coach menu.
- Current training phase/month.
- Per-exercise target and notes.

## Possible implementation options

1. Static local web app generated from Markdown/JSON logs.
2. Streamlit dashboard for fast charts and forms.
3. Small local Next.js/React app if polished UI matters more.

## Suggested MVP

Use Streamlit first for speed:

- Store data in Markdown + CSV/JSON.
- Local browser dashboard.
- Easy charts/calendar.
- Can later upgrade to prettier React UI.

## Open questions

- What exactly should be visible at a glance?
- Should logs be entered through UI forms, Discord messages, or both?
- Should reminders be weekly or per planned workout day?

## 2026-05-18 — MVP v1 created

Installed and used ClawHub `dashboard` skill for the first UI pass.

Created static local dashboard:

- `~/dashboard/fitness/index.html`
- `~/dashboard/fitness/data.json`
- `~/dashboard/fitness/config.json`
- screenshot: `/mnt/1tb/projects/fitness-health-assistant/dashboard/fitness-dashboard-v1.png`

Design direction:

- Lin-Xuan Teal × Tech × Professional
- Dark glass dashboard
- At-a-glance layout: weekly completion, streak, last workout, readiness, June calendar, next workout, progress charts, recent logs, coach program

Visual QA:

- Rendered with Playwright screenshot at 1440×1400.
- First QA found title wrapping/contrast/empty-state issues.
- Fixed title size, contrast, calendar label size, chart contrast, and cardio empty state.
- Second QA passed with only minor future polish suggestions.

Next improvements after real data:

- Replace placeholder June plan with coach program.
- Add real workout log ingestion.
- Add better empty-state illustration or placeholder trend once enough data exists.
- Decide whether log entry is via Discord only, UI form, or both.

## 2026-05-18 — Workout mode connected

Homepage dashboard now includes a "今天照著練" workout mode:

- Dropdown selector for A1/A2/A3/B1/B2/B3.
- Selected workout is stored in browser `localStorage` as `fitness.selectedWorkout`.
- The main dashboard displays full workout details for the selected item:
  - title, week, focus
  - warm-up chips
  - exercise list
  - prescription and rest chips
  - technique notes and substitutions
- Data source: `~/dashboard/fitness/data.json` `programs` object.

Design QA:

- Rendered screenshot: `/mnt/1tb/projects/fitness-health-assistant/dashboard/fitness-dashboard-workout-mode-v1.png`.
- QA passed for picker/workout mode usability.
- Fixed oversized hero title wrap after QA.
