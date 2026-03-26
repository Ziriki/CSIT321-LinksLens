from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import requests
import time
import os
from dotenv import load_dotenv
from urllib.parse import quote, urlparse

import models
from models import ScanRequest
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

# Google Safe Browsing v4 Lookup API endpoint
GSB_LOOKUP_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"

# Polling configuration: wait 10s before first poll, then every 5s, up to 12 attempts (70s total)
INITIAL_WAIT_SECONDS = 10
POLL_INTERVAL_SECONDS = 5
MAX_POLL_ATTEMPTS = 12

# GSB threat type → LinksLens status mapping
_MALICIOUS_THREATS = {"MALWARE", "SOCIAL_ENGINEERING"}
_SUSPICIOUS_THREATS = {"UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"}

# Severity order used when merging two verdicts
_STATUS_SEVERITY = {"SAFE": 0, "SUSPICIOUS": 1, "MALICIOUS": 2}



#########################################################
# Helper: Check URLs against Google Safe Browsing v4
#########################################################
def check_google_safe_browsing(urls: list[str]) -> dict[str, dict]:
    """
    Batch-check a list of URLs via the GSB v4 threatMatches:find endpoint.

    Uses a POST request with a JSON body containing client info and all threat types.
    Supports up to 500 URLs per request. Returns a dict keyed by URL:
    { flagged, threat_types, gsb_status }.

    On API failure the function does NOT raise — it returns SUSPICIOUS defaults so the
    urlscan.io pipeline still runs. SUSPICIOUS is used rather than SAFE so that an
    unreachable GSB API never silently passes a potentially harmful URL.
    """
    results = {
        url: {"flagged": False, "threat_types": [], "gsb_status": "SUSPICIOUS"}
        for url in urls
    }

    # v4 uses POST with a structured JSON body; API key passed as query param
    payload = {
        "client": {
            "clientId": "linkslens",
            "clientVersion": "1.0"
        },
        "threatInfo": {
            "threatTypes": [
                "MALWARE",
                "SOCIAL_ENGINEERING",
                "UNWANTED_SOFTWARE",
                "POTENTIALLY_HARMFUL_APPLICATION"
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url} for url in urls]
        }
    }
    headers = {"Content-Type": "application/json", "User-Agent": "LinksLens/1.0"}

    delay = 1
    for _ in range(4):
        try:
            response = requests.post(
                GSB_LOOKUP_URL,
                params={"key": GSB_API_KEY},
                json=payload,
                headers=headers,
                timeout=10
            )
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

        # 200 OK — empty body or absent 'matches' key means all URLs are clean
        try:
            data = response.json()
        except Exception:
            # Non-JSON body (e.g. HTML error page from invalid/unenabled API key) — non-blocking
            return results

        # v4 response: { "matches": [{ "threat": { "url": "..." }, "threatType": "..." }] }
        for match in data.get("matches", []):
            url = match.get("threat", {}).get("url", "")
            threat_type = match.get("threatType", "")
            if url not in results:
                continue

            results[url]["flagged"] = True
            if threat_type not in results[url]["threat_types"]:
                results[url]["threat_types"].append(threat_type)

            # Determine the worst status from the returned threat type
            if threat_type in _MALICIOUS_THREATS:
                results[url]["gsb_status"] = "MALICIOUS"
            elif threat_type in _SUSPICIOUS_THREATS:
                if results[url]["gsb_status"] != "MALICIOUS":
                    results[url]["gsb_status"] = "SUSPICIOUS"

        # GSB returned 200 OK — URLs not flagged are confirmed SAFE
        for url_key in results:
            if not results[url_key]["flagged"]:
                results[url_key]["gsb_status"] = "SAFE"

        return results

    # All retries exhausted — non-blocking, return safe defaults
    return results


#########################################################
# Helper: Submit a single URL to urlscan.io
#########################################################
def submit_scan(url: str) -> dict | None:
    """Returns the submission JSON on success, or None if urlscan.io is unreachable/rejects."""
    safe_url = quote(url, safe='/:?=&')
    headers = {
        "API-Key": URLSCAN_API_KEY,
        "Content-Type": "application/json",
    }
    # Visibility is set to public as the quota for non-public calls is too small to be usable
    payload = {"url": safe_url, "visibility": "public"}

    try:
        response = requests.post(URLSCAN_SUBMIT_URL, headers=headers, json=payload, timeout=15)
    except requests.RequestException:
        return None

    if response.status_code not in (200, 201):
        return None

    data = response.json()
    return data if data.get("uuid") else None


#########################################################
# Helper: Poll urlscan.io until the result is ready
#########################################################
def poll_result(uuid: str) -> dict | None:
    """Returns the raw result JSON on success, or None on timeout or unexpected error."""
    result_url = URLSCAN_RESULT_URL.format(uuid=uuid)

    # urlscan.io recommends waiting at least 10 seconds before the first poll
    time.sleep(INITIAL_WAIT_SECONDS)

    for attempt in range(MAX_POLL_ATTEMPTS):
        try:
            response = requests.get(result_url, timeout=15)
        except requests.RequestException:
            return None

        if response.status_code == 200:
            return response.json()

        if response.status_code == 404:
            # Scan still in progress — keep polling
            if attempt < MAX_POLL_ATTEMPTS - 1:
                time.sleep(POLL_INTERVAL_SECONDS)
            continue

        # Any other unexpected status — give up non-fatally
        return None

    # All attempts exhausted
    return None


#########################################################
# Helper: Map urlscan.io raw result to a structured dict
#########################################################
def process_result(uuid: str | None, raw_result: dict | None) -> dict:
    # If the 2 scanning APIs returned nothing, fall back to safe empty values
    if not raw_result or not uuid:
        return {
            "uuid": uuid,
            "urlscan_status": "SUSPICIOUS",
            "score": None,
            "initial_url": None,
            "redirect_url": None,
            "server_location": None,
            "ip_address": None,
            "screenshot_url": None,
            "result_url": None,
            "brands": [],
            "tags": [],
        }

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
def merge_status(gsb_status: str, urlscan_status: str) -> str:
    if _STATUS_SEVERITY.get(gsb_status, 0) >= _STATUS_SEVERITY.get(urlscan_status, 0):
        return gsb_status
    return urlscan_status


#########################################################
# POST /scan — Submit one or more URLs and return results
#########################################################
@router.post("")
def scan_url(request: ScanRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Accept a single URL string or a list of URL strings.
    Each URL is checked via Google Safe Browsing v4 first, then submitted to urlscan.io.
    Results are merged (most severe verdict wins) and saved to ScanHistory.
    Always returns a list — one entry per URL submitted.
    """
    urls = request.urls

    if not urls:
        raise HTTPException(status_code=400, detail="At least one URL is required.")

    for url in urls:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise HTTPException(status_code=400, detail=f"Invalid URL: {url}")

    # Step 1: Batch-check all URLs with Google Safe Browsing v4 (single round-trip)
    gsb_results = check_google_safe_browsing(urls)

    scan_results = []

    for url in urls:
        gsb = gsb_results[url]

        # Step 2: Submit to urlscan.io — returns None on failure
        submission = submit_scan(url)
        uuid = submission.get("uuid") if submission else None

        # Step 3: Poll for the result — returns None on timeout or failure
        raw_result = poll_result(uuid) if uuid else None

        # Step 4: Perform script level analysis - returns None on timeout or failure
        # script_result = script_analysis(url)

        # Step 5: Parse result — process_result handles None uuid/raw_result with SUSPICIOUS fallback
        urlscan_result = process_result(uuid, raw_result)

        # Step 6: Merge GSB and urlscan verdicts — most severe status wins
        final_status = merge_status(gsb["gsb_status"], urlscan_result["urlscan_status"])

        # Step 6b: Check against internal URLRules (blacklist/whitelist) — overrides external verdicts
        domain = urlparse(urlscan_result["initial_url"] or url).netloc
        url_rule = db.query(models.URLRules).filter(models.URLRules.URLDomain == domain).first()
        if url_rule:
            if url_rule.ListType == models.ListTypeEnum.BLACKLIST:
                final_status = "MALICIOUS"
            elif url_rule.ListType == models.ListTypeEnum.WHITELIST:
                final_status = "SAFE"

        # Step 7: Save to ScanHistory
        # initial_url falls back to the submitted url if urlscan returned nothing
        initial_url = urlscan_result["initial_url"] or url
        scan_record = models.ScanHistory(
            UserID=current_user["user_id"],
            InitialURL=initial_url,
            RedirectURL=urlscan_result["redirect_url"],
            StatusIndicator=models.ScanStatusEnum(final_status),
            ServerLocation=urlscan_result["server_location"],
            ScreenshotURL=urlscan_result["screenshot_url"],
        )
        db.add(scan_record)
        db.commit()
        db.refresh(scan_record)

        scan_results.append({
            "scan_id": scan_record.ScanID,
            "user_id": scan_record.UserID,
            "uuid": urlscan_result["uuid"],
            "initial_url": scan_record.InitialURL,
            "redirect_url": scan_record.RedirectURL,
            "status_indicator": scan_record.StatusIndicator.value,
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
