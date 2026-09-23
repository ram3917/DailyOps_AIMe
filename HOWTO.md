# HowTo: setting up RAMA (Orchestrator + Personal Trainer)

Step-by-step guide to get the Garmin→Notion sync and the
Orchestrator/Personal Trainer Telegram agent running from scratch. For
what each piece does and the file layout, see [README.md](README.md).

## 0. Prerequisites

- Python 3.11+
- A Garmin Connect account
- A Notion workspace with the **Daily Ops** page (Workouts + Daily Log
  databases already exist there)
- A Telegram account
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

### Telegram (long polling — no public URL needed)

1. In Telegram, message [@BotFather](https://t.me/BotFather) → `/newbot`.
   Follow the prompts (display name, then a unique `@username` ending in
   `bot`).
2. BotFather replies with an API token like `123456789:AAExampleToken...`
   — this is `TELEGRAM_BOT_TOKEN`.
3. Open a chat with your new bot (search its `@username`) and send it any
   message — Telegram only delivers messages to the bot for chats that
   messaged it first.
4. (Optional, for proactive morning check-ins) Get the chat ID to post
   check-ins to. Easiest way: send your bot a message, then visit
   `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser (with
   your real token) and read `message.chat.id` from the JSON response.
   This is `TELEGRAM_CHECKIN_CHAT_ID`.

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
TELEGRAM_BOT_TOKEN=123456789:AAExampleToken...
TELEGRAM_CHECKIN_CHAT_ID=000000000
```

`.env` is git-ignored — never commit it.

For the GitHub Actions Garmin sync/backfill workflows (separate from the
Telegram agent), add `GARMIN_EMAIL`, `GARMIN_PASSWORD`, and `NOTION_TOKEN`
as **repository secrets** too (Settings → Secrets and variables → Actions).

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

## 6. Run the Telegram app

```bash
python interfaces/telegram_app.py
```

Leave this running (it's a long-polling client against Telegram's HTTP
Bot API — no ports exposed, no public URL). Message the bot:

- "what were my steps yesterday"
- "how was my sleep last night"
- "what's my weight today" → if missing, it asks; reply with a bare
  number (e.g. `82.4`) and it logs it to Notion Daily Log
- Anything else fitness-related falls through to a free-form Claude reply
  using your onboarding profile
- Anything unrelated gets "I don't have an agent set up for that yet."

At the `morning_checkin_time` you gave during onboarding, it'll send the
weight prompt + sleep feedback + steps progress to
`TELEGRAM_CHECKIN_CHAT_ID` automatically (checked once a minute; the
process must be running).

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
| Telegram bot never responds | You haven't messaged the bot first (Telegram won't deliver updates otherwise), `TELEGRAM_BOT_TOKEN` is wrong, or `interfaces/telegram_app.py` isn't running. |
| `RuntimeError: Telegram API error` | Check the token is correct and the bot hasn't been blocked/deleted; the error message includes Telegram's own response body. |
| `NotImplementedError` from the agent | Registry `backend` is set to `local_model` but no local runtime is wired up — set it back to `claude_api` (re-run onboarding, choice `1`). |
| Morning check-in never fires | `interfaces/telegram_app.py` isn't running continuously, or `morning_checkin_time` in the profile doesn't match `HH:MM` 24h format. |
| `pytest` fails on `test_memory_isolation` | An agent module is calling `open_agent_db()` with something other than a literal string or its own `AGENT_NAME` constant — see the assertion message for the offending file. |
