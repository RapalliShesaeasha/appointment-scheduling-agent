from pathlib import Path
import json
from datetime import datetime, timedelta

SCHEDULE_FILE = Path("data/doctor_schedule.json")


def get_availability(date: str, appointment_type: str):
    """
    Reads availability from local doctor_schedule.json as required in the PDF.
    No external API calls.
    """

    with open(SCHEDULE_FILE, "r") as f:
        data = json.load(f)

    appt_types = data.get("appointment_types", {})
    duration = appt_types.get(appointment_type)

    if not duration:
        raise ValueError("Unknown appointment type")

    existing = [
        appt for appt in data.get("existing_appointments", [])
        if appt["date"] == date
    ]

    # Working hours
    start_h = 9
    end_h = 17

    t = datetime.strptime(f"{date} 09:00", "%Y-%m-%d %H:%M")
    end_t = datetime.strptime(f"{date} 17:00", "%Y-%m-%d %H:%M")

    slots = []

    while t + timedelta(minutes=duration) <= end_t:
        start_str = t.strftime("%H:%M")
        end_str = (t + timedelta(minutes=duration)).strftime("%H:%M")

        conflict = False
        for appt in existing:
            ap_s = datetime.strptime(f"{appt['date']} {appt['start_time']}", "%Y-%m-%d %H:%M")
            ap_e = datetime.strptime(f"{appt['date']} {appt['end_time']}", "%Y-%m-%d %H:%M")
            slot_s = t
            slot_e = t + timedelta(minutes=duration)

            if not (slot_e <= ap_s or slot_s >= ap_e):
                conflict = True
                break

        slots.append({
            "start_time": start_str,
            "end_time": end_str,
            "available": not conflict
        })

        t += timedelta(minutes=duration)

    return {
        "date": date,
        "available_slots": slots
    }
