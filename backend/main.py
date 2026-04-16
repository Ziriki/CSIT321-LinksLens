from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from sqlalchemy.orm import Session
from sqlalchemy import text, func
import requests
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
from controllers.url_scan_controller import router as url_scan_router

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

# Allow the static marketing site to call the password reset endpoints from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://linkslens.com"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

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
app.include_router(url_scan_router)

@app.get("/")
def read_root():
    return {
        "status": "Online",
        "service": "LinkLens Backend API",
        "documentation": "/docs"  # FastAPI automatically generates this
    }

def _check_component(name: str, check_fn: Callable[[], None]) -> dict:
    try:
        check_fn()
        return {"name": name, "status": "operational"}
    except Exception as e:
        return {"name": name, "status": "outage", "detail": str(e)}


@app.get("/api/health")
def system_health(db: Session = Depends(get_db), _: dict = Depends(require_role(1))):
    """System health dashboard — Admin only."""

    # --- Component checks (run in parallel to minimise latency) ---

    def check_database():
        db.execute(text("SELECT 1"))

    def check_gsb():
        gsb_key = os.getenv("GOOGLE_SAFE_BROWSING_API_KEY")
        if not gsb_key:
            raise ValueError("API key not configured")
        resp = requests.post(
            "https://safebrowsing.googleapis.com/v4/threatMatches:find",
            params={"key": gsb_key},
            json={
                "client": {"clientId": "linkslens-health", "clientVersion": "1.0"},
                "threatInfo": {
                    "threatTypes": ["MALWARE"],
                    "platformTypes": ["ANY_PLATFORM"],
                    "threatEntryTypes": ["URL"],
                    "threatEntries": [{"url": "https://example.com"}],
                },
            },
            timeout=5,
        )
        if resp.status_code != 200:
            raise ValueError(f"HTTP {resp.status_code}")

    def check_urlscan():
        urlscan_key = os.getenv("URLSCAN_API_KEY")
        if not urlscan_key:
            raise ValueError("API key not configured")
        resp = requests.get(
            "https://urlscan.io/api/v1/search/?q=domain:example.com&size=1",
            headers={"API-Key": urlscan_key},
            timeout=5,
        )
        if resp.status_code != 200:
            raise ValueError(f"HTTP {resp.status_code}")

    def check_resend():
        resend_key = os.getenv("RESEND_KEY")
        if not resend_key:
            raise ValueError("API key not configured")
        resp = requests.get(
            "https://api.resend.com/domains",
            headers={"Authorization": f"Bearer {resend_key}"},
            timeout=5,
        )
        if resp.status_code != 200:
            raise ValueError(f"HTTP {resp.status_code}")

    checks = [
        ("Database",             check_database),
        ("Google Safe Browsing", check_gsb),
        ("urlscan.io",           check_urlscan),
        ("Email (Resend)",       check_resend),
    ]
    with ThreadPoolExecutor() as executor:
        components = list(executor.map(lambda c: _check_component(c[0], c[1]), checks))

    overall = "outage" if any(c["status"] == "outage" for c in components) else "operational"

    # --- Operational metrics (work queues) ---

    pending_blacklist_requests = db.query(models.BlacklistRequest).filter(
        models.BlacklistRequest.Status == models.RequestStatus.PENDING
    ).count()

    unresolved_scan_feedback = db.query(models.ScanFeedback).filter(
        models.ScanFeedback.IsResolved == False
    ).count()

    unread_app_feedback = db.query(models.AppFeedback).count()

    scans_today = db.query(models.ScanHistory).filter(
        func.date(models.ScanHistory.ScannedAt) == func.current_date()
    ).count()

    url_rule_counts = dict(
        db.query(models.URLRules.ListType, func.count(models.URLRules.RuleID))
        .group_by(models.URLRules.ListType)
        .all()
    )

    return {
        "overall_status": overall,
        "components": components,
        "pending_work": {
            "blacklist_requests_pending_review": pending_blacklist_requests,
            "scan_feedback_pending_review": unresolved_scan_feedback,
            "app_feedback_unreviewed": unread_app_feedback,
        },
        "activity": {
            "scans_today": scans_today,
        },
        "url_rules": {
            "blacklisted_domains": url_rule_counts.get(models.ListTypeEnum.BLACKLIST, 0),
            "whitelisted_domains": url_rule_counts.get(models.ListTypeEnum.WHITELIST, 0),
        },
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
