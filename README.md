# DailyOps AIMe

My personal assistant that runs daily tasks.

Currently syncs Garmin Connect workout and daily wellness data into a
Notion database, so each day shows up as a row without manual entry — rest
days included.

## What's here

- `scripts/garmin_workout_sync.py` — fetches **today's** Garmin data (the
  day's activity, if any, plus steps/resting HR/body battery/stress) and
  pushes it to Notion. On days with no logged workout, the row is marked
  `Rest` but still carries the day-level metrics.
- `scripts/garmin_backfill_30days.py` — walks the **last 30 days** and pushes
  one row per day to Notion, same logic as above. Reuses the fetch/push
  logic from `garmin_workout_sync.py`.
- `.github/workflows/garmin-workout-sync.yml` — runs the daily sync
  automatically every night (cron) and supports manual runs.
- `.github/workflows/garmin-backfill-30days.yml` — runs the 30-day backfill,
  manually only (`workflow_dispatch`).

## Setup

### Secrets

Both scripts need:

| Variable          | Description                                   |
| ------------------ | ---------------------------------------------- |
| `GARMIN_EMAIL`      | Garmin Connect account email                   |
| `GARMIN_PASSWORD`   | Garmin Connect account password                |
| `NOTION_TOKEN`      | Notion integration token with access to the Workouts data source |

For GitHub Actions, add these as repository secrets
(**Settings → Secrets and variables → Actions**) — the workflows read them
from `secrets.*`.

For local runs, copy `.env.example` to `.env` and fill in real values:

```bash
cp .env.example .env
```

`.env` is git-ignored and never committed.

### Notion database

Both scripts write to a hardcoded Notion data source ID
(`WORKOUTS_DB_ID` in `scripts/garmin_workout_sync.py`) with these properties:
`Session` (title), `Date`, `Activity Type` (select), `Duration (min)`,
`Calories`, `Avg HR`, `Max HR`, `Training Load`, `Steps`, `Distance (km)`,
`Elevation Gain (m)`, `Resting HR`, `Body Battery`, `Stress`.

## Running locally

```bash
pip install garminconnect requests
export $(cat .env | xargs)   # or use python-dotenv / your own loader

python scripts/garmin_workout_sync.py       # today only
python scripts/garmin_backfill_30days.py    # last 30 days
```

## Running via GitHub Actions

- **Garmin Workout Sync** runs nightly at 19:00 UTC and can also be
  triggered manually from the Actions tab.
- **Garmin 30-Day Backfill** only runs when triggered manually from the
  Actions tab (**Actions → Garmin 30-Day Backfill → Run workflow**).
