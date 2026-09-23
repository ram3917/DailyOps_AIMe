# HowTo: setting up RAMA (Orchestrator + Personal Trainer)

Step-by-step guide to get the Garmin→Notion sync and the
Orchestrator/Personal Trainer Slack agent running from scratch. For what
each piece does and the file layout, see [README.md](README.md).

## 0. Prerequisites

- Python 3.11+
- A Garmin Connect account
- A Notion workspace with the **Daily Ops** page (Workouts + Daily Log
  databases already exist there)
- A Slack workspace where you can install apps
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

## 1. Clone and install

```bash
git clone <this repo>
cd DailyOps_AIMe
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Get your credentials

### Garmin

Just your normal Garmin Connect email + password. No app/API registration
needed — `garminconnect` logs in as you.

### Notion

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) → **New integration**.
2. Name it (e.g. "RAMA"), pick your workspace, create it. Copy the
   **Internal Integration Secret** (`secret_...` or `ntn_...`) — this is `NOTION_TOKEN`.
3. Open the **Daily Ops** page in Notion → `•••` menu → **Connections** →
   add your new integration. This shares the page and everything under it
   (Workouts, Daily Log, Balances, Trades, Todos) with the integration —
   without this step, every API call gets a 404.

### Anthropic

Create a key at [console.anthropic.com](https://console.anthropic.com) →
**API Keys**. This is `ANTHROPIC_API_KEY`.

### Slack (Socket Mode — no public URL needed)

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**. Name it, pick your workspace.
2. **Socket Mode** (left sidebar) → toggle **Enable Socket Mode** on. This
   prompts you to generate an app-level token — name it anything, scope
   `connections:write`. Copy the token (`xapp-...`) — this is `SLACK_APP_TOKEN`.
3. **OAuth & Permissions** → under **Scopes → Bot Token Scopes**, add:
   - `chat:write` (send messages)
   - `im:history` (read DMs sent to the bot)
   - `channels:history` (read messages in channels it's in, for the
     `#`-channel case)
   - `message.im` isn't a scope you add here — see Event Subscriptions below.
4. **Event Subscriptions** → toggle on. Under **Subscribe to bot events**,
   add `message.im` (DMs) and, if you want to talk to it in a channel,
   `message.channels`. Save.
5. Back at the top of **OAuth & Permissions**, click **Install to
   Workspace**, approve. Copy the **Bot User OAuth Token** (`xoxb-...`) —
   this is `SLACK_BOT_TOKEN`.
6. Invite the bot to a DM (just message it directly) or `/invite @YourApp`
   into a channel.
7. (Optional, for proactive morning check-ins) Get the channel ID you want
   check-ins posted to: open the channel in Slack → `•••` → **View channel
   details** → ID is at the bottom. This is `SLACK_CHECKIN_CHANNEL`.

## 3. Fill in `.env`

```bash
cp .env.example .env
```

Edit `.env` with the credentials from step 2:

```
GARMIN_EMAIL=you@example.com
GARMIN_PASSWORD=your-garmin-password
NOTION_TOKEN=secret_...
ANTHROPIC_API_KEY=sk-ant-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_CHECKIN_CHANNEL=C0000000000
```

`.env` is git-ignored — never commit it.

For the GitHub Actions Garmin sync/backfill workflows (separate from the
Slack agent), add `GARMIN_EMAIL`, `GARMIN_PASSWORD`, and `NOTION_TOKEN` as
**repository secrets** too (Settings → Secrets and variables → Actions).

## 4. Load the env vars into your shell

```bash
export $(grep -v '^#' .env | xargs)
```

(or use `python-dotenv` / your own loader if you prefer)

## 5. Onboard the Personal Trainer

```bash
python onboarding/onboard_agent.py personal_trainer
```

Answer the interview questions (goal, tone, backend, step goal, sleep
target, injuries/limits, preferred workouts, morning check-in time). This
writes `registry/personal_trainer.yaml` and creates
`memory/personal_trainer.db`.

## 6. Run the Slack app

```bash
python interfaces/slack_app.py
```

Leave this running (it's a long-lived Socket Mode connection — no ports
exposed, no public URL). DM the bot or mention it in a channel it's in:

- "what were my steps yesterday"
- "how was my sleep last night"
- "what's my weight today" → if missing, it asks; reply with a bare
  number (e.g. `82.4`) and it logs it to Notion Daily Log
- Anything else fitness-related falls through to a free-form Claude reply
  using your onboarding profile
- Anything unrelated gets "I don't have an agent set up for that yet."

At the `morning_checkin_time` you gave during onboarding, it'll post the
weight prompt + sleep feedback + steps progress to `SLACK_CHECKIN_CHANNEL`
automatically (checked once a minute; the process must be running).

## 7. (Optional) Run the Garmin sync scripts manually

```bash
python scripts/garmin_workout_sync.py       # today's Workouts row
python scripts/garmin_backfill_30days.py    # last 30 days
```

These also run in GitHub Actions — nightly cron for the first, manual
`workflow_dispatch` for the backfill (Actions tab → pick the workflow →
**Run workflow**).

## 8. (Optional) Run the dashboard stub

```bash
python interfaces/dashboard.py
```

Visit `http://127.0.0.1:5151` — read-only JSON view of onboarded agents'
profiles. Localhost only, by design.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Notion calls return 404 | The integration isn't connected to the Daily Ops page — redo step 2's Notion §3. |
| `GarminConnectAuthenticationError` | Wrong/missing `GARMIN_EMAIL`/`GARMIN_PASSWORD`, or env vars weren't exported into the shell running the script. |
| Slack bot never responds | Socket Mode not enabled, or the bot isn't in the channel/DM, or `message.im`/`message.channels` events weren't subscribed. |
| `NotImplementedError` from the agent | Registry `backend` is set to `local_model` but no local runtime is wired up — set it back to `claude_api` (re-run onboarding, choice `1`). |
| Morning check-in never fires | `interfaces/slack_app.py` isn't running continuously, or `morning_checkin_time` in the profile doesn't match `HH:MM` 24h format. |
| `pytest` fails on `test_memory_isolation` | An agent module is calling `open_agent_db()` with something other than a literal string or its own `AGENT_NAME` constant — see the assertion message for the offending file. |
