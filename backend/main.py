from fastapi import FastAPI
from backend.api import chat, calendly_integration
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Appointment Scheduling Agent")

app.include_router(chat.router)
app.include_router(calendly_integration.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
def read_root():
    return {"message": "Appointment Scheduling Agent is running."}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
