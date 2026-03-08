from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
import uvicorn
import os
import time
from sqlalchemy.exc import OperationalError

import models
from database import engine, get_db
from dependencies import require_role
from controllers.user_role_controller import router as user_role_router
from controllers.user_account_controller import router as user_account_router
from controllers.user_details_controller import router as user_details_router
from controllers.user_preferences_controller import router as user_preferences_router
from controllers.action_history_controller import router as action_history_router
from controllers.app_feedback_controller import router as app_feedback_router
from controllers.blacklist_request_controller import router as blacklist_request_router
from controllers.url_rules_controller import router as url_rules_router
from controllers.scan_history_controller import router as scan_history_router
from controllers.scan_feedback_controller import router as scan_feedback_router
from controllers.auth_controller import router as auth_router

# Tells FastAPI to try connecting 5 times, waiting 5 seconds between each try.
retries = 5
while retries > 0:
    try:
        models.Base.metadata.create_all(bind=engine)
        print("Successfully connected to the database and created tables!")
        break
    except OperationalError:
        print(f"Database not ready yet. Retrying in 5 seconds... ({retries} attempts left)")
        time.sleep(5)
        retries -= 1

if retries == 0:
    print("FATAL ERROR: Could not connect to the database after 5 attempts.")

app = FastAPI(title="LinksLens API")

# Connect the UserRole Controller to the main app
app.include_router(user_role_router)
app.include_router(user_account_router)
app.include_router(user_details_router)
app.include_router(user_preferences_router)
app.include_router(action_history_router)
app.include_router(app_feedback_router)
app.include_router(blacklist_request_router)
app.include_router(url_rules_router)
app.include_router(scan_history_router)
app.include_router(scan_feedback_router)
app.include_router(auth_router)

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

@app.get("/api/health")
def system_health(db: Session = Depends(get_db), _: dict = Depends(require_role(1))):
    """System health dashboard data — Admin only."""
    # Database connectivity check
    try:
        db.execute(text("SELECT 1"))
        db_status = "Connected"
    except Exception:
        db_status = "Disconnected"

    total_users = db.query(models.UserAccount).count()
    active_users = db.query(models.UserAccount).filter(models.UserAccount.IsActive == True).count()
    total_scans = db.query(models.ScanHistory).count()
    pending_blacklist = db.query(models.BlacklistRequest).filter(
        models.BlacklistRequest.Status == models.RequestStatus.PENDING
    ).count()
    unresolved_scan_feedback = db.query(models.ScanFeedback).filter(
        models.ScanFeedback.IsResolved == False
    ).count()
    total_url_rules = db.query(models.URLRules).count()
    total_app_feedback = db.query(models.AppFeedback).count()

    return {
        "database": db_status,
        "total_users": total_users,
        "active_users": active_users,
        "total_scans": total_scans,
        "pending_blacklist_requests": pending_blacklist,
        "unresolved_scan_feedback": unresolved_scan_feedback,
        "total_url_rules": total_url_rules,
        "total_app_feedback": total_app_feedback,
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