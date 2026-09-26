"""Telegram bot for the Personal Trainer - long polling, no exposed ports.

Every message gets full recent chat history as context plus today's/
yesterday's logged data, answered by whichever backend LLM_BACKEND
selects (ollama|hf). A bare number in a plausible weight range is logged
straight to the DB instead of going to the LLM.

Run: python -m trainer.bot
"""
import datetime
import os
import time

import requests

from trainer import db
from trainer.backends import get_reply
from trainer.prompts import build_system_prompt

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
WEIGHT_RANGE = (30.0, 300.0)
HISTORY_LIMIT = 20


def _call(method: str, **params):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    url = TELEGRAM_API.format(token=token, method=method)
    payload = {k: v for k, v in params.items() if v is not None}
    r = requests.post(url, json=payload, timeout=35)
    r.raise_for_status()
    body = r.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram API error calling {method}: {body}")
    return body["result"]


def send_message(chat_id, text: str) -> None:
    _call("sendMessage", chat_id=chat_id, text=text)


def _maybe_record_weight(text: str) -> str | None:
    stripped = text.strip().replace(",", ".")
    try:
        value = float(stripped)
    except ValueError:
        return None
    if WEIGHT_RANGE[0] <= value <= WEIGHT_RANGE[1]:
        db.set_weight(datetime.date.today().isoformat(), value)
        return f"Logged {value} kg for today."
    return None


def handle_message(text: str, chat_id) -> None:
    reply = _maybe_record_weight(text)
    if reply is None:
        today = datetime.date.today().isoformat()
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        system = build_system_prompt(
            db.get_all_profile(),
            db.get_daily_log(today),
            db.get_daily_log(yesterday),
        )
        reply = get_reply(system, db.get_recent_messages(HISTORY_LIMIT), text)

    db.add_message("user", text)
    db.add_message("assistant", reply)
    send_message(chat_id, reply)


def _polling_loop() -> None:
    offset = None
    while True:
        try:
            updates = _call("getUpdates", offset=offset, timeout=30)
        except requests.RequestException:
            time.sleep(5)
            continue
        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message") or {}
            text = message.get("text")
            chat_id = (message.get("chat") or {}).get("id")
            if text and chat_id:
                handle_message(text, chat_id)


if __name__ == "__main__":
    _polling_loop()
