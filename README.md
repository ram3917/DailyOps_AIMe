# RAMA - Personal Trainer

A Telegram chatbot that's your personal trainer: it reads your Garmin
data (steps, sleep, weight, workouts) from a local database and talks to
you about it, in your pocket, all day. Fully self-hosted - no cloud LLM,
no Notion, no external chat platform beyond Telegram itself.

**New to this repo?** See [HOWTO.md](HOWTO.md) for setup from scratch.

## What's here

```
scripts/garmin_sync.py     # pulls Garmin data, writes to trainer.db (run via cron)
trainer/db.py               # the only file that opens trainer.db (profile, daily log, chat history)
trainer/backends.py          # LLM backends: ollama (local) or hf (Hugging Face hosted API)
trainer/prompts.py            # the trainer's persona/system prompt
trainer/bot.py                 # Telegram bot, long polling - the actual chat interface
trainer/setup_profile.py        # one-time interactive setup of your goals/limits
```

## How it fits together

1. **`scripts/garmin_sync.py`** runs on a schedule (cron) and upserts one
   row per day into `trainer.db`'s `daily_log` table: steps, sleep hours,
   weight (if you use a Garmin smart scale), resting HR, body battery,
   stress, and workout details (type, duration, calories, HR, training
   load, distance, elevation).
2. **`trainer/bot.py`** is a long-polling Telegram bot (no public
   endpoint, no exposed ports). Every message you send gets answered with
   your recent chat history plus today's/yesterday's logged data as
   context, via whichever `LLM_BACKEND` you configured. Send it a bare
   number in a plausible weight range (e.g. `82.4`) and it logs that as
   today's weight directly, no LLM call needed.
3. Everything - your goals, your Garmin data, and the full chat history -
   lives in one local SQLite file, `trainer.db`. Nothing is sent
   anywhere except to Telegram and to whichever LLM backend you picked.

## Setup

See [HOWTO.md](HOWTO.md) for the full walkthrough (Garmin, Telegram,
Ollama or Hugging Face). Short version:

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your credentials
export $(grep -v '^#' .env | xargs)

python -m trainer.setup_profile      # answer a few questions once
python scripts/garmin_sync.py --days 30   # backfill the last 30 days
python -m trainer.bot                      # start the bot
```

## Non-goals

No Notion, no cloud LLM API, no Slack, no n8n, no multi-agent framework.
This is one bot, one database, one job: your personal trainer.
