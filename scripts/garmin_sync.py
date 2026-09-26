"""Fetch Garmin data and upsert it into the local trainer DB.

Run: python scripts/garmin_sync.py [--days N]   (default: 1 = today only)
Set up a cron job to run this daily; the bot only reads from the DB, it
never calls Garmin itself.
"""
import argparse
import datetime
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from garminconnect import Garmin

from trainer.db import upsert_daily_log


def fetch_day(client: Garmin, date_str: str) -> dict:
    activities = client.get_activities_by_date(date_str, date_str)
    activity = activities[0] if activities else None
    stats = client.get_stats(date_str) or {}
    stress = client.get_stress_data(date_str) or {}
    sleep = client.get_sleep_data(date_str) or {}
    sleep_seconds = (sleep.get("dailySleepDTO") or {}).get("sleepTimeSeconds")

    weight_kg = None
    try:
        body_comp = client.get_body_composition(date_str, date_str) or {}
        weight_grams = (body_comp.get("totalAverage") or {}).get("weight")
        if weight_grams:
            weight_kg = round(weight_grams / 1000, 1)
    except Exception:
        pass  # no smart-scale data for this day - fine, weight can come from the bot instead

    distance = (activity or {}).get("distance")
    return {
        "date": date_str,
        "steps": stats.get("totalSteps"),
        "resting_hr": stats.get("restingHeartRate"),
        "body_battery": stats.get("bodyBatteryMostRecentValue"),
        "stress": stress.get("avgStressLevel"),
        "sleep_hours": round(sleep_seconds / 3600, 1) if sleep_seconds else None,
        "weight_kg": weight_kg,
        "activity_type": (activity or {}).get("activityType", {}).get("typeKey", "rest"),
        "duration_min": round((activity or {}).get("duration", 0) / 60, 1) if activity else 0,
        "calories": (activity or {}).get("calories"),
        "avg_hr": (activity or {}).get("averageHR"),
        "max_hr": (activity or {}).get("maxHR"),
        "training_load": (activity or {}).get("activityTrainingLoad"),
        "distance_km": round(distance / 1000, 2) if distance else None,
        "elevation_gain_m": (activity or {}).get("elevationGain"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=1, help="How many days back to sync (1 = today only)")
    args = parser.parse_args()

    client = Garmin(os.environ["GARMIN_EMAIL"], os.environ["GARMIN_PASSWORD"])
    client.login()

    today = datetime.date.today()
    for offset in range(args.days):
        date_str = (today - datetime.timedelta(days=offset)).isoformat()
        row = fetch_day(client, date_str)
        # Drop fields Garmin had no data for, so re-running a sync never
        # overwrites a value (e.g. a weight the user texted the bot)
        # with null just because today's Garmin call came back empty.
        row = {k: v for k, v in row.items() if v is not None or k == "date"}
        upsert_daily_log(row)
        print(f"Synced {date_str}: {row.get('activity_type')}, steps={row.get('steps')}")


if __name__ == "__main__":
    main()
