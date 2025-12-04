import random
import string

def book_slot(payload: dict) -> dict:
    """
    Mock booking logic per PDF.
    Generates booking_id & confirmation_code locally.
    """

    booking_id = f"APPT-{payload['date'].replace('-', '')}-{random.randint(100,999)}"
    confirmation = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    return {
        "booking_id": booking_id,
        "status": "confirmed",
        "confirmation_code": confirmation,
        "details": payload
    }
