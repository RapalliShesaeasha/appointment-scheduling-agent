from typing import Dict
from datetime import datetime, timedelta
from pathlib import Path
import json

from ..tools.availability_tool import get_availability
from ..tools.booking_tool import book_slot
from ..rag.faq_rag import answer_faq, initialize_faq_index

# load FAQ DB
try:
    initialize_faq_index()
except:
    pass

SESSIONS: Dict[str, Dict] = {}

FAQ_KEYWORDS = [
    "insurance", "hours", "working hours", "clinic hours", "location",
    "where are you", "parking", "cancel", "cancellation", "prepare"
]

# If you want to override the mock "today", set this path (relative)
_SCHEDULE_PATH = Path("data/doctor_schedule.json")


# ---------------------------------------------------------
# Helpers: mock-today detection (useful for PDF/mocked data)
# ---------------------------------------------------------
def get_mock_today() -> datetime.date:
    """
    Try to pick a sensible 'mock' today from the schedule file.
    We choose the earliest date appearing in existing_appointments if available
    (this makes 'today' align with the dates in the provided mock JSON).
    Falls back to real today if file missing or malformed.
    """
    try:
        if _SCHEDULE_PATH.exists():
            with open(_SCHEDULE_PATH, "r") as f:
                data = json.load(f)
            existing = data.get("existing_appointments", [])
            if existing:
                # pick the earliest date present in the mock data
                dates = []
                for a in existing:
                    try:
                        d = datetime.strptime(a["date"], "%Y-%m-%d").date()
                        dates.append(d)
                    except Exception:
                        continue
                if dates:
                    return min(dates)
    except Exception:
        pass
    return datetime.now().date()


# ---------------------------------------------------------
# FAQ SUPPORT
# ---------------------------------------------------------
def _extract_single_answer(rag_resp):
    return rag_resp["answer"] if rag_resp and "answer" in rag_resp else ""


def _is_faq_question(text: str) -> bool:
    low = text.lower()
    return any(k in low for k in FAQ_KEYWORDS)


def _get_next_question_after_faq(sess):
    """Resume conversation after FAQ answer."""
    state = sess["state"]

    if state == "awaiting_reason":
        return "What brings you in today?"
    if state == "awaiting_appt_type":
        return "Would this be a consultation, followup, physical, or specialist visit?"
    if state == "awaiting_preference":
        return ("Do you have a preferred date or time (e.g., tomorrow afternoon, "
                "next week, or a specific date YYYY-MM-DD)?")
    if state == "awaiting_slot_choice":
        return "Please pick a slot number from the list, or say 'none of these work'."

    return "Shall we continue with your appointment booking?"


# ---------------------------------------------------------
# NATURAL LANGUAGE DATE INTERPRETATION (contains-based)
# ---------------------------------------------------------
def _interpret_preferred_date(text: str) -> str | None:
    """
    Return YYYY-MM-DD string when user mentions a recognizable date phrase.
    Uses the mock 'today' from the schedule file so 'today' matches the mock dataset.
    """
    low = text.lower()
    today_date = get_mock_today()

    if "today" in low:
        return today_date.strftime("%Y-%m-%d")
    if "tomorrow" in low:
        return (today_date + timedelta(days=1)).strftime("%Y-%m-%d")

    # day of week (e.g., "wednesday", "next wednesday")
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, d in enumerate(days):
        if d in low:
            today_dow = today_date.weekday()
            delta = (i - today_dow + 7) % 7
            # if user said e.g. "this wednesday" and it's that same day, keep delta=0
            # but to match natural 'next' we treat delta==0 as delta=7 when "next" present,
            # otherwise keep same-week day.
            if delta == 0 and "next" in low:
                delta = 7
            return (today_date + timedelta(days=delta)).strftime("%Y-%m-%d")

    # explicit yyyy-mm-dd anywhere in text
    import re
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if m:
        return m.group(1)

    return None


def _choose_top_available_slots(avail_response, limit=5):
    slots = [s for s in avail_response.get("available_slots", []) if s.get("available")]
    return slots[:limit]


def _normalize_appointment_type(text: str) -> str | None:
    """Normalize free-text appointment type into expected keys."""
    low = text.lower()
    if "consult" in low:
        return "consultation"
    if "follow" in low:
        return "followup"
    if "physical" in low:
        return "physical"
    if "special" in low:
        return "specialist"
    return None


# ---------------------------------------------------------
# MAIN AGENT LOGIC
# ---------------------------------------------------------
def handle_message(session_id: str, message: str) -> Dict:
    sess = SESSIONS.setdefault(session_id, {"state": "new", "data": {}})
    low = message.lower()

    # -------------------------
    # FAQ check first
    # -------------------------
    if _is_faq_question(message):
        rag = answer_faq(message)
        ans = _extract_single_answer(rag)
        follow = _get_next_question_after_faq(sess)
        return {"type": "faq", "response": f"{ans}\n\n{follow}"}

    # -------------------------
    # NEW SESSION — check if user mentions a date (contains-based)
    # -------------------------
    if sess["state"] == "new":
        # interpret date phrases using mock-today
        date_str = _interpret_preferred_date(message)
        if date_str:
            # default appointment type
            appt_type = "consultation"
            try:
                avail = get_availability(date_str, appt_type)
            except Exception as e:
                return {"type": "error", "response": f"Could not check availability: {str(e)}"}

            available = [s for s in avail["available_slots"] if s["available"]]

            if available:
                top = available[:5]
                sess["data"].update({
                    "appointment_type": appt_type,
                    "preferred": date_str,
                    "suggested_slots": top
                })
                sess["state"] = "awaiting_slot_choice"

                text = "I found these available slots:\n" + "\n".join(
                    f"{i+1}. {s['start_time']} - {s['end_time']}" for i, s in enumerate(top)
                )
                return {"type": "options", "response": text + "\nPlease pick a slot number."}
            else:
                # fallback for no slots — use next day suggestions per PDF
                try:
                    next_day = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
                    next_avail = get_availability(next_day, appt_type)
                    top_slots = [s for s in next_avail["available_slots"] if s["available"]][:3]
                    times = [s["start_time"] for s in top_slots]
                except Exception:
                    times = []
                # If no times, give a polite fallback message
                if not times:
                    return {
                        "type": "info",
                        "response": (
                            f"Sorry, no slots available on {date_str}. "
                            f"I couldn't find alternatives right now — would you like me to check other dates?"
                        )
                    }

                return {
                    "type": "info",
                    "response": (
                        f"Sorry, no slots available on {date_str}. "
                        f"Here are some options for {next_day}:\n- " + "\n- ".join(times)
                    )
                }

        # no date mentioned → proceed with normal greeting
        sess["state"] = "awaiting_reason"
        return {
            "type": "ask",
            "response": "Hello — I’m here to help you schedule appointments. What brings you in today?"
        }

    # -------------------------------------------
    # CAPTURE REASON
    # -------------------------------------------
    if sess["state"] == "awaiting_reason":
        sess["data"]["reason"] = message
        sess["state"] = "awaiting_appt_type"
        return {
            "type": "ask",
            "response": "Would this be a consultation, followup, physical, or specialist visit?"
        }

    # -------------------------------------------
    # CAPTURE APPOINTMENT TYPE
    # -------------------------------------------
    if sess["state"] == "awaiting_appt_type":
        appt = _normalize_appointment_type(message)
        if not appt:
            return {
                "type": "ask",
                "response": "Please select one of: consultation, followup, physical, specialist."
            }
        sess["data"]["appointment_type"] = appt
        sess["state"] = "awaiting_preference"
        return {
            "type": "ask",
            "response": (
                "Great. When would you like to come in? "
                "You can say things like 'tomorrow afternoon', 'next week', or '2024-01-15'"
            )
        }

    # -------------------------------------------
    # CAPTURE DATE / TIME
    # -------------------------------------------
    if sess["state"] == "awaiting_preference":
        date = _interpret_preferred_date(message)
        if not date:
            return {
                "type": "ask",
                "response": "Could you provide a specific date? (e.g., 2024-01-15)"
            }
        sess["data"]["preferred"] = date
        try:
            avail = get_availability(date, sess["data"]["appointment_type"])
        except Exception as e:
            return {"type": "error", "response": f"Could not fetch availability: {str(e)}"}

        available = [s for s in avail["available_slots"] if s["available"]]

        if not available:
            return {
                "type": "info",
                "response": "No available slots that day. Would you like options for the next few days?"
            }

        top = _choose_top_available_slots(avail, limit=5)
        sess["data"]["suggested_slots"] = top
        sess["state"] = "awaiting_slot_choice"

        text = "I found these available slots:\n" + "\n".join(
            f"{i+1}. {s['start_time']} - {s['end_time']}" for i, s in enumerate(top)
        )
        return {"type": "options", "response": text + "\nPlease pick a slot number."}

    # -------------------------------------------
    # SLOT CHOICE
    # -------------------------------------------
    if sess["state"] == "awaiting_slot_choice":
        try:
            idx = int(message.strip()) - 1
            slots = sess["data"]["suggested_slots"]
            if idx < 0 or idx >= len(slots):
                return {"type": "ask", "response": "Please choose a valid slot number."}

            sess["data"]["chosen_slot"] = slots[idx]
            sess["state"] = "awaiting_patient_info"
            return {
                "type": "ask",
                "response": (
                    "Great! Before I confirm, please provide:\n"
                    "- Full name\n- Email\n- Phone\n(Format: Name, email, phone)"
                )
            }

        except:
            return {"type": "ask", "response": "Please reply with the slot number."}

    # -------------------------------------------
    # PATIENT INFO → FINAL BOOKING
    # -------------------------------------------
    if sess["state"] == "awaiting_patient_info":
        parts = [p.strip() for p in message.split(",")]
        if len(parts) < 3:
            return {"type": "ask", "response": "Please use: Name, email, phone"}

        name, email, phone = parts
        payload = {
            "appointment_type": sess["data"]["appointment_type"],
            "date": sess["data"]["preferred"],
            "start_time": sess["data"]["chosen_slot"]["start_time"],
            "patient": {"name": name, "email": email, "phone": phone},
            "reason": sess["data"]["reason"]
        }
        resp = book_slot(payload)

        sess["state"] = "booked"
        sess["data"]["booking"] = resp

        return {
            "type": "confirmation",
            "response": (
                f"All set! Your appointment is confirmed.\n"
                f"Booking ID: {resp['booking_id']}\n"
                f"Confirmation Code: {resp['confirmation_code']}"
            )
        }

    # -------------------------------------------
    # DEFAULT
    # -------------------------------------------
    return {"type": "ask", "response": "How can I help?"}
