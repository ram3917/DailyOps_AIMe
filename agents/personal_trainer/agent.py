"""Personal Trainer agent: the first concrete specialist built against the
orchestrator's interfaces.

Objective metrics (steps, sleep, weight) are read from Notion's Daily Log,
never cached here. This agent's own memory.db (opened only as
"personal_trainer" - see memory/db.py and tests/test_memory_isolation.py)
holds only what Notion doesn't: injury history, preferred workout types,
morning check-in time, and qualitative notes.
"""
import datetime
import re

from memory.db import get_all_profile, get_profile, open_agent_db
from models.router import get_backend

from .tools import fetch_garmin_data, read_daily_log, write_daily_log_field

AGENT_NAME = "personal_trainer"

_WEIGHT_INTENT = re.compile(r"\b(weight|weigh)\b", re.I)
_SLEEP_INTENT = re.compile(r"\bsleep\b", re.I)
_STEPS_INTENT = re.compile(r"\bsteps?\b", re.I)
_PLAUSIBLE_WEIGHT_KG = (30.0, 300.0)


def _db():
    return open_agent_db(AGENT_NAME)


def _today() -> str:
    return datetime.date.today().isoformat()


def _yesterday() -> str:
    return (datetime.date.today() - datetime.timedelta(days=1)).isoformat()


def _ensure_fresh(date_str: str, fields: list[str]) -> dict:
    """If any of `fields` is missing from that date's Daily Log row, call
    fetch_garmin_data once to refresh it, then re-read."""
    row = read_daily_log(date_str)
    if row is None or any(row.get(field) is None for field in fields):
        fetch_garmin_data(date_str)
        row = read_daily_log(date_str)
    return row or {}


def _weight_prompt() -> str:
    row = read_daily_log(_today())
    if row and row.get("weight_kg") is not None:
        return f"Today's weight is already logged: {row['weight_kg']} kg."
    return "I don't have today's weight yet — what did you weigh in at this morning?"


def record_weight(value_kg: float) -> str:
    """Writes directly to Notion Daily Log, never to this agent's own DB -
    weight is an objective metric, not something Personal Trainer owns."""
    write_daily_log_field(_today(), {"weight_kg": value_kg})
    return f"Logged {value_kg} kg for today."


def _sleep_feedback() -> str:
    target = get_profile(_db(), "sleep_target_hours")
    row = _ensure_fresh(_yesterday(), ["sleep_hours"])
    hours = row.get("sleep_hours")
    if hours is None:
        return "I don't have last night's sleep data yet."

    message = f"You slept {hours}h last night"
    if target:
        target_hours = float(target)
        diff = hours - target_hours
        if diff >= 0:
            message += f", at or above your {target_hours}h target — nice."
        elif diff >= -0.5:
            message += f", just under your {target_hours}h target."
        else:
            message += f", {abs(diff):.1f}h short of your {target_hours}h target."
    return message


def _steps_progress() -> str:
    goal = get_profile(_db(), "daily_step_goal")
    row = _ensure_fresh(_yesterday(), ["steps"])
    steps = row.get("steps")
    if steps is None:
        return "I don't have yesterday's step count yet."

    steps = int(steps)
    message = f"Yesterday: {steps:,} steps"
    if goal:
        goal = int(float(goal))
        if steps >= goal:
            message += f" — goal of {goal:,} met, by {steps - goal:,}."
        else:
            message += f" — missed your {goal:,} goal by {goal - steps:,}."
    return message


def _maybe_weight_reply(text: str) -> str | None:
    """A bare number sent in reply to the weight prompt."""
    stripped = text.strip().replace(",", ".")
    try:
        value = float(stripped)
    except ValueError:
        return None
    if _PLAUSIBLE_WEIGHT_KG[0] <= value <= _PLAUSIBLE_WEIGHT_KG[1]:
        return record_weight(value)
    return None


def handle_message(text: str) -> str:
    weight_reply = _maybe_weight_reply(text)
    if weight_reply is not None:
        return weight_reply

    if _WEIGHT_INTENT.search(text):
        return _weight_prompt()
    if _SLEEP_INTENT.search(text):
        return _sleep_feedback()
    if _STEPS_INTENT.search(text):
        return _steps_progress()

    return _freeform_reply(text)


def _freeform_reply(text: str) -> str:
    profile = get_all_profile(_db())
    tone = profile.get("tone", "encouraging")
    system = (
        "You are the user's Personal Trainer agent inside RAMA, their personal "
        f"multi-agent assistant. Speak in a {tone} tone. You only know what is in "
        "the profile below (their own stated goals/preferences/limits) plus "
        "whatever they just said - you do not have live access to their Notion "
        "data in this reply, so don't invent step counts, sleep hours, or "
        f"weight.\nProfile: {profile}"
    )
    return get_backend(AGENT_NAME).reply(system=system, user_message=text)


def answer_readonly(question: str) -> str:
    """Read-only Q&A entry point for orchestrator.ask_agent(). Queries only
    this agent's own memory and returns natural language - never raw rows,
    never write access. This is the sole sanctioned way another agent may
    learn anything from Personal Trainer.
    """
    profile = get_all_profile(_db())
    system = (
        "Answer only using this profile data about the user's fitness "
        "goals, preferences, and limits. If the answer isn't contained in "
        f"it, say you don't know rather than guessing.\nProfile: {profile}"
    )
    return get_backend(AGENT_NAME).reply(system=system, user_message=question)


def run_morning_checkin() -> str:
    return "\n".join([_weight_prompt(), _sleep_feedback(), _steps_progress()])
