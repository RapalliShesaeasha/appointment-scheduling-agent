import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_root():
    r = client.get("/")
    assert r.status_code == 200

def test_availability_endpoint():
    r = client.get("/api/calendly/availability", params={"date": "2024-01-16", "appointment_type": "consultation"})
    assert r.status_code == 200
    data = r.json()
    assert "available_slots" in data

def test_booking_flow():
    chat = client.post("/api/chat", json={"message": "I need to see the doctor"})
    assert chat.status_code == 200
    session_id = chat.json().get("session_id")
    r2 = client.post("/api/chat", json={"message": "I've been having headaches", "session_id": session_id})
    assert r2.status_code == 200
    r3 = client.post("/api/chat", json={"message": "consultation", "session_id": session_id})
    assert r3.status_code == 200
    r4 = client.post("/api/chat", json={"message": "2024-01-16", "session_id": session_id})
    assert r4.status_code == 200
