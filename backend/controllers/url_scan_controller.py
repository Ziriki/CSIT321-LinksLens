from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, literal, or_
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import requests
import time
import os
import re
import unicodedata
from dotenv import load_dotenv
from urllib.parse import quote, urlparse, urlunparse

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
_GSB_DEFAULT_PORTS: dict[str, int] = {"http": 80, "https": 443}

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
# Script analysis: domain classification lists
#########################################################
_AD_DOMAINS = {
    "doubleclick.net", "googlesyndication.com", "amazon-adsystem.com",
    "adnxs.com", "advertising.com", "taboola.com", "outbrain.com",
    "criteo.com", "rubiconproject.com", "pubmatic.com", "openx.net",
    "moatads.com", "scorecardresearch.com", "adsafeprotected.com",
    "sharethrough.com", "33across.com", "appnexus.com", "smartadserver.com",
}
_CRYPTO_MINER_DOMAINS = {
    "coinhive.com", "coin-hive.com", "cryptoloot.pro", "webmine.pro",
    "minero.cc", "jsecoin.com", "monerominer.rocks", "coinimp.com",
    "papoto.com", "authedmine.com",
}
_MALICIOUS_SCRIPT_DOMAINS = {
    "greatbigstuff.net", "trackyoudown.net", "blackhatseo.tech",
}
_TRUSTED_CDN_DOMAINS = {
    "cdnjs.cloudflare.com", "cdn.jsdelivr.net", "unpkg.com",
    "ajax.googleapis.com", "code.jquery.com", "stackpath.bootstrapcdn.com",
    "maxcdn.bootstrapcdn.com", "cdn.tailwindcss.com", "cdn.ampproject.org",
}
_FREE_HOSTING_DOMAINS = {
    "pastebin.com", "paste.ee", "hastebin.com", "ghostbin.com",
    "raw.githubusercontent.com", "gist.githubusercontent.com",
}
_AD_HEAVY_THRESHOLD = 5
_OBFUSCATED_NAME_RE = re.compile(r"/[a-z0-9]{8,}\.js$", re.IGNORECASE)
_IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

_CONFUSABLE_SCRIPTS = {"CYRILLIC", "GREEK", "ARMENIAN", "CHEROKEE", "GEORGIAN"}


def _reg_domain(netloc: str) -> str:
    """Return the registrable domain (last two labels) from a netloc string."""
    parts = netloc.removeprefix("www.").split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else netloc


#########################################################
# Helper: Analyse scripts using urlscan.io result data
#########################################################
def analyze_scripts(raw_result: dict | None, initial_url: str = "") -> dict:
    """
    Parse urlscan.io result data to classify scripts loaded by the page.

    Uses data.lists.scripts (pre-extracted by urlscan.io) — same sandboxed
    browser visit urlscan already performed, no second visit needed.
    Tech stack is sourced from meta.processors.wappa (Wappalyzer).
    """
    if not raw_result:
        return {
            "total": 0, "trusted_count": 0, "ad_count": 0, "ad_heavy": False,
            "crypto_miners": [], "malicious_scripts": [],
            "suspicious_patterns": [], "tech_stack": [], "script_risk_score": 0,
        }

    data = raw_result.get("data", {})
    page_url = raw_result.get("page", {}).get("url", "") or initial_url
    page_scheme = urlparse(page_url).scheme.lower()
    scripts: list[str] = data.get("lists", {}).get("scripts", [])

    ad_scripts: list[str] = []
    crypto_miners: list[str] = []
    malicious_scripts: list[str] = []
    trusted_scripts: list[str] = []
    suspicious_patterns: list[dict] = []

    for script_url in scripts:
        parsed = urlparse(script_url)
        netloc = parsed.netloc.lower()

        if _IP_RE.match(netloc):
            suspicious_patterns.append({"url": script_url, "reason": "IP-hosted script"})
            continue
        if page_scheme == "https" and parsed.scheme == "http":
            suspicious_patterns.append({"url": script_url, "reason": "HTTP script on HTTPS page"})
            continue
        reg = _reg_domain(netloc)
        if reg in _FREE_HOSTING_DOMAINS:
            suspicious_patterns.append({"url": script_url, "reason": "Script from free hosting service"})
            continue

        if reg in _CRYPTO_MINER_DOMAINS:
            crypto_miners.append(script_url)
        elif reg in _MALICIOUS_SCRIPT_DOMAINS:
            malicious_scripts.append(script_url)
        elif reg in _AD_DOMAINS:
            ad_scripts.append(script_url)
        elif netloc in _TRUSTED_CDN_DOMAINS:
            trusted_scripts.append(script_url)
        elif _OBFUSCATED_NAME_RE.search(parsed.path):
            suspicious_patterns.append({"url": script_url, "reason": "Obfuscated script filename"})

    wappa_data = data.get("meta", {}).get("processors", {}).get("wappa", {}).get("data", [])
    tech_stack = [
        {"name": t.get("app", ""), "categories": [c.get("name", "") for c in t.get("categories", [])]}
        for t in wappa_data if t.get("app")
    ]

    ad_heavy = len(ad_scripts) >= _AD_HEAVY_THRESHOLD
    score = 0
    score += min(len(crypto_miners) * 35, 70)
    score += min(len(malicious_scripts) * 25, 50)
    score += min(len(suspicious_patterns) * 10, 30)
    score += min(len(ad_scripts) * 2, 15)
    score += 10 if ad_heavy else 0
    score -= min(len(trusted_scripts) * 3, 15)
    score = max(0, min(score, 100))

    return {
        "total": len(scripts),
        "trusted_count": len(trusted_scripts),
        "ad_count": len(ad_scripts),
        "ad_heavy": ad_heavy,
        "crypto_miners": crypto_miners[:20],
        "malicious_scripts": malicious_scripts[:20],
        "suspicious_patterns": suspicious_patterns[:20],
        "tech_stack": tech_stack,
        "script_risk_score": score,
    }


#########################################################
# Helper: Detect IDN homograph attacks (stdlib only)
#########################################################
def detect_homograph_risk(url: str) -> dict:
    """
    Detect IDN homograph attacks using only Python stdlib unicodedata.
    Flags domains that mix Latin with visually confusable scripts (Cyrillic,
    Greek, Armenian, Cherokee, Georgian). Never raises — failures return safe
    defaults so the scan pipeline is never aborted.
    """
    result: dict = {
        "is_homograph": False, "risk_score": 0, "punycode": None,
        "mixed_scripts": [], "confusable_chars": [], "details": None,
    }
    try:
        domain = urlparse(url).hostname or ""
        if not domain:
            return result

        try:
            domain.encode("ascii")
            if "xn--" not in domain.lower():
                return result
            labels = domain.lower().split(".")
            decoded_labels = []
            for label in labels:
                if label.startswith("xn--"):
                    try:
                        decoded_labels.append(label.encode("ascii").decode("idna"))
                    except Exception:
                        decoded_labels.append(label)
                else:
                    decoded_labels.append(label)
            result["punycode"] = domain
            domain = ".".join(decoded_labels)
        except UnicodeEncodeError:
            try:
                labels = domain.lower().split(".")
                punycode_parts = []
                for label in labels:
                    try:
                        punycode_parts.append(label.encode("idna").decode("ascii"))
                    except Exception:
                        punycode_parts.append(label)
                result["punycode"] = ".".join(punycode_parts)
            except Exception:
                pass

        scripts_found: set[str] = set()
        confusable_chars: list[str] = []
        for char in domain:
            if char in ".-":
                continue
            char_name = unicodedata.name(char, "")
            script = char_name.split(" ")[0] if char_name else "UNKNOWN"
            scripts_found.add(script)
            if script in _CONFUSABLE_SCRIPTS and len(confusable_chars) < 10:
                confusable_chars.append(f"'{char}' ({char_name})")

        latin_present = "LATIN" in scripts_found
        non_latin = scripts_found - {"LATIN", "DIGIT", "UNKNOWN"}

        if confusable_chars:
            result["is_homograph"] = True
            result["mixed_scripts"] = sorted(scripts_found - {"UNKNOWN"})
            result["confusable_chars"] = confusable_chars
            if latin_present and non_latin:
                result["risk_score"] = min(90, 50 + len(confusable_chars) * 8)
                result["details"] = (
                    f"Domain mixes scripts ({', '.join(sorted(non_latin))} + Latin) "
                    f"with {len(confusable_chars)} visually confusable character(s)."
                )
            else:
                result["risk_score"] = min(80, 40 + len(confusable_chars) * 8)
                result["details"] = (
                    f"Domain contains {len(confusable_chars)} character(s) from "
                    f"{', '.join(sorted(non_latin or {'unknown script'}))} "
                    f"that visually resemble ASCII letters."
                )
    except Exception:
        pass
    return result


def _normalize_for_gsb(url: str) -> str:
    """
    Normalize a URL to match GSB's canonical form before lookup.
    Mirrors the normalization Chrome applies: strip fragment, lowercase hostname,
    remove default ports (80/443). Without this, GSB may return a match for the
    normalized form that doesn't key back to the original URL in our results dict.
    """
    try:
        parsed = urlparse(url.strip())
        host = (parsed.hostname or "").lower()
        port = parsed.port
        netloc = f"{host}:{port}" if port and port != _GSB_DEFAULT_PORTS.get(parsed.scheme) else host
        # Strip fragment — GSB ignores it; keep everything else intact
        return urlunparse((parsed.scheme, netloc, parsed.path or "/", parsed.params, parsed.query, ""))
    except Exception:
        return url


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

    # Normalize each URL to GSB's canonical form and keep a reverse map so that
    # when GSB returns a match we can key back to the original URL in results.
    # Without this, a match for "http://evil.com/path" silently drops if we sent
    # "http://Evil.com/path#fragment" — the URLs don't match as dict keys.
    norm_to_original: dict[str, str] = {_normalize_for_gsb(url): url for url in urls}

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
            "threatEntries": [{"url": norm_url} for norm_url in norm_to_original]
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
            gsb_url = match.get("threat", {}).get("url", "")
            threat_type = match.get("threatType", "")
            # GSB returns the URL in its normalized form — map back to the original
            original_url = (
                norm_to_original.get(gsb_url)
                or norm_to_original.get(_normalize_for_gsb(gsb_url))
            )
            if not original_url:
                continue

            results[original_url]["flagged"] = True
            if threat_type not in results[original_url]["threat_types"]:
                results[original_url]["threat_types"].append(threat_type)

            # Determine the worst status from the returned threat type
            if threat_type in _MALICIOUS_THREATS:
                results[original_url]["gsb_status"] = "MALICIOUS"
            elif threat_type in _SUSPICIOUS_THREATS:
                if results[original_url]["gsb_status"] != "MALICIOUS":
                    results[original_url]["gsb_status"] = "SUSPICIOUS"

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
# Helper: Extract SSL/TLS certificate info from urlscan
#########################################################
def extract_ssl_info(raw_result: dict | None) -> dict | None:
    """
    Extract SSL/TLS certificate details from the first HTTPS request in the
    urlscan.io raw result that contains securityDetails.
    Returns None when SSL info is unavailable (HTTP site or scan timeout).
    Non-blocking — failures must never abort the scan pipeline.
    """
    if not raw_result:
        return None
    try:
        for req in raw_result.get("data", {}).get("requests", []):
            sec = req.get("response", {}).get("response", {}).get("securityDetails")
            if not sec:
                continue
            protocol = sec.get("protocol")
            issuer = sec.get("issuer")
            if not (protocol and issuer):
                continue
            valid_from_ts = sec.get("validFrom")
            valid_to_ts = sec.get("validTo")
            return {
                "issuer": issuer,
                "subject": sec.get("subjectName"),
                "valid_from": datetime.fromtimestamp(valid_from_ts, tz=timezone.utc).strftime("%Y-%m-%d") if valid_from_ts else None,
                "valid_to": datetime.fromtimestamp(valid_to_ts, tz=timezone.utc).strftime("%Y-%m-%d") if valid_to_ts else None,
                "protocol": protocol,
            }
    except Exception:
        pass
    return None


#########################################################
# Helper: Map urlscan.io raw result to a structured dict
#########################################################
def process_result(uuid: str | None, raw_result: dict | None) -> dict:
    # If the 2 scanning APIs returned nothing, fall back to safe empty values
    if not raw_result or not uuid:
        return {
            "uuid": uuid,
            "urlscan_status": "SAFE",
            "score": None,
            "initial_url": None,
            "redirect_url": None,
            "server_location": None,
            "ip_address": None,
            "asn_name": None,
            "page_title": None,
            "apex_domain": None,
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
        "asn_name": page.get("asnname"),
        "page_title": page.get("title"),
        "apex_domain": page.get("apexDomain"),
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
    result = process_result(uuid, raw_result)
    result["_raw"] = raw_result  # preserved for analyze_scripts / extract_redirect_chain
    return result


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
        # Match exact domain or any subdomain (e.g. "www.mom.gov.sg" matches stored "mom.gov.sg")
        # The CONCAT check uses "%.domain" so "evil-mom.gov.sg" does NOT match "mom.gov.sg"
        domain_match = or_(
            models.URLRules.URLDomain == domain,
            literal(domain).like(func.concat("%.", models.URLRules.URLDomain))
        )
        url_rule = db.query(models.URLRules).filter(domain_match).first()

        bl_domain_match = or_(
            models.BlacklistRequest.URLDomain == domain,
            literal(domain).like(func.concat("%.", models.BlacklistRequest.URLDomain))
        )
        approved_blacklist = db.query(models.BlacklistRequest).filter(
            bl_domain_match,
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
        "total_days": total_days if dates["registration"] and age else None,
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
# POST /scan — Submit one or more URLs and return results
#########################################################
@router.post("")
def scan_url(request: ScanRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    For each URL:
      1. GSB, urlscan.io (with raw), DB blacklist, RDAP — concurrent
      2. extract_redirect_chain()    — from raw result, ~0ms
      3. analyze_scripts()           — urlscan.io-based, ~0ms
      4. detect_homograph_risk()     — stdlib unicodedata, ~0ms
      5. compare_async_results()     — weighted GSB + urlscan + DB override
      6. Escalation rules            — crypto miners / homograph / malicious scripts
      7. domain_age_days             — from RDAP age breakdown
      8. Save all fields to DB
      9. Return response
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
            with ThreadPoolExecutor(max_workers=4) as executor:
                gsb_future       = executor.submit(check_google_safe_browsing, [url])
                urlscan_future   = executor.submit(run_urlscan, url)
                blacklist_future = executor.submit(check_blacklist_db, url)
                rdap_future      = executor.submit(check_domain_rdap, url)

                gsb             = gsb_future.result()[url]
                urlscan_result  = urlscan_future.result()
                blacklist_check = blacklist_future.result()
                domain_info     = rdap_future.result()

            raw_result = urlscan_result.pop("_raw", None)
            initial_url = urlscan_result["initial_url"] or url

            redirect_chain     = extract_redirect_chain(initial_url, raw_result)
            script_analysis    = analyze_scripts(raw_result, initial_url)
            homograph_analysis = detect_homograph_risk(initial_url)
            ssl_info           = extract_ssl_info(raw_result)

            final_status = compare_async_results(gsb, urlscan_result, blacklist_check)

            # Escalation — only applied when DB rules haven't already set MALICIOUS
            if final_status != "MALICIOUS":
                if script_analysis["malicious_scripts"]:
                    final_status = "MALICIOUS"
                elif (
                    script_analysis["crypto_miners"]
                    or homograph_analysis["is_homograph"]
                    or script_analysis["script_risk_score"] >= 70
                ) and final_status == "SAFE":
                    final_status = "SUSPICIOUS"

            # If urlscan.io couldn't reach the URL (domain unreachable / doesn't exist)
            # and no other signal flagged it, the result is genuinely unknown — not SAFE.
            if raw_result is None and final_status == "SAFE":
                final_status = "UNAVAILABLE"

            domain_age_days = domain_info.get("total_days")

            scan_record = models.ScanHistory(
                UserID=current_user["user_id"],
                InitialURL=initial_url,
                RedirectURL=urlscan_result["redirect_url"],
                RedirectChain=redirect_chain or None,
                StatusIndicator=models.ScanStatusEnum(final_status),
                DomainAgeDays=domain_age_days,
                ServerLocation=urlscan_result["server_location"],
                IpAddress=urlscan_result["ip_address"],
                AsnName=urlscan_result["asn_name"],
                PageTitle=urlscan_result["page_title"],
                ApexDomain=urlscan_result["apex_domain"],
                SslInfo=ssl_info,
                ScreenshotURL=urlscan_result["screenshot_url"],
                ScriptAnalysis=script_analysis,
                HomographAnalysis=homograph_analysis,
            )
            db.add(scan_record)
            db.commit()
            db.refresh(scan_record)

            scan_results.append({
                "scan_id": scan_record.ScanID,
                "user_id": current_user["user_id"],
                "uuid": urlscan_result["uuid"],
                "initial_url": initial_url,
                "redirect_url": urlscan_result["redirect_url"],
                "redirect_chain": redirect_chain or [],
                "status_indicator": final_status,
                "domain_age_days": domain_age_days,
                "server_location": urlscan_result["server_location"],
                "ip_address": urlscan_result["ip_address"],
                "asn_name": urlscan_result["asn_name"],
                "page_title": urlscan_result["page_title"],
                "apex_domain": urlscan_result["apex_domain"],
                "screenshot_url": urlscan_result["screenshot_url"],
                "brands": urlscan_result["brands"],
                "tags": urlscan_result["tags"],
                "result_url": urlscan_result["result_url"],
                "scanned_at": scan_record.ScannedAt.isoformat() if scan_record.ScannedAt else None,
                "gsb_flagged": gsb["flagged"],
                "gsb_threat_types": gsb["threat_types"],
                "script_analysis": script_analysis,
                "homograph_analysis": homograph_analysis,
                "ssl_info": ssl_info,
            })

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    return scan_results
