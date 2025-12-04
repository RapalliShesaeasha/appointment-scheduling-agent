from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import json
from pathlib import Path
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/calendly", tags=["calendly"])

SCHEDULE_FILE = Path("data/doctor_schedule.json")

def load_schedule():
    with open(SCHEDULE_FILE, "r") as f:
        return json.load(f)

@router.get("/availability")
def get_availability(date: str = Query(...), appointment_type: str = Query(...)):
    schedule = load_schedule()
    appt_types = schedule.get("appointment_types", {})
    if appointment_type not in appt_types:
        raise HTTPException(status_code=400, detail="Unknown appointment type")
    duration_min = appt_types[appointment_type]
    existing = [a for a in schedule.get("existing_appointments", []) if a["date"] == date]
    start_hour = 9
    end_hour = 17
    slots = []
    t = datetime.strptime(f"{date} {start_hour:02d}:00", "%Y-%m-%d %H:%M")
    end_dt = datetime.strptime(f"{date} {end_hour:02d}:00", "%Y-%m-%d %H:%M")
    while t + timedelta(minutes=duration_min) <= end_dt:
        start_str = t.strftime("%H:%M")
        end_str = (t + timedelta(minutes=duration_min)).strftime("%H:%M")
        occupied = False
        for ex in existing:
            ex_start = datetime.strptime(f"{ex['date']} {ex['start_time']}", "%Y-%m-%d %H:%M")
            ex_end = datetime.strptime(f"{ex['date']} {ex['end_time']}", "%Y-%m-%d %H:%M")
            slot_start = datetime.strptime(f"{date} {start_str}", "%Y-%m-%d %H:%M")
            slot_end = datetime.strptime(f"{date} {end_str}", "%Y-%m-%d %H:%M")
            if not (slot_end <= ex_start or slot_start >= ex_end):
                occupied = True
                break
        slots.append({"start_time": start_str, "end_time": end_str, "available": not occupied})
        t += timedelta(minutes=duration_min)
    return {"date": date, "available_slots": slots}

@router.post("/book")
def book_appointment(payload: dict):
    schedule = load_schedule()
    body = payload
    appt_type = body.get("appointment_type")
    date = body.get("date")
    start_time = body.get("start_time")
    patient = body.get("patient")
    reason = body.get("reason", "")
    if not (appt_type and date and start_time and patient):
        raise HTTPException(status_code=400, detail="Missing required fields")
    duration = schedule["appointment_types"].get(appt_type)
    if duration is None:
        raise HTTPException(status_code=400, detail="Unknown appointment type")
    start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
    end_dt = start_dt + timedelta(minutes=duration)
    for ex in schedule.get("existing_appointments", []):
        ex_start = datetime.strptime(f"{ex['date']} {ex['start_time']}", "%Y-%m-%d %H:%M")
        ex_end = datetime.strptime(f"{ex['date']} {ex['end_time']}", "%Y-%m-%d %H:%M")
        if not (end_dt <= ex_start or start_dt >= ex_end):
            raise HTTPException(status_code=409, detail="Slot already booked")
    booking_id = f"APPT-{len(schedule.get('existing_appointments', [])) + 1:03d}"
    new_appt = {
        "booking_id": booking_id,
        "date": date,
        "start_time": start_time,
        "end_time": end_dt.strftime("%H:%M"),
        "appointment_type": appt_type,
        "patient": patient,
        "reason": reason,
        "status": "confirmed"
    }
    schedule.setdefault("existing_appointments", []).append(new_appt)
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(schedule, f, indent=2)
    return {
        "booking_id": booking_id,
        "status": "confirmed",
        "confirmation_code": "MOCKCONF" + booking_id[-3:],
        "details": new_appt
    }
