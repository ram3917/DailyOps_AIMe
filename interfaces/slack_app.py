"""Slack interface, Socket Mode - outbound-only websocket, no public
endpoint, no exposed ports. This is the "always with me" surface.

Requires SLACK_BOT_TOKEN (xoxb-...) and SLACK_APP_TOKEN (xapp-..., Socket
Mode app-level token) in the environment. SLACK_CHECKIN_CHANNEL (a channel
ID) is optional - without it, proactive morning check-ins are computed but
not posted anywhere.
"""
import datetime
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from agents.orchestrator import Orchestrator
from memory.db import get_profile, open_agent_db

orchestrator = Orchestrator()
app = App(token=os.environ["SLACK_BOT_TOKEN"])


@app.event("message")
def handle_message_events(event, say):
    text = event.get("text", "")
    if not text or event.get("bot_id"):
        return

    lower = text.strip().lower()
    if lower.startswith("onboard "):
        agent_name = lower.split("onboard ", 1)[1].strip()
        say(
            f"Run `python onboarding/onboard_agent.py {agent_name}` in a "
            f"terminal to onboard this agent - Slack-driven onboarding "
            f"isn't wired up yet in this milestone."
        )
        return

    _agent_name, reply = orchestrator.route_message(text)
    say(reply)


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
                channel = os.environ.get("SLACK_CHECKIN_CHANNEL")
                if message and channel:
                    app.client.chat_postMessage(channel=channel, text=message)
                sent_today[key] = True
        time.sleep(poll_seconds)


def main() -> None:
    threading.Thread(target=_checkin_scheduler_loop, daemon=True).start()
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()


if __name__ == "__main__":
    main()
