"""External I/O for the Personal Trainer agent: Notion Daily Log read/write,
and the Garmin data-fetch wrapper.

Personal Trainer does not keep its own copy of objective metrics (steps,
sleep, weight) - it reads them from Notion's Daily Log, the same table
other future agents (Dietician, etc.) will read. Its own memory.db holds
only what Notion doesn't: injury history, preferred workout types,
qualitative notes.
"""
import datetime
import os
import subprocess
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GARMIN_SYNC_SCRIPT = REPO_ROOT / "scripts" / "garmin_workout_sync.py"

# "Daily Log" data source in the Daily Ops Notion workspace.
DAILY_LOG_DATA_SOURCE_ID = "54dfd16e-179a-47bf-9d8c-ee1f52f1517f"

DAILY_LOG_FIELD_MAP = {
    "steps": "Steps",
    "weight_kg": "Weight (kg)",
    "sleep_hours": "Sleep (hrs)",
}


def _notion_headers() -> dict:
    return {
        "Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
        "Notion-Version": "2025-09-03",
        "Content-Type": "application/json",
    }


def read_daily_log(date_str: str) -> dict | None:
    """Read-only: returns {page_id, steps, weight_kg, sleep_hours} for the
    given date, or None if no Daily Log row exists for that date yet."""
    url = f"https://api.notion.com/v1/data_sources/{DAILY_LOG_DATA_SOURCE_ID}/query"
    payload = {"filter": {"property": "Date", "date": {"equals": date_str}}}
    r = requests.post(url, headers=_notion_headers(), json=payload, timeout=30)
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        return None
    props = results[0]["properties"]
    return {
        "page_id": results[0]["id"],
        "steps": props.get("Steps", {}).get("number"),
        "weight_kg": props.get("Weight (kg)", {}).get("number"),
        "sleep_hours": props.get("Sleep (hrs)", {}).get("number"),
    }


def write_daily_log_field(date_str: str, updates: dict) -> None:
    """Create-or-update today's Daily Log row. `updates` maps this module's
    own field names (steps/weight_kg/sleep_hours) or raw Notion property
    names to numeric values."""
    existing = read_daily_log(date_str)
    properties = {}
    for key, value in updates.items():
        prop_name = DAILY_LOG_FIELD_MAP.get(key, key)
        properties[prop_name] = {"number": value}

    if existing:
        url = f"https://api.notion.com/v1/pages/{existing['page_id']}"
        r = requests.patch(url, headers=_notion_headers(), json={"properties": properties}, timeout=30)
    else:
        properties["Entry"] = {"title": [{"text": {"content": date_str}}]}
        properties["Date"] = {"date": {"start": date_str}}
        url = "https://api.notion.com/v1/pages"
        payload = {"parent": {"data_source_id": DAILY_LOG_DATA_SOURCE_ID}, "properties": properties}
        r = requests.post(url, headers=_notion_headers(), json=payload, timeout=30)
    r.raise_for_status()


def fetch_garmin_data(date_str: str | None = None) -> bool:
    """Refresh Garmin-derived fields in Notion for `date_str` (default:
    today). Invokes the existing garmin_workout_sync.py as a subprocess
    (does not reimplement or import its internals) to refresh today's
    Workouts row, then separately pulls steps/sleep for the requested date
    straight from Garmin and upserts them into Daily Log - the table
    Personal Trainer actually reads from.

    Returns True if the sync ran without a hard failure.
    """
    result = subprocess.run([sys.executable, str(GARMIN_SYNC_SCRIPT)], cwd=REPO_ROOT)
    if result.returncode != 0:
        return False

    date_str = date_str or datetime.date.today().isoformat()
    try:
        from garminconnect import Garmin

        client = Garmin(os.environ["GARMIN_EMAIL"], os.environ["GARMIN_PASSWORD"])
        client.login()
        stats = client.get_stats(date_str) or {}
        sleep = client.get_sleep_data(date_str) or {}
        sleep_seconds = (sleep.get("dailySleepDTO") or {}).get("sleepTimeSeconds")

        updates = {}
        if stats.get("totalSteps") is not None:
            updates["steps"] = stats["totalSteps"]
        if sleep_seconds:
            updates["sleep_hours"] = round(sleep_seconds / 3600, 1)
        if updates:
            write_daily_log_field(date_str, updates)
    except Exception:
        # The Workouts DB refresh above already succeeded; a miss here
        # (e.g. Garmin has no sleep data for the date) shouldn't fail the
        # whole tool call.
        pass
    return True
