# HowTo: setting up RAMA Personal Trainer

## 0. Prerequisites

- Python 3.11+
- A Garmin Connect account
- A Telegram account
- Either [Ollama](https://ollama.com) running locally, **or** a
  [Hugging Face](https://huggingface.co) account with an API token

## 1. Clone and install

```bash
git clone <this repo>
cd DailyOps_AIMe
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Get your credentials

### Garmin

Just your normal Garmin Connect email + password.

### Telegram

1. Message [@BotFather](https://t.me/BotFather) → `/newbot`, follow the
   prompts.
2. Copy the API token it gives you (`123456789:AAExampleToken...`) — this
   is `TELEGRAM_BOT_TOKEN`.
3. Open a chat with your new bot and send it any message first — Telegram
   only delivers messages to a bot for chats that messaged it first.

### LLM backend — pick one

**Ollama (local, recommended if you have the hardware):**

```bash
# install from https://ollama.com, then:
ollama pull llama3.1
ollama serve   # usually already running as a service after install
```
Set `LLM_BACKEND=ollama`, `OLLAMA_HOST=http://localhost:11434`,
`OLLAMA_MODEL=llama3.1` (or whichever model you pulled).

**Hugging Face hosted Inference API (lighter on your hardware):**

1. Create a token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) (read access is enough).
2. Set `LLM_BACKEND=hf`, `HF_API_TOKEN=<your token>`, and `HF_MODEL` to a
   chat model available on the Inference API (default:
   `meta-llama/Llama-3.1-8B-Instruct`).

## 3. Fill in `.env`

```bash
cp .env.example .env
```

Edit `.env` with your credentials, then load it into your shell:

```bash
export $(grep -v '^#' .env | xargs)
```

## 4. Set up your profile

```bash
python -m trainer.setup_profile
```

Answers (goal, tone, step goal, sleep target, injuries/limits, preferred
workouts) are saved to `trainer.db`. Run this again anytime to update them.

## 5. Backfill Garmin data

```bash
python scripts/garmin_sync.py --days 30
```

Then set up a daily cron job to keep it current, e.g. (`crontab -e`):

```
30 6 * * * cd /path/to/DailyOps_AIMe && /path/to/.venv/bin/python scripts/garmin_sync.py
```

## 6. Run the bot

```bash
python -m trainer.bot
```

Leave it running (long polling — no exposed ports, no public URL).
Message the bot anything: "how'd I sleep", "what were my steps
yesterday", "82.4" to log today's weight, or just talk to it like a
trainer — it remembers your recent conversation and your logged data.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `GarminConnectAuthenticationError` | Wrong/missing `GARMIN_EMAIL`/`GARMIN_PASSWORD`, or env vars weren't exported into the shell. |
| Telegram bot never responds | You haven't messaged the bot first, `TELEGRAM_BOT_TOKEN` is wrong, or `trainer.bot` isn't running. |
| `ConnectionError` from Ollama | Ollama isn't running, or `OLLAMA_HOST`/`OLLAMA_MODEL` don't match your setup (`ollama list` to check pulled models). |
| `KeyError: 'HF_API_TOKEN'` | Set `LLM_BACKEND=hf` but forgot the token in `.env`. |
| Bot's replies have no memory of earlier questions | Check `trainer.db` exists and is writable — `add_message`/`get_recent_messages` in `trainer/db.py` handle this automatically. |
