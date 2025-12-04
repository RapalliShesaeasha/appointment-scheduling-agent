from pydantic import BaseModel, EmailStr
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class AvailabilityQuery(BaseModel):
    date: str
    appointment_type: str

class PatientInfo(BaseModel):
    name: str
    email: EmailStr
    phone: str

class BookingRequest(BaseModel):
    appointment_type: str
    date: str
    start_time: str
    patient: PatientInfo
    reason: Optional[str] = ""
