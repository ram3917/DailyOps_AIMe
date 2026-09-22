import os
import datetime
from garminconnect import Garmin
import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
WORKOUTS_DB_ID = "ef08f42b-275d-4d44-89ac-9302d40cb184"  # Workouts data source ID

def get_today_activity():
    client = Garmin(os.environ["GARMIN_EMAIL"], os.environ["GARMIN_PASSWORD"])
    client.login()
    today = datetime.date.today().isoformat()
    activities = client.get_activities_by_date(today, today)
    if not activities:
        return None
    # Take the primary activity of the day; adjust if you log multiple
    a = activities[0]
    return {
        "date": today,
        "activity_type": a.get("activityType", {}).get("typeKey", "Other"),
        "duration_min": round(a.get("duration", 0) / 60, 1),
        "calories": a.get("calories"),
        "avg_hr": a.get("averageHR"),
        "max_hr": a.get("maxHR"),
        "training_load": a.get("activityTrainingLoad"),
        "steps": client.get_steps_data(today)[0].get("totalSteps") if client.get_steps_data(today) else None,
    }

def map_activity_type(garmin_type):
    mapping = {"strength_training": "Strength", "running": "Cardio", "cycling": "Cardio"}
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
        },
    }
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()

if __name__ == "__main__":
    data = get_today_activity()
    if data:
        push_to_notion(data)
    else:
        print("No Garmin activity found for today — skipping Notion write.")
