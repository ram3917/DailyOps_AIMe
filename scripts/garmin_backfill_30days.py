import os
import datetime
from garminconnect import Garmin

from garmin_workout_sync import map_activity_type, push_to_notion

BACKFILL_DAYS = 30


def get_activity_for_date(client, date_str):
    activities = client.get_activities_by_date(date_str, date_str)
    if not activities:
        return None
    # Take the primary activity of the day; adjust if you log multiple
    a = activities[0]
    steps_data = client.get_steps_data(date_str)
    return {
        "date": date_str,
        "activity_type": a.get("activityType", {}).get("typeKey", "Other"),
        "duration_min": round(a.get("duration", 0) / 60, 1),
        "calories": a.get("calories"),
        "avg_hr": a.get("averageHR"),
        "max_hr": a.get("maxHR"),
        "training_load": a.get("activityTrainingLoad"),
        "steps": steps_data[0].get("totalSteps") if steps_data else None,
    }


def backfill():
    client = Garmin(os.environ["GARMIN_EMAIL"], os.environ["GARMIN_PASSWORD"])
    client.login()

    today = datetime.date.today()
    for offset in range(BACKFILL_DAYS):
        date_str = (today - datetime.timedelta(days=offset)).isoformat()
        data = get_activity_for_date(client, date_str)
        if data:
            push_to_notion(data)
            print(f"Synced {date_str}: {data['activity_type']}")
        else:
            print(f"No Garmin activity found for {date_str} — skipping.")


if __name__ == "__main__":
    backfill()
