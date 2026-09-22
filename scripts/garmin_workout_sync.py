import os
import datetime
from garminconnect import Garmin
import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
WORKOUTS_DB_ID = "ef08f42b-275d-4d44-89ac-9302d40cb184"  # Workouts data source ID

def get_activity_data(client, date_str):
    activities = client.get_activities_by_date(date_str, date_str)
    # Take the primary activity of the day; adjust if you log multiple
    a = activities[0] if activities else None

    # Day-level stats (steps, resting HR, body battery, stress) are fetched
    # every day regardless of whether a workout was logged, so rest days
    # still get a row instead of being skipped entirely.
    # get_stats() is the daily summary and has totalSteps; get_steps_data()
    # is the intraday steps chart (per-interval, no daily total) so it's
    # not usable here.
    stats = client.get_stats(date_str) or {}
    stress = client.get_stress_data(date_str) or {}
    day_metrics = {
        "steps": stats.get("totalSteps"),
        "resting_hr": stats.get("restingHeartRate"),
        "body_battery": stats.get("bodyBatteryMostRecentValue"),
        "stress": stress.get("avgStressLevel"),
    }

    if a is None:
        return {
            "date": date_str,
            "activity_type": "rest",
            "duration_min": 0,
            "calories": None,
            "avg_hr": None,
            "max_hr": None,
            "training_load": None,
            "distance_km": None,
            "elevation_gain_m": None,
            **day_metrics,
        }

    distance = a.get("distance")
    return {
        "date": date_str,
        "activity_type": a.get("activityType", {}).get("typeKey", "Other"),
        "duration_min": round(a.get("duration", 0) / 60, 1),
        "calories": a.get("calories"),
        "avg_hr": a.get("averageHR"),
        "max_hr": a.get("maxHR"),
        "training_load": a.get("activityTrainingLoad"),
        "distance_km": round(distance / 1000, 2) if distance else None,
        "elevation_gain_m": a.get("elevationGain"),
        **day_metrics,
    }


def get_today_activity():
    client = Garmin(os.environ["GARMIN_EMAIL"], os.environ["GARMIN_PASSWORD"])
    client.login()
    today = datetime.date.today().isoformat()
    return get_activity_data(client, today)

def map_activity_type(garmin_type):
    mapping = {
        "strength_training": "Strength",
        "running": "Cardio",
        "cycling": "Cardio",
        "rest": "Rest",
    }
    return mapping.get(garmin_type, "Mixed")

def push_to_notion(data):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    payload = {
        "parent": {"data_source_id": WORKOUTS_DB_ID},
        "properties": {
            "Session": {"title": [{"text": {"content": data["date"]}}]},
            "Date": {"date": {"start": data["date"]}},
            "Activity Type": {"select": {"name": map_activity_type(data["activity_type"])}},
            "Duration (min)": {"number": data["duration_min"]},
            "Calories": {"number": data["calories"]},
            "Avg HR": {"number": data["avg_hr"]},
            "Max HR": {"number": data["max_hr"]},
            "Training Load": {"number": data["training_load"]},
            "Steps": {"number": data["steps"]},
            "Distance (km)": {"number": data["distance_km"]},
            "Elevation Gain (m)": {"number": data["elevation_gain_m"]},
            "Resting HR": {"number": data["resting_hr"]},
            "Body Battery": {"number": data["body_battery"]},
            "Stress": {"number": data["stress"]},
        },
    }
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()

if __name__ == "__main__":
    push_to_notion(get_today_activity())
