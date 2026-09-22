import os
import datetime
from garminconnect import Garmin

from garmin_workout_sync import get_activity_data, push_to_notion

BACKFILL_DAYS = 30


def backfill():
    client = Garmin(os.environ["GARMIN_EMAIL"], os.environ["GARMIN_PASSWORD"])
    client.login()

    today = datetime.date.today()
    for offset in range(BACKFILL_DAYS):
        date_str = (today - datetime.timedelta(days=offset)).isoformat()
        data = get_activity_data(client, date_str)
        push_to_notion(data)
        print(f"Synced {date_str}: {data['activity_type']}")


if __name__ == "__main__":
    backfill()
