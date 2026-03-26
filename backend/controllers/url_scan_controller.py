from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from typing import Union
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

GSB_API_KEY = os.getenv("GOOGLE_SAFE_BROWSING_API_KEY")
if not GSB_API_KEY:
    raise ValueError("FATAL ERROR: GOOGLE_SAFE_BROWSING_API_KEY environment variable is not set!")

# urlscan.io endpoints
URLSCAN_SUBMIT_URL = "https://urlscan.io/api/v1/scan/"
URLSCAN_RESULT_URL = "https://urlscan.io/api/v1/result/{uuid}/"
URLSCAN_SCREENSHOT_URL = "https://urlscan.io/screenshots/{uuid}.png"

# Google Safe Browsing v5alpha1 endpoint
GSB_LOOKUP_URL = "https://safebrowsing.googleapis.com/v5alpha1/urls:search"

# Polling configuration: wait 10s before first poll, then every 5s, up to 12 attempts (70s total)
INITIAL_WAIT_SECONDS = 10
POLL_INTERVAL_SECONDS = 5
MAX_POLL_ATTEMPTS = 12

# GSB threat type → LinksLens status mapping
_MALICIOUS_THREATS = {"MALWARE", "SOCIAL_ENGINEERING"}
_SUSPICIOUS_THREATS = {"UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"}

# Severity order used when merging two verdicts
_STATUS_SEVERITY = {"SAFE": 0, "SUSPICIOUS": 1, "MALICIOUS": 2}


class ScanRequest(BaseModel):
    urls: Union[str, list[str]]

    @field_validator("urls")
    @classmethod
    def normalize_urls(cls, v):
        """Accept a single URL string or a list; always normalise to a list internally."""
        if isinstance(v, str):
            return [v]
        return v


#########################################################
# Helper: Check URLs against Google Safe Browsing v5
#########################################################
def check_google_safe_browsing(urls: list[str]) -> dict[str, dict]:
    """
    Batch-check a list of URLs via the GSB v5alpha1 urls:search endpoint.

    Uses a GET request with the 'urls' parameter repeated for each URL, as required by the API.
    Returns a dict keyed by URL: { flagged, threat_types, gsb_status }.

    On API failure the function does NOT raise — it returns SAFE defaults so the
    urlscan.io pipeline still runs.
    """
    results = {
        url: {"flagged": False, "threat_types": [], "gsb_status": "SAFE"}
        for url in urls
    }

    # v5 uses GET with repeated 'urls' params; list-of-tuples preserves duplicates
    params = [("key", GSB_API_KEY)] + [("urls", url) for url in urls]
    headers = {"Accept": "application/json", "User-Agent": "LinksLens/1.0"}

    delay = 1
    for _ in range(4):
        try:
            response = requests.get(GSB_LOOKUP_URL, params=params, headers=headers, timeout=10)
        except requests.RequestException:
            # Network failure — fall through to urlscan.io only
            return results

        if response.status_code == 429 or response.status_code >= 500:
            # Exponential backoff for rate limits and server errors (cap at 32s)
            time.sleep(delay)
            delay = min(delay * 2, 32)
            continue

        if response.status_code != 200:
            # Non-blocking: other errors should not abort the overall scan
            return results

        # 200 OK — empty body or absent 'threats' key means all URLs are clean
        for threat in response.json().get("threats", []):
            url = threat.get("url", "")
            threat_types = threat.get("threatTypes", [])
            if url not in results:
                continue

            results[url]["flagged"] = True
            results[url]["threat_types"] = threat_types

            # Determine the worst status from the returned threat types
            if any(t in _MALICIOUS_THREATS for t in threat_types):
                results[url]["gsb_status"] = "MALICIOUS"
            elif any(t in _SUSPICIOUS_THREATS for t in threat_types):
                results[url]["gsb_status"] = "SUSPICIOUS"

        return results

    # All retries exhausted — non-blocking, return safe defaults
    return results


#########################################################
# Helper: Submit a single URL to urlscan.io
#########################################################
def submit_scan(url: str) -> dict:
    safe_url = quote(url, safe='/:?=&')
    headers = {
        "API-Key": URLSCAN_API_KEY,
        "Content-Type": "application/json",
    }
    # Visibility is set to public as the quota for non-public calls is too small to be usable
    payload = {"url": safe_url, "visibility": "public"}

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
            # Scan still in progress — keep polling
            if attempt < MAX_POLL_ATTEMPTS - 1:
                time.sleep(POLL_INTERVAL_SECONDS)
            continue

        raise HTTPException(
            status_code=502,
            detail=f"Unexpected response from urlscan.io while polling (HTTP {response.status_code}).",
        )

    raise HTTPException(
        status_code=504,
        detail="Scan timed out. urlscan.io did not return results within the allowed time.",
    )


#########################################################
# Helper: Map urlscan.io raw result to a structured dict
#########################################################
def process_result(uuid: str, raw_result: dict) -> dict:
    page = raw_result.get("page", {})
    verdicts = raw_result.get("verdicts", {})
    overall = verdicts.get("overall", {})

    is_malicious = overall.get("malicious", False)
    score = overall.get("score", 0)

    if is_malicious:
        urlscan_status = "MALICIOUS"
    elif score >= 50:
        urlscan_status = "SUSPICIOUS"
    else:
        urlscan_status = "SAFE"

    initial_url = page.get("url", "")
    redirect_url = page.get("redirected")

    return {
        "uuid": uuid,
        "urlscan_status": urlscan_status,
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
# Helper: Return the more severe of two status strings
#########################################################
def _merge_status(gsb_status: str, urlscan_status: str) -> str:
    if _STATUS_SEVERITY.get(gsb_status, 0) >= _STATUS_SEVERITY.get(urlscan_status, 0):
        return gsb_status
    return urlscan_status


#########################################################
# POST /scan — Submit one or more URLs and return results
#########################################################
# I will include an option to select quick or detailed later
@router.post("")
def scan_url(request: ScanRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Accept a single URL string or a list of URL strings.
    Each URL is checked via Google Safe Browsing v5 first, then submitted to urlscan.io.
    Results are merged (most severe verdict wins) and saved to ScanHistory.
    Always returns a list — one entry per URL submitted.
    """
    urls = request.urls

    # Step 1: Batch-check all URLs with Google Safe Browsing v5 (single round-trip)
    gsb_results = check_google_safe_browsing(urls)

    scan_results = []

    for url in urls:
        gsb = gsb_results[url]

        # Step 2: Submit to urlscan.io
        submission = submit_scan(url)
        uuid = submission.get("uuid")
        if not uuid:
            raise HTTPException(status_code=502, detail=f"urlscan.io did not return a scan UUID for: {url}")

        # Step 3: Poll until the result is ready
        raw_result = poll_result(uuid)

        # Step 4: Parse the urlscan.io result
        urlscan_result = process_result(uuid, raw_result)

        # Step 5: Merge GSB and urlscan verdicts — most severe status wins
        final_status = _merge_status(gsb["gsb_status"], urlscan_result["urlscan_status"])

        # Step 6: Save to ScanHistory
        scan_record = models.ScanHistory(
            UserID=current_user["user_id"],
            InitialURL=urlscan_result["initial_url"],
            RedirectURL=urlscan_result["redirect_url"],
            StatusIndicator=models.ScanStatusEnum(final_status),
            ServerLocation=urlscan_result["server_location"],
            ScreenshotURL=urlscan_result["screenshot_url"],
        )
        db.add(scan_record)
        db.commit()
        db.refresh(scan_record)

        # Step 7: If MALICIOUS, also raise a BlacklistRequest
        # if final_status == "MALICIOUS":
        #     domain = urlparse(urlscan_result["initial_url"]).netloc
        #     blacklist_record = models.BlacklistRequest(
        #         UserID=current_user["user_id"],
        #         URLDomain=domain,
        #         Status=models.RequestStatus.PENDING,
        #     )
        #     db.add(blacklist_record)
        #     db.commit()

        scan_results.append({
            "scan_id": scan_record.ScanID,
            "user_id": scan_record.UserID,
            "uuid": urlscan_result["uuid"],
            "initial_url": scan_record.InitialURL,
            "redirect_url": scan_record.RedirectURL,
            "status_indicator": scan_record.StatusIndicator,
            "score": urlscan_result["score"],
            "server_location": scan_record.ServerLocation,
            "ip_address": urlscan_result["ip_address"],
            "screenshot_url": scan_record.ScreenshotURL,
            "brands": urlscan_result["brands"],
            "tags": urlscan_result["tags"],
            "result_url": urlscan_result["result_url"],
            "scanned_at": scan_record.ScannedAt.isoformat() if scan_record.ScannedAt else None,
            "gsb_flagged": gsb["flagged"],
            "gsb_threat_types": gsb["threat_types"],
        })

    return scan_results
