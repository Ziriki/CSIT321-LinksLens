from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import datetime, timezone
import requests
import time
import os
import re
import math
from dotenv import load_dotenv
from urllib.parse import quote, urlparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

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

# Weights applied when combining GSB and urlscan scores (must sum to 1.0)
_GSB_WEIGHT      = 0.55   # GSB is a large, authoritative threat database
_URLSCAN_WEIGHT  = 0.45   # urlscan provides behavioural and visual analysis

# Weighted-score thresholds for mapping to status
# GSB MALWARE alone scores 100 × 0.55 = 55 → threshold ≤ 55 ensures it reaches MALICIOUS
# GSB UNWANTED alone scores  60 × 0.55 = 33 → threshold ≤ 33 ensures it reaches SUSPICIOUS
_MALICIOUS_THRESHOLD  = 50   # weighted score ≥ 50 → MALICIOUS
_SUSPICIOUS_THRESHOLD = 30   # weighted score ≥ 30 → SUSPICIOUS

#########################################################
# Helper: Get domain age in days via WHOIS
#########################################################
def get_domain_age_days(domain: str) -> int | None:
    """
    Look up the domain creation date via WHOIS and return its age in days.
    Returns None if the lookup fails or the creation date is unavailable.
    Non-blocking — failures must never abort the scan pipeline.
    """
    try:
        info = whois.whois(domain)
        creation_date = info.creation_date
        if isinstance(creation_date, list):
            creation_date = creation_date[0]
        if not isinstance(creation_date, datetime):
            return None
        if creation_date.tzinfo is None:
            creation_date = creation_date.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - creation_date).days
    except Exception:
        return None


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
# Helper: Extract the full redirect chain from urlscan.io result
#########################################################
def extract_redirect_chain(initial_url: str, raw_result: dict) -> list[str]:
    """
    Build an ordered list of redirect URLs from urlscan.io result data.
    Parses data.requests for 3xx responses to reconstruct the chain.
    Returns an empty list if there were no redirects or the data is unavailable.
    Non-blocking — failures must never abort the scan pipeline.
    """
    if not raw_result:
        return []

    final_url = raw_result.get("page", {}).get("url", "")
    if not final_url or final_url == initial_url:
        return []

    try:
        requests_data = raw_result.get("data", {}).get("requests", [])
        chain = []
        for req in requests_data:
            response_obj = req.get("response", {}).get("response", {})
            status = response_obj.get("status", 0)
            if 300 <= status < 400:
                url = response_obj.get("url", "")
                if url and url not in chain:
                    chain.append(url)

        if chain and final_url not in chain:
            chain.append(final_url)

        return chain if chain else [final_url]
    except Exception:
        # Fallback: just the final URL so we always return something useful
        return [final_url]


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
        "redirect_url": redirect_url if redirect_url and redirect_url != initial_url and redirect_url.startswith("http") else None,
        "server_location": page.get("country"),
        "ip_address": page.get("ip"),
        "screenshot_url": URLSCAN_SCREENSHOT_URL.format(uuid=uuid),
        "result_url": f"https://urlscan.io/result/{uuid}/",
        "brands": overall.get("brands", []),
        "tags": overall.get("tags", []),
    }


#########################################################
# Helper: Run the full urlscan.io pipeline for one URL
#########################################################
def run_urlscan(url: str) -> dict:
    """Submit, poll and process a single URL through urlscan.io. Returns fallback on any failure."""
    submission = submit_scan(url)
    uuid = submission.get("uuid") if submission else None
    raw_result = poll_result(uuid) if uuid else None
    return process_result(uuid, raw_result)


#########################################################
# Helper: Query DB blacklist/whitelist for a URL domain
#########################################################
def check_blacklist_db(url: str) -> dict:
    """
    Check the URL domain against URLRules and BlacklistRequest tables.
    Uses get_db() manually for thread safety — does not share the request session.
    Returns: { domain, url_rule_type, is_approved_blacklist }
    """
    domain = urlparse(url).netloc
    db_gen = get_db()
    db = next(db_gen)
    try:
        url_rule = db.query(models.URLRules).filter(
            models.URLRules.URLDomain == domain
        ).first()

        approved_blacklist = db.query(models.BlacklistRequest).filter(
            models.BlacklistRequest.URLDomain == domain,
            models.BlacklistRequest.Status == models.RequestStatus.APPROVED
        ).first()

        return {
            "domain": domain,
            "url_rule_type": url_rule.ListType.value if url_rule else None,
            "is_approved_blacklist": approved_blacklist is not None,
        }
    finally:
        next(db_gen, None)


#########################################################
# Helper: Query rdap.org for domain registration info
#########################################################
def check_domain_rdap(url: str) -> dict:
    """
    Query rdap.org for the registration details of the URL's domain.

    Returns:
        domain        — bare hostname (port stripped)
        registration  — ISO-8601 registration date or None
        expiration    — ISO-8601 expiration date or None
        last_changed  — ISO-8601 last-changed date or None
        age           — { years, months, days } since registration, or None
        error         — human-readable reason when the lookup could not complete
    """
    domain = urlparse(url).netloc.split(":")[0]
    # RDAP operates on registrable domains — strip the leading www. if present
    if domain.startswith("www."):
        domain = domain[4:]

    def _fail(reason: str) -> dict:
        return {
            "domain": domain,
            "registration": None,
            "expiration": None,
            "last_changed": None,
            "age": None,
            "error": reason,
        }

    try:
        response = requests.get(
            f"https://rdap.org/domain/{domain}",
            headers={"Accept": "application/json"},
            timeout=15,
        )
    except requests.RequestException as e:
        return _fail(f"RDAP request failed: {str(e)}")

    if response.status_code == 404:
        return _fail(f"Domain not found in RDAP registry: {domain}")
    if response.status_code != 200:
        return _fail(f"RDAP registry returned HTTP {response.status_code}")

    try:
        data = response.json()
    except Exception:
        return _fail("RDAP response was not valid JSON")

    dates: dict[str, str | None] = {"registration": None, "expiration": None, "last_changed": None}
    for event in data.get("events", []):
        action = event.get("eventAction", "").lower().strip()
        date_str = event.get("eventDate")
        if action == "registration":
            dates["registration"] = date_str
        elif action == "expiration":
            dates["expiration"] = date_str
        elif action == "last changed":
            dates["last_changed"] = date_str

    age = None
    if dates["registration"]:
        try:
            reg_dt     = datetime.fromisoformat(dates["registration"].replace("Z", "+00:00"))
            delta      = datetime.now(timezone.utc) - reg_dt
            total_days = delta.days
            years      = total_days // 365
            months     = (total_days % 365) // 30
            days       = (total_days % 365) % 30
            age = {"years": years, "months": months, "days": days}
        except Exception:
            age = None

    return {
        "domain": domain,
        "registration": dates["registration"],
        "expiration": dates["expiration"],
        "last_changed": dates["last_changed"],
        "age": age,
        "error": None,
    }


#########################################################
# Helper: Compare GSB, urlscan and DB results
#########################################################
def compare_async_results(gsb: dict, urlscan_result: dict, blacklist_check: dict) -> str:
    """
    Derive a final_status by weighing all three verdict sources.

    Step 1 — Convert raw signals to 0-100 scores:
      GSB score:
        Any MALWARE / SOCIAL_ENGINEERING threat type  → 100
        Any UNWANTED_SOFTWARE / POTENTIALLY_HARMFUL   → 60
        No threats flagged                            → 0

      urlscan score: numeric field from result (0-100)

    Step 2 — Weighted combination:
      weighted_score = (gsb_score × 0.55) + (urlscan_score × 0.45)

    Step 3 — Map to api_status:
      weighted_score ≥ 50 → MALICIOUS
      weighted_score ≥ 30 → SUSPICIOUS
      weighted_score < 30 → SAFE

    Step 4 — DB rule override (authoritative — admin/moderator has final say):
      URLRules BLACKLIST or approved BlacklistRequest → MALICIOUS
      URLRules WHITELIST                              → SAFE
    """
    # Step 1: derive scores
    threat_types = gsb.get("threat_types", [])
    if any(t in _MALICIOUS_THREATS for t in threat_types):
        gsb_score = 100
    elif any(t in _SUSPICIOUS_THREATS for t in threat_types):
        gsb_score = 60
    else:
        gsb_score = 0

    urlscan_score = urlscan_result.get("score") or 0

    # Step 2: weighted combination
    weighted_score = (gsb_score * _GSB_WEIGHT) + (urlscan_score * _URLSCAN_WEIGHT)

    # Step 3: map to api_status
    if weighted_score >= _MALICIOUS_THRESHOLD:
        api_status = "MALICIOUS"
    elif weighted_score >= _SUSPICIOUS_THRESHOLD:
        api_status = "SUSPICIOUS"
    else:
        api_status = "SAFE"

    # Step 4: DB rule override
    url_rule = blacklist_check.get("url_rule_type")
    is_approved_blacklist = blacklist_check.get("is_approved_blacklist", False)

    if url_rule == "BLACKLIST" or is_approved_blacklist:
        final_status = "MALICIOUS"
    elif url_rule == "WHITELIST":
        final_status = "SAFE"
    else:
        final_status = api_status

    return final_status


#########################################################
# Helper: Merge async API verdict with JS analysis result
#########################################################

# Status → numeric score for weighted merge
_ASYNC_STATUS_SCORE = {"SAFE": 0, "SUSPICIOUS": 50, "MALICIOUS": 100}

# JS is weighted slightly more than the async verdict
_MERGE_JS_WEIGHT    = 0.55
_MERGE_ASYNC_WEIGHT = 0.45

def merge_final_verdict(async_status: str, js_result: dict | None) -> str:
    """
    Combine the async API verdict (GSB + urlscan + DB rule) with the JS
    analysis result to produce the definitive final_status.

    JS analysis is weighted slightly more (0.55) because it performs live
    behavioural inspection of the actual page content.

    Return values:
        SAFE        — no signals from either source
        SUSPICIOUS  — moderate risk detected
        MALICIOUS   — high-confidence threat detected
        UNAVAILABLE — JS browser launch failed AND async verdict is not
                      conclusive enough to confirm safety; caller should
                      treat the URL as unverified
    """
    # JS was not run because the URL was already confirmed MALICIOUS — trust it
    if js_result is None:
        return async_status

    # Detect browser launch failure
    browser_failed = any(
        f.get("pattern") == "browser_error"
        for f in js_result.get("findings", [])
    )

    if browser_failed:
        # Can't do live JS analysis — escalate async verdict or flag UNAVAILABLE
        if async_status == "MALICIOUS":
            return "MALICIOUS"
        if async_status == "SAFE":
            return "UNAVAILABLE"
        return async_status  # SUSPICIOUS stays SUSPICIOUS

    # Both sources are available — perform weighted merge
    async_score = _ASYNC_STATUS_SCORE.get(async_status, 0)
    js_score    = js_result.get("js_score", 0)          # already 0-100

    weighted = (js_score * _MERGE_JS_WEIGHT) + (async_score * _MERGE_ASYNC_WEIGHT)

    if weighted >= _MALICIOUS_THRESHOLD:
        return "MALICIOUS"
    if weighted >= _SUSPICIOUS_THRESHOLD:
        return "SUSPICIOUS"
    return "SAFE"


#########################################################
# Suspicious JS patterns checked during page analysis
#########################################################
_JS_PATTERNS = [
    # --- MALICIOUS ---
    {
        "name": "eval_obfuscation",
        "pattern": re.compile(r'\beval\s*\(\s*(?:unescape|decodeURIComponent|atob)\s*\(', re.IGNORECASE),
        "severity": "MALICIOUS",
        "description": "eval() wrapping a decoder — classic obfuscation used to hide malicious payloads",
    },
    {
        "name": "fromCharCode_chain",
        "pattern": re.compile(r'String\.fromCharCode\s*\((?:\s*\d+\s*,){4,}', re.IGNORECASE),
        "severity": "MALICIOUS",
        "description": "Long String.fromCharCode() chain — common technique to obscure shellcode or injected scripts",
    },
    {
        "name": "crypto_miner",
        "pattern": re.compile(r'(coinhive|cryptonight|minero|webminepool|coin-hive|miner\.start)', re.IGNORECASE),
        "severity": "MALICIOUS",
        "description": "Known crypto-mining library reference detected",
    },
    {
        # Tightened: network call must appear within ~300 chars of the key listener
        # (no DOTALL) to avoid false positives where keyboard shortcuts and fetch
        # calls are unrelated functions in the same file (e.g. media players).
        "name": "keylogger",
        "pattern": re.compile(r'addEventListener\s*\(\s*["\']key(?:down|up|press)["\'].{0,300}(?:fetch|XMLHttpRequest|\.open\s*\()', re.IGNORECASE),
        "severity": "SUSPICIOUS",
        "description": "Keyboard event listener close to a network call — possible keylogger pattern",
    },
    {
        "name": "form_hijack",
        "pattern": re.compile(r'(?:document\.querySelector|getElementById)\s*\([^)]*form[^)]*\).*?addEventListener\s*\(\s*["\']submit', re.IGNORECASE | re.DOTALL),
        "severity": "MALICIOUS",
        "description": "Form submit listener patched dynamically — potential credential harvesting",
    },
    # --- SUSPICIOUS ---
    {
        "name": "eval_dynamic",
        "pattern": re.compile(r'\beval\s*\([^)]{20,}\)', re.IGNORECASE),
        "severity": "SUSPICIOUS",
        "description": "eval() with a non-trivial argument — may execute dynamically constructed code",
    },
    {
        "name": "document_write_encoded",
        "pattern": re.compile(r'document\.write\s*\(\s*(?:unescape|decodeURIComponent|atob)\s*\(', re.IGNORECASE),
        "severity": "SUSPICIOUS",
        "description": "document.write() with encoded content — often used to inject hidden iframes or scripts",
    },
    {
        "name": "base64_decode",
        "pattern": re.compile(r'\batob\s*\(', re.IGNORECASE),
        "severity": "SUSPICIOUS",
        "description": "Base64 decode (atob) call — frequently used to conceal payload strings",
    },
    {
        "name": "forced_redirect",
        "pattern": re.compile(r'window\.location\s*(?:\.\s*(?:href|replace|assign)\s*=|=)\s*["\']https?://', re.IGNORECASE),
        "severity": "SUSPICIOUS",
        "description": "Hard-coded external redirect via window.location — may redirect users to malicious sites",
    },
    {
        "name": "high_hex_density",
        "pattern": re.compile(r'(?:\\x[0-9a-f]{2}){12,}', re.IGNORECASE),
        "severity": "SUSPICIOUS",
        "description": "Dense hex-escape sequence — indicates obfuscated string content",
    },
    {
        "name": "high_unicode_density",
        "pattern": re.compile(r'(?:\\u[0-9a-f]{4}){8,}', re.IGNORECASE),
        "severity": "SUSPICIOUS",
        "description": "Dense unicode-escape sequence — indicates obfuscated string content",
    },
]

_JS_MALICIOUS_SCORE  = 35   # added per MALICIOUS finding
_JS_SUSPICIOUS_SCORE = 15   # added per SUSPICIOUS finding
_JS_MALICIOUS_THRESHOLD  = 70
_JS_SUSPICIOUS_THRESHOLD = 55  # raised from 40 — minor accumulation no longer flips SAFE

def calc_entropy(text: str) -> float:
    """
    Shannon entropy of a string — measures character distribution randomness.
    High entropy (> 5.2) suggests the content is encoded, compressed, or obfuscated.

    Formula: H = -Σ p(c) * log2(p(c))
      where p(c) is the probability of each character c appearing in the string.
    The more evenly characters are distributed, the higher the entropy.
    """
    if not text:
        return 0.0

    # Count how many times each character appears
    freq = Counter(text)
    length = len(text)
    entropy = 0.0
    for count in freq.values():
        probability = count / length                        # p(c)
        entropy    += probability * math.log2(probability) # p(c) * log2(p(c))

    return -entropy  # negate to get a positive value


def analyse_javascript(source: str, location: str) -> list[dict]:
    """Run all pattern checks against a single JS source string. Returns a list of findings."""
    findings = []
    for rule in _JS_PATTERNS:
        if rule["pattern"].search(source):
            findings.append({
                "pattern": rule["name"],
                "severity": rule["severity"],
                "description": rule["description"],
                "location": location,
            })

    # Entropy check — raised from 5.2 to 5.7 to avoid flagging legitimately minified JS
    entropy = calc_entropy(source)
    if entropy > 5.7 and len(source) > 300:
        findings.append({
            "pattern": "high_entropy",
            "severity": "SUSPICIOUS",
            "description": f"Script has unusually high entropy ({entropy:.2f}) — likely obfuscated or minified malicious code",
            "location": location,
        })

    return findings


#########################################################
# Helper: Launch headless browser, extract and analyse JS
#########################################################
def analyse_script(url: str) -> dict:
    """
    Launch a headless Chromium browser, navigate to the URL, intercept all JS
    responses, and analyse each script for malicious or suspicious patterns.

    Returns:
        js_status        — SAFE | SUSPICIOUS | MALICIOUS
        js_score         — 0-100 weighted score
        findings         — list of { pattern, severity, description, location }
        scripts_analysed — total JS sources checked
        inline_count     — number of inline <script> blocks
        external_count   — number of external .js files intercepted
    """
    collected_scripts: list[tuple[str, str]] = []   # (source, location)
    js_response_bodies: dict[str, str] = {}

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
                java_script_enabled=True,
            )
            page = context.new_page()

            # Intercept JS responses to capture external script bodies
            def handle_response(response):
                content_type = response.headers.get("content-type", "")
                if "javascript" in content_type or response.url.split("?")[0].endswith(".js"):
                    try:
                        body = response.body().decode("utf-8", errors="ignore")
                        js_response_bodies[response.url] = body
                    except Exception:
                        pass

            page.on("response", handle_response)

            try:
                page.goto(url, wait_until="networkidle", timeout=20_000)
            except PlaywrightTimeoutError:
                pass

            inline_sources = page.eval_on_selector_all(
                "script:not([src])",
                "els => els.map(el => el.textContent)"
            )
            for idx, src in enumerate(inline_sources):
                if src and src.strip():
                    collected_scripts.append((src, f"inline[{idx}]"))

            browser.close()

    except Exception as e:
        return {
            "js_status": "SUSPICIOUS",
            "js_score": 0,
            "findings": [{"pattern": "browser_error", "severity": "SUSPICIOUS",
                          "description": f"Headless browser failed: {str(e)}", "location": url}],
            "scripts_analysed": 0,
            "inline_count": 0,
            "external_count": 0,
        }

    # Add captured external JS bodies
    for script_url, body in js_response_bodies.items():
        collected_scripts.append((body, script_url))

    inline_count   = len(inline_sources)
    external_count = len(js_response_bodies)

    # Analyse every collected script
    all_findings: list[dict] = []
    for source, location in collected_scripts:
        all_findings.extend(analyse_javascript(source, location))

    # Score: accumulate per finding, cap at 100
    score = 0
    for finding in all_findings:
        score += _JS_MALICIOUS_SCORE if finding["severity"] == "MALICIOUS" else _JS_SUSPICIOUS_SCORE
    score = min(score, 100)

    if score >= _JS_MALICIOUS_THRESHOLD:
        js_status = "MALICIOUS"
    elif score >= _JS_SUSPICIOUS_THRESHOLD:
        js_status = "SUSPICIOUS"
    else:
        js_status = "SAFE"

    return {
        "js_status": js_status,
        "js_score": score,
        "findings": all_findings,
        "scripts_analysed": len(collected_scripts),
        "inline_count": inline_count,
        "external_count": external_count,
    }


#########################################################
# POST /scan — Submit one or more URLs and return results
#########################################################
@router.post("")
def scan_url(request: ScanRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    For each URL:
      1. Fire GSB, urlscan.io, DB blacklist check and RDAP concurrently
      2. Wait for all four results
      3. compare_async_results()  — weighted GSB + urlscan + DB rule → async_status
      4. analyse_script()         — headless JS analysis (skipped if already MALICIOUS)
      5. merge_final_verdict()    — combine async_status + JS result → final_status
      6. Save to ScanHistory, return response
    """
    scan_results = []
    try:
        urls = request.urls

        if not urls:
            raise HTTPException(status_code=400, detail="At least one URL is required.")

        for url in urls:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise HTTPException(status_code=400, detail=f"Invalid URL: {url}")

        for url in urls:
            # Step 1 & 2: Fire GSB, urlscan.io, DB blacklist check and RDAP concurrently
            # and collect results — .result() blocks until each future completes
            with ThreadPoolExecutor(max_workers=4) as executor:
                gsb_future       = executor.submit(check_google_safe_browsing, [url])
                urlscan_future   = executor.submit(run_urlscan, url)
                blacklist_future = executor.submit(check_blacklist_db, url)
                rdap_future      = executor.submit(check_domain_rdap, url)

                gsb             = gsb_future.result()[url]
                urlscan_result  = urlscan_future.result()
                blacklist_check = blacklist_future.result()
                domain_info     = rdap_future.result()

            # Step 3: Compare async results — weighted scoring + DB rule override
            async_status = compare_async_results(gsb, urlscan_result, blacklist_check)

            # Step 4: JS analysis — only run if not already confirmed MALICIOUS
            js_result = None
            if async_status in ("SAFE", "SUSPICIOUS"):
                js_result = analyse_script(url)

            # Step 5: Merge async verdict with JS analysis to get final_status
            final_status = merge_final_verdict(async_status, js_result)

            # UNAVAILABLE cannot be stored as a ScanStatusEnum — save as SUSPICIOUS
            db_status = "SUSPICIOUS" if final_status == "UNAVAILABLE" else final_status

            # Step 6: Save to ScanHistory
            initial_url = urlscan_result["initial_url"] or url
            scan_record = models.ScanHistory(
                UserID=current_user["user_id"],
                InitialURL=initial_url,
                RedirectURL=urlscan_result["redirect_url"],
                StatusIndicator=models.ScanStatusEnum(db_status),
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
                "status_indicator": final_status,
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
                "js_analysis": js_result,
                "domain_info": domain_info,
            })
    
    except HTTPException:
        raise

    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request syntax: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    return scan_results
