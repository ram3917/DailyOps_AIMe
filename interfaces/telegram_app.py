"""Telegram interface (long polling - outbound-only, no public endpoint,
no exposed ports). This is the "always with me" surface.

Implemented over Telegram's plain HTTP Bot API via `requests` rather than
an async SDK, to stay consistent with the rest of this codebase (which is
synchronous throughout, e.g. agents/personal_trainer/tools.py's Notion
calls) and to keep the background check-in scheduler thread simple - no
event loop to hand results off to.

Requires TELEGRAM_BOT_TOKEN (from @BotFather) in the environment.
TELEGRAM_CHECKIN_CHAT_ID (a chat ID) is optional - without it, proactive
morning check-ins are computed but not sent anywhere.
"""
import datetime
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from agents.orchestrator import Orchestrator
from memory.db import get_profile, open_agent_db

orchestrator = Orchestrator()

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _call(method: str, **params):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    url = TELEGRAM_API.format(token=token, method=method)
    payload = {key: value for key, value in params.items() if value is not None}
    r = requests.post(url, json=payload, timeout=35)
    r.raise_for_status()
    body = r.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram API error calling {method}: {body}")
    return body["result"]


def send_message(chat_id, text: str) -> None:
    _call("sendMessage", chat_id=chat_id, text=text)


def _handle_update(update: dict) -> None:
    message = update.get("message") or {}
    text = message.get("text")
    chat_id = (message.get("chat") or {}).get("id")
    if not text or not chat_id:
        return

    lower = text.strip().lower()
    if lower.startswith("onboard "):
        agent_name = lower.split("onboard ", 1)[1].strip()
        send_message(
            chat_id,
            f"Run `python onboarding/onboard_agent.py {agent_name}` in a "
            f"terminal to onboard this agent - Telegram-driven onboarding "
            f"isn't wired up yet in this milestone.",
        )
        return

    _agent_name, reply = orchestrator.route_message(text)
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
            _handle_update(update)


def _checkin_scheduler_loop(poll_seconds: int = 30) -> None:
    """Best-effort in-process scheduler: fires each agent's morning
    check-in once per day, at the time stored in that agent's own profile
    (morning_checkin_time). Not a durable cron - if the process restarts
    mid-day, a check-in already sent today is not replayed, but one that
    was due while the process was down is simply missed.
    """
    sent_today: dict[tuple[str, str], bool] = {}
    while True:
        now = datetime.datetime.now()
        today = now.date().isoformat()
        for agent_name in orchestrator.registry:
            conn = open_agent_db(agent_name)
            checkin_time = get_profile(conn, "morning_checkin_time")
            conn.close()
            if not checkin_time:
                continue
            try:
                hour, minute = (int(part) for part in checkin_time.split(":"))
            except ValueError:
                continue

            key = (agent_name, today)
            due = now.hour == hour and now.minute == minute
            if due and key not in sent_today:
                message = orchestrator.run_agent_checkin(agent_name)
                chat_id = os.environ.get("TELEGRAM_CHECKIN_CHAT_ID")
                if message and chat_id:
                    send_message(chat_id, message)
                sent_today[key] = True
        time.sleep(poll_seconds)


def main() -> None:
    threading.Thread(target=_checkin_scheduler_loop, daemon=True).start()
    _polling_loop()


if __name__ == "__main__":
    main()
