# Fitness Health Assistant

運動小幫手：教練菜單、今日訓練模式、訓練紀錄與進度追蹤。

## GitHub Pages

This repo is intended to publish the static app from `public/` via GitHub Pages.

Recommended Pages setting:

- Source: GitHub Actions
- Workflow: `.github/workflows/pages.yml`

Expected URL after publishing under user `xuan1071` and repo `fitness`:

<https://xuan1071.github.io/fitness/>

## Local preview

```bash
cd public
python3 -m http.server 8787
```

Then open <http://localhost:8787/>.

## Collaboration

Both ASUS 小璁璁 and Mac 小璁芛 should develop through this GitHub repo rather than ad-hoc file copying.
# Fitness & Health Assistant

Start date: 2026-05-18
Owner: 游林軒

Purpose: track coach-provided workout programming, daily training logs, light health notes, and progress review.

## Scope

- Record coach workout menu/program.
- Log each session: date, workout day/type, exercises, sets, reps, weight/resistance, cardio, RPE/effort, notes.
- Track bodyweight/body measurements only if owner wants.
- Track sleep/energy/soreness/injury notes only if owner wants.
- Provide weekly/monthly summaries and gentle reminders.
- Do not replace medical advice or coach instructions.

## Files

- `coach-program.md` — coach-provided workout menu/program.
- `training-log.md` — chronological workout records.
- `metrics.md` — optional bodyweight/measurements/health indicators.
- `reviews.md` — weekly/monthly summaries and adjustments.
