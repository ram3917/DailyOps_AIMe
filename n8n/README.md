# n8n workflow: RAMA Personal Trainer

`rama-personal-trainer.workflow.json` is an n8n port of the Telegram
Personal Trainer bot — an alternative to running
`interfaces/telegram_app.py` yourself, for anyone who'd rather host this
on n8n instead of a Python process.

**Mirrors:** `agents/personal_trainer/agent.py`'s intent routing (weight
logging, sleep feedback vs. target, steps vs. goal, Claude freeform
fallback) and `interfaces/telegram_app.py`'s morning check-in.

**Does not mirror:** the actual Garmin fetch. Garmin's login flow
(`garminconnect`'s reverse-engineered SSO handshake) isn't practical to
replicate in n8n. This workflow only reads/writes the Notion **Daily
Log** database, which `scripts/garmin_workout_sync.py` / the GitHub
Actions cron already keeps populated — that piece stays as-is.

## Import

1. n8n → **Workflows** → **Import from File** → select
   `rama-personal-trainer.workflow.json`.
2. Create 3 credentials (n8n prompts you to map these on import):
   - **Telegram Bot (RAMA)** — Telegram API credential, bot token from
     [@BotFather](https://t.me/BotFather) (see [../HOWTO.md](../HOWTO.md) for the full walkthrough).
   - **Notion API Token** — generic **Header Auth** credential.
     Header name `Authorization`, value `Bearer <your Notion integration secret>`.
   - **Anthropic API Key** — generic **Header Auth** credential.
     Header name `x-api-key`, value `<your Anthropic API key>`.
3. Open the **Config** and **Config (Checkin)** nodes and fill in your
   `daily_step_goal`, `sleep_target_hours`, `tone`, `primary_goal`, and
   `telegram_checkin_chat_id`.
4. Edit the **Morning Checkin Schedule** node's cron expression
   (default `30 7 * * *`) to your preferred check-in time.
5. Activate the workflow.

## Architecture note

n8n's Telegram Trigger node registers a **webhook**, unlike the
Python bot's long-polling (zero exposed ports). Your n8n instance needs a
public URL Telegram can reach — n8n Cloud has this by default; self-hosted
needs a domain or tunnel.

## Layout

- **Telegram Trigger → Config → Classify Intent → Route Intent (Switch)**
  fans out into 5 branches: `record_weight`, `weight_prompt`, `sleep`,
  `steps`, and a `freeform` fallback that calls Claude.
- **Morning Checkin Schedule** is a separate trigger that composes the
  same three checks into one message, sent to `telegram_checkin_chat_id`.
- Sticky notes on the canvas repeat the credential/config setup steps.
