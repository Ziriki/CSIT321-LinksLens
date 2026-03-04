from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os

import models
from database import engine
from controllers.user_role_controller import router as user_role_router
from controllers.user_account_controller import router as user_account_router
from controllers.user_details_controller import router as user_details_router
from controllers.user_preferences_controller import router as user_preferences_router

# This line checks MySQL and creates the UserRole table if it doesn't exist yet!
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="LinksLens API")

# Connect the UserRole Controller to the main app
app.include_router(user_role_router)
app.include_router(user_account_router)
app.include_router(user_details_router)
app.include_router(user_preferences_router)

# Data model for the mobile app to send us
class ScanRequest(BaseModel):
    url: str

@app.get("/")
def read_root():
    return {
        "status": "Online",
        "service": "LinkLens Backend API",
        "documentation": "/docs"  # FastAPI automatically generates this
    }

@app.post("/scan")
def scan_website(request: ScanRequest):
    """
    This is the endpoint your React Native App will hit.
    For now, it returns a fake result. Later, we add Playwright here.
    """
    print(f"Received scan request for: {request.url}")
    
    # Mock logic (Replace with real scanner later)
    if "phishing" in request.url:
        return {
            "url": request.url,
            "safety_score": 10,
            "verdict": "DANGEROUS",
            "threats": ["Suspicious Domain", "Hidden Iframes"]
        }
    else:
        return {
            "url": request.url,
            "safety_score": 95,
            "verdict": "SAFE",
            "threats": []
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)