from fastapi import APIRouter
from ..models.schemas import ChatRequest
from ..agent.scheduling_agent import handle_message
import uuid

router = APIRouter(prefix="/api", tags=["chat"])

@router.post("/chat")
def chat_endpoint(req: ChatRequest):
    try:
        session_id = req.session_id or str(uuid.uuid4())
        result = handle_message(session_id, req.message)
        return {"session_id": session_id, "result": result}
    except Exception as e:
        print("Error in handle_message:", e)  # <-- see the real error in backend terminal
        return {
            "session_id": req.session_id,
            "result": {"response": "Server error occurred.", "type": "text"}
        }
