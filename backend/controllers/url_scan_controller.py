from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import requests
import time
import os
from dotenv import load_dotenv
from urllib.parse import quote, urlparse

import models
from database import get_db
from dependencies import get_current_user

load_dotenv()

router = APIRouter(
    prefix="/scan",
    tags=["URL Scanner"]
)

URLSCAN_API_KEY = os.getenv("URLSCAN_API_KEY")
if not URLSCAN_API_KEY:
    raise ValueError("FATAL ERROR: URLSCAN_API_KEY environment variable is not set!")

URLSCAN_SUBMIT_URL = "https://urlscan.io/api/v1/scan/"
URLSCAN_RESULT_URL = "https://urlscan.io/api/v1/result/{uuid}/"
URLSCAN_SCREENSHOT_URL = "https://urlscan.io/screenshots/{uuid}.png"

# Polling configuration: wait 10s before first poll, then every 5s, up to 12 attempts (70s total)
INITIAL_WAIT_SECONDS = 10
POLL_INTERVAL_SECONDS = 5
MAX_POLL_ATTEMPTS = 12


class ScanRequest(BaseModel):
    url: str


#########################################################
# Helper: Submit URL to urlscan.io
#########################################################
def submit_scan(url: str) -> dict:

    # Sanitize the url of harmful characters
    safe_url = quote(url, safe='/:?=&')
    headers = {
        "API-Key": URLSCAN_API_KEY,
        "Content-Type": "application/json"
    }
    # Visibility is set to public as the quota for non public calls is too small to be usable
    payload = {
        "url": safe_url,
        "visibility": "public"
    }

    response = requests.post(URLSCAN_SUBMIT_URL, headers=headers, json=payload, timeout=15)

    if response.status_code == 400:
        detail = response.json().get("message", "Bad request")
        raise HTTPException(status_code=400, detail=f"urlscan.io rejected the URL: {detail}")
    if response.status_code == 401:
        raise HTTPException(status_code=502, detail="urlscan.io API key is invalid or missing.")
    if response.status_code == 429:
        raise HTTPException(status_code=429, detail="urlscan.io rate limit reached. Please try again later.")
    if response.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=f"urlscan.io submission failed (HTTP {response.status_code}).")

    return response.json()


#########################################################
# Helper: Poll urlscan.io until the result is ready
#########################################################
def poll_result(uuid: str) -> dict:
    result_url = URLSCAN_RESULT_URL.format(uuid=uuid)

    # urlscan.io recommends waiting at least 10 seconds before the first poll
    time.sleep(INITIAL_WAIT_SECONDS)

    for attempt in range(MAX_POLL_ATTEMPTS):
        response = requests.get(result_url, timeout=15)

        if response.status_code == 200:
            return response.json()

        if response.status_code == 404:
            # Scan is still in progress — keep polling
            if attempt < MAX_POLL_ATTEMPTS - 1:
                time.sleep(POLL_INTERVAL_SECONDS)
            continue

        raise HTTPException(
            status_code=502,
            detail=f"Unexpected response from urlscan.io while polling (HTTP {response.status_code})."
        )

    raise HTTPException(
        status_code=504,
        detail="Scan timed out. urlscan.io did not return results within the allowed time."
    )


#########################################################
# Helper: Map urlscan.io result to a structured response
#########################################################
def process_result(uuid: str, raw_result: dict) -> dict:
    page = raw_result.get("page", {})
    verdicts = raw_result.get("verdicts", {})
    overall = verdicts.get("overall", {})

    is_malicious = overall.get("malicious", False)
    score = overall.get("score", 0)

    if is_malicious:
        status_indicator = "MALICIOUS"
    elif score >= 50:
        status_indicator = "SUSPICIOUS"
    else:
        status_indicator = "SAFE"

    initial_url = page.get("url", "")
    redirect_url = page.get("redirected")

    return {
        "uuid": uuid,
        "status": status_indicator,
        "score": score,
        "initial_url": initial_url,
        "redirect_url": redirect_url if redirect_url and redirect_url != initial_url else None,
        "server_location": page.get("country"),
        "ip_address": page.get("ip"),
        "screenshot_url": URLSCAN_SCREENSHOT_URL.format(uuid=uuid),
        "result_url": f"https://urlscan.io/result/{uuid}/",
        "brands": overall.get("brands", []),
        "tags": overall.get("tags", []),
    }


#########################################################
# POST /scan — Submit a URL and return its scan results
#########################################################
#I will include a option to select quick or detailed later
@router.post("")
def scan_url(request: ScanRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Submit a URL to urlscan.io, wait for the scan to complete, and return the results."""
    # 1. Submit the URL to urlscan.io
    submission = submit_scan(request.url)
    uuid = submission.get("uuid")

    if not uuid:
        raise HTTPException(status_code=502, detail="urlscan.io did not return a scan UUID.")

    # 2. Poll until the result is ready
    raw_result = poll_result(uuid)

    # 3. Process the structured result
    result = process_result(uuid, raw_result)

    # 4. Save to ScanHistory
    scan_record = models.ScanHistory(
        UserID=current_user["user_id"],
        InitialURL=result["initial_url"],
        RedirectURL=result["redirect_url"],
        StatusIndicator=models.ScanStatusEnum(result["status"]),
        ServerLocation=result["server_location"],
        ScreenshotURL=result["screenshot_url"],
    )
    db.add(scan_record)
    db.commit()
    db.refresh(scan_record)

    # 5. If MALICIOUS, also raise a BlacklistRequest
    # if result["status"] == "MALICIOUS":
    #     domain = urlparse(result["initial_url"]).netloc
    #     blacklist_record = models.BlacklistRequest(
    #         UserID=current_user["user_id"],
    #         URLDomain=domain,
    #         Status=models.RequestStatus.PENDING,
    #     )
    #     db.add(blacklist_record)
    #     db.commit()

    # Returns the full urlscan result, omit the uncessary fields when needed
    return {
        "scan_id": scan_record.ScanID,
        "user_id": scan_record.UserID,
        "uuid": result["uuid"],
        "initial_url": scan_record.InitialURL,
        "redirect_url": scan_record.RedirectURL,
        "status_indicator": scan_record.StatusIndicator,
        "score": result["score"],
        "server_location": scan_record.ServerLocation,
        "ip_address": result["ip_address"],
        "screenshot_url": scan_record.ScreenshotURL,
        "brands": result["brands"],
        "tags": result["tags"],
        "result_url": result["result_url"],
        "scanned_at": scan_record.ScannedAt,
    }
