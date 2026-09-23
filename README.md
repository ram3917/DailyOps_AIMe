# DailyOps AIMe (RAMA)

My personal multi-agent assistant.

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

## Orchestrator + Personal Trainer agent

RAMA's first multi-agent milestone: a generic orchestrator plus one
concrete specialist agent (Personal Trainer), talking over Slack.

```
agents/orchestrator.py          # registry loading, routing, ask_agent(), checkins
agents/personal_trainer/        # agent.py (behavior) + tools.py (Garmin/Notion I/O)
onboarding/onboard_agent.py     # CLI interview -> registry.yaml + memory.db
registry/personal_trainer.yaml  # this agent's full config (tools, routing, checkins)
memory/                         # one SQLite file per agent (schema.sql is the shared shape)
models/                         # router.py picks claude_backend.py or local_backend.py per agent
interfaces/slack_app.py         # Bolt app, Socket Mode - the "always with me" surface
interfaces/dashboard.py         # localhost-only read-only stub
```

**Access model:** Slack via Socket Mode (outbound-only websocket, no public
endpoint). The dashboard binds to `127.0.0.1` only. No cloud hosting, no
public URLs, anywhere in this milestone.

**Memory isolation** is structural, not just convention: `memory/db.py`'s
`open_agent_db()` is the only function that opens an agent's SQLite file,
and `tests/test_memory_isolation.py` statically verifies every
`agents/*/*.py` module only ever calls it with its own name. Cross-agent
info requests go through `orchestrator.ask_agent(name, question)` only,
which returns a natural-language answer from that agent's own memory —
never raw rows, never write access.

**Personal Trainer** reads Steps/Sleep/Weight from the Notion **Daily
Log** database (not its own copy) and writes new weigh-ins there too. When
those fields are missing or stale, it calls `fetch_garmin_data`, which
invokes the existing `scripts/garmin_workout_sync.py` as a subprocess
(unmodified) and separately upserts steps/sleep into Daily Log via a
direct Garmin fetch. Its own `memory/personal_trainer.db` holds only what
Notion doesn't: injury history, preferred workout types, morning check-in
time, and qualitative notes.

### Setup

```bash
pip install -r requirements.txt
```

Additional secrets beyond the Garmin/Notion ones above, via `.env`:

| Variable               | Description                                    |
| ----------------------- | ----------------------------------------------- |
| `SLACK_BOT_TOKEN`        | `xoxb-...`                                       |
| `SLACK_APP_TOKEN`        | `xapp-...`, Socket Mode app-level token          |
| `SLACK_CHECKIN_CHANNEL`  | Channel ID for proactive morning check-ins (optional) |
| `ANTHROPIC_API_KEY`      | Claude API key (used when an agent's `backend: claude_api`) |
| `RAMA_CLAUDE_MODEL`      | Override the default model (`claude-opus-5`), optional |

See `config/settings.example.yaml` for the same list with context.

### Onboarding

```bash
python onboarding/onboard_agent.py personal_trainer
```

Runs the scope interview (goal, tone, backend) and context interview
(step goal, sleep target, injuries/limits, preferred workouts, morning
check-in time), then writes `registry/personal_trainer.yaml` and seeds
`memory/personal_trainer.db`.

### Running

```bash
python interfaces/slack_app.py
```

Ask it things like "how was my sleep last night" or "what were my steps
yesterday" in a channel/DM the bot is in, or wait for the morning
check-in at the onboarded `morning_checkin_time`.

### Non-goals for this milestone

No other agents (Dietician, Finance, ...), no public/cloud hosting, no
multi-agent parallel dispatch, and the local-model backend
(`models/local_backend.py`) is a stub — every agent defaults to
`backend: claude_api` until a local runtime is wired up.
