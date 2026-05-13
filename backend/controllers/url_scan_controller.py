from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import tldextract
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import ipaddress
import requests
import socket
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


############################################
# This function is to resolve the URL's hostname to an IP address and
# return False if it maps to a private, loopback, link-local, multicast,
# reserved, or unspecified range to prevent SSRF attacks.
############################################
def _is_ssrf_safe(url: str) -> bool:
    try:
        hostname = urlparse(url).hostname
        if not hostname:
            return False
        ip = ipaddress.ip_address(socket.gethostbyname(hostname))
        return not any([
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        ])
    except Exception:
        return False

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

# Initial sleep before first poll. urlscan.io recommends 10s, but 3s is safe.
# Early polls that return 404 are harmless and allow fast scans to be caught sooner.
INITIAL_WAIT_SECONDS = 3

# Progressive back-off between poll attempts.
# Front-loaded with short intervals to catch fast scans. Longer waits later
# to avoid hammering the API on slow pages.
# Total max wait: INITIAL_WAIT_SECONDS + sum(POLL_INTERVALS) ≈ 89s.
# Nginx proxy_read_timeout is set to 120s. Do not exceed that budget.
POLL_INTERVALS: list[int] = [1, 1, 2, 3, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
MAX_POLL_ATTEMPTS = len(POLL_INTERVALS)

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
    # Google
    "doubleclick.net", "googlesyndication.com", "googletagmanager.com",
    "google-analytics.com", "googletagservices.com", "googleadservices.com",
    "google.com",
    # Meta / Facebook
    "facebook.net", "facebook.com",
    # Amazon
    "amazon-adsystem.com",
    # Trade desk / programmatic
    "adnxs.com", "appnexus.com", "rubiconproject.com", "pubmatic.com",
    "openx.net", "33across.com", "sharethrough.com", "smartadserver.com",
    "advertising.com", "adsafeprotected.com", "moatads.com",
    "scorecardresearch.com", "criteo.com",
    # Content recommendation
    "taboola.com", "outbrain.com", "revcontent.com", "mgid.com",
    # Analytics / heatmaps / session recording
    "hotjar.com", "clarity.ms", "mouseflow.com", "fullstory.com",
    "logrocket.com", "heap.io", "mixpanel.com", "segment.com",
    "amplitude.com", "optimizely.com",
    # Social / pixel trackers
    "tiktok.com", "ads-twitter.com", "twitter.com", "pinterest.com",
    "snapchat.com", "linkedin.com",
    # Other ad networks
    "adroll.com", "quantserve.com", "adsystem.com", "bidswitch.net",
    "casalemedia.com", "contextweb.com", "districtm.net", "emxdgt.com",
    "indexexchange.com", "lijit.com", "media.net", "sovrn.com",
    "spotxchange.com", "triplelift.com", "undertone.com", "yieldmo.com",
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
    # Cloudflare
    "cdnjs.cloudflare.com", "static.cloudflareinsights.com",
    "challenges.cloudflare.com",
    # jsDelivr / unpkg / popular OSS CDNs
    "cdn.jsdelivr.net", "unpkg.com",
    # Google
    "ajax.googleapis.com", "fonts.googleapis.com", "fonts.gstatic.com",
    "apis.google.com", "www.google.com",
    # jQuery
    "code.jquery.com",
    # Bootstrap
    "stackpath.bootstrapcdn.com", "maxcdn.bootstrapcdn.com",
    "cdn.bootstrapcdn.com",
    # Tailwind / AMP
    "cdn.tailwindcss.com", "cdn.ampproject.org",
    # Microsoft
    "ajax.aspnetcdn.com", "az416426.vo.msecnd.net",
    # Payment processors (legitimate embedded JS)
    "js.stripe.com", "js.braintreegateway.com", "js.paypal.com",
    "checkout.razorpay.com",
    # E-commerce platforms
    "cdn.shopify.com", "assets.squarespace.com", "static.parastorage.com",
    "cdn.wix.com", "cdn.bigcommerce.com",
    # Common UI / utility libraries
    "cdn.auth0.com", "cdn.segment.com", "browser.sentry-cdn.com",
    "cdn.onesignal.com", "cdn.rawgit.com",
    # WordPress / Drupal infra
    "s0.wp.com", "s1.wp.com", "s2.wp.com",
}
_FREE_HOSTING_DOMAINS = {
    "pastebin.com", "paste.ee", "hastebin.com", "ghostbin.com",
    "raw.githubusercontent.com", "gist.githubusercontent.com",
}
_AD_HEAVY_THRESHOLD = 5
_OBFUSCATED_NAME_RE = re.compile(r"/[a-z0-9]{8,}\.js$", re.IGNORECASE)
_IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

_CONFUSABLE_SCRIPTS = {"CYRILLIC", "GREEK", "ARMENIAN", "CHEROKEE", "GEORGIAN"}


############################################
# This function is to extract the registrable domain from a netloc
# string by taking the last two dot-separated labels.
############################################
def _reg_domain(netloc: str) -> str:
    parts = netloc.removeprefix("www.").split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else netloc


############################################
# This function is to parse urlscan.io result data to classify all
# scripts loaded by the scanned page into ad, crypto miner, malicious,
# trusted, and suspicious categories, and return a composite risk score.
# Returns None when raw_result is absent so callers can distinguish
# "urlscan did not complete" from "page genuinely has zero scripts".
############################################
def analyze_scripts(raw_result: dict | None, initial_url: str = "") -> dict | None:
    if not raw_result:
        return None

    page_url = raw_result.get("page", {}).get("url", "") or initial_url
    page_scheme = urlparse(page_url).scheme.lower()
    scripts: list[str] = raw_result.get("lists", {}).get("scripts", [])
    if not scripts:
        seen: set[str] = set()
        for req in raw_result.get("data", {}).get("requests", []):
            resp = req.get("response", {}).get("response", {})
            url = resp.get("url", "") or req.get("request", {}).get("url", "")
            mime = resp.get("mimeType", "")
            if url and "javascript" in mime.lower() and url not in seen:
                seen.add(url)
                scripts.append(url)

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

    wappa_data = raw_result.get("meta", {}).get("processors", {}).get("wappa", {}).get("data", [])
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


############################################
# This function is to detect IDN homograph attacks by analysing each
# character in the domain using Python's unicodedata module, flagging
# domains that mix Latin with visually confusable scripts (Cyrillic,
# Greek, Armenian, Cherokee, Georgian). Never raises. Failures return
# safe defaults so the scan pipeline is never aborted.
############################################
def detect_homograph_risk(url: str) -> dict:
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


############################################
# This function is to normalise a URL to the canonical form that Google
# Safe Browsing uses internally by stripping the fragment and default
# ports so that lookup results map back correctly to the original URLs.
############################################
def _normalize_for_gsb(url: str) -> str:
    try:
        parsed = urlparse(url.strip())
        host = (parsed.hostname or "").lower()
        port = parsed.port
        netloc = f"{host}:{port}" if port and port != _GSB_DEFAULT_PORTS.get(parsed.scheme) else host
        # Strip fragment as GSB ignores it. Keep everything else intact.
        return urlunparse((parsed.scheme, netloc, parsed.path or "/", parsed.params, parsed.query, ""))
    except Exception:
        return url


############################################
# This function is to batch-check a list of URLs against the GSB v4
# threatMatches:find endpoint with exponential backoff on rate limits.
# Returns a per-URL dict without raising on API failure. Falls back
# to SUSPICIOUS so the urlscan.io pipeline still runs.
############################################
def check_google_safe_browsing(urls: list[str]) -> dict[str, dict]:
    results = {
        url: {"flagged": False, "threat_types": [], "gsb_status": "SUSPICIOUS"}
        for url in urls
    }

    # Normalize each URL to GSB's canonical form and keep a reverse map so that
    # when GSB returns a match the original URL can be keyed back from results.
    # Also include the alternate-scheme variant (http↔https) for each URL: a threat
    # listed under one scheme would otherwise be missed when the other is submitted.
    norm_to_original: dict[str, str] = {}
    for url in urls:
        norm_to_original[_normalize_for_gsb(url)] = url
        if url.startswith("http://"):
            alt = _normalize_for_gsb("https://" + url[7:])
        elif url.startswith("https://"):
            alt = _normalize_for_gsb("http://" + url[8:])
        else:
            alt = None
        if alt and alt not in norm_to_original:
            norm_to_original[alt] = url

    # v4 uses POST with a structured JSON body. API key is passed as a query param.
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
            # Network failure. Fall through to urlscan.io only.
            return results

        if response.status_code == 429 or response.status_code >= 500:
            # Exponential backoff for rate limits and server errors (cap at 32s)
            time.sleep(delay)
            delay = min(delay * 2, 32)
            continue

        if response.status_code != 200:
            # Non-blocking: other errors should not abort the overall scan
            return results

        # 200 OK. Empty body or absent 'matches' key means all URLs are clean.
        try:
            data = response.json()
        except Exception:
            # Non-JSON body (e.g. HTML error page from invalid/unenabled API key). Non-blocking.
            return results

        # v4 response:{ "matches": [{ "threat": { "url": "..." }, "threatType": "..." }] }
        for match in data.get("matches", []):
            gsb_url = match.get("threat", {}).get("url", "")
            threat_type = match.get("threatType", "")
            # GSB returns the URL in its normalised form. Map back to the original.
            # It may return a more specific path than submitted (e.g. /malware.exe
            # when the bare domain was submitted). Fall back to the sole submitted URL for
            # single-URL batches since GSB only returns matches for submitted URLs.
            original_url = (
                norm_to_original.get(gsb_url)
                or norm_to_original.get(_normalize_for_gsb(gsb_url))
                or (next(iter(norm_to_original.values())) if len(urls) == 1 else None)
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

        # GSB returned 200 OK. URLs not flagged are confirmed SAFE.
        for url_key in results:
            if not results[url_key]["flagged"]:
                results[url_key]["gsb_status"] = "SAFE"

        return results

    # All retries exhausted. Non-blocking, return safe defaults.
    return results


############################################
# This function is to submit a single URL to the urlscan.io scanning
# API and return the submission JSON containing the scan UUID, or None
# if urlscan.io is unreachable or rejects the request.
############################################
def submit_scan(url: str) -> dict | None:
    parsed = urlparse(url)
    safe_url = quote(urlunparse(parsed._replace(netloc=parsed.netloc.lower())), safe='/:?=&')
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


############################################
# This function is to poll the urlscan.io result endpoint at progressive
# intervals until the scan result is available or the maximum wait time
# is reached, returning None on timeout or unexpected errors.
############################################
def poll_result(uuid: str) -> dict | None:
    result_url = URLSCAN_RESULT_URL.format(uuid=uuid)

    time.sleep(INITIAL_WAIT_SECONDS)

    for attempt, interval in enumerate(POLL_INTERVALS):
        try:
            response = requests.get(result_url, headers={"API-Key": URLSCAN_API_KEY}, timeout=15)
        except requests.RequestException:
            return None

        if response.status_code == 200:
            return response.json()

        if response.status_code == 404:
            if attempt < MAX_POLL_ATTEMPTS - 1:
                time.sleep(interval)
            continue

        # Any other unexpected status. Give up non-fatally.
        return None

    return None


############################################
# This function is to build an ordered list of redirect URLs from the
# urlscan.io result data by parsing 3xx responses in the request log.
# Returns an empty list if there were no redirects or data is missing.
# Non-blocking. Failures must never abort the scan pipeline.
############################################
def extract_redirect_chain(initial_url: str, raw_result: dict) -> list[str]:
    if not raw_result:
        return []

    final_url = raw_result.get("page", {}).get("url", "")
    if not final_url or final_url.rstrip("/") == initial_url.rstrip("/"):
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

        return chain if chain else [initial_url, final_url]
    except Exception:
        return [initial_url, final_url]


############################################
# This function is to extract SSL/TLS certificate details from the first
# HTTPS request in the urlscan.io result that contains securityDetails.
# Returns None when SSL info is unavailable (HTTP site or scan timeout).
# Non-blocking. Failures must never abort the scan pipeline.
############################################
def extract_ssl_info(raw_result: dict | None) -> dict | None:
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


############################################
# This function is to map the urlscan.io raw result JSON to a structured
# dict, deriving the urlscan status from the malicious flag and score
# field, falling back to safe empty values if the result is absent.
############################################
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


############################################
# This function is to run the full urlscan.io pipeline for a single URL
# by submitting, polling, and processing the result, returning a fallback
# dict on any failure.
############################################
def run_urlscan(url: str) -> dict:
    submission = submit_scan(url)
    uuid = submission.get("uuid") if submission else None
    raw_result = poll_result(uuid) if uuid else None
    result = process_result(uuid, raw_result)
    result["_raw"] = raw_result  # preserved for analyze_scripts / extract_redirect_chain
    return result


############################################
# This function is to check the URL's registered domain against the
# URLRules and BlacklistRequest tables using a dedicated DB session
# for thread safety. It does not share the request's session.
############################################
def check_blacklist_db(url: str) -> dict:
    extracted = tldextract.extract(url)
    domain = extracted.registered_domain or extracted.netloc or urlparse(url).netloc
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


############################################
# This function is to query rdap.org for the registration details of
# the URL's domain and calculate the domain age in years, months, and
# days since registration.
############################################
def check_domain_rdap(url: str) -> dict:
    domain = urlparse(url).netloc.split(":")[0]
    # RDAP operates on registrable domains. Strip the leading www. if present.
    if domain.startswith("www."):
        domain = domain[4:]

    ############################################
    # This function is to return a standardised failure response dict
    # for RDAP lookup errors with all date fields set to None.
    ############################################
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
            timeout=8,
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


############################################
# This function is to derive a final scan status by combining GSB and
# urlscan.io weighted scores (GSB 55%, urlscan 45%), then applying DB
# rule overrides as the authoritative final verdict.
# MALICIOUS_THRESHOLD >= 50, SUSPICIOUS_THRESHOLD >= 30.
############################################
def compare_async_results(gsb: dict, urlscan_result: dict, blacklist_check: dict) -> str:
    # Step 1: derive scores
    threat_types = gsb.get("threat_types", [])
    if any(t in _MALICIOUS_THREATS for t in threat_types):
        gsb_score = 100
    elif any(t in _SUSPICIOUS_THREATS for t in threat_types):
        gsb_score = 60
    else:
        gsb_score = 0

    urlscan_score = urlscan_result.get("score") or 0
    # urlscan_status carries the boolean malicious flag from verdicts.overall.malicious.
    # It can be MALICIOUS even when the numeric score is low (score reflects community
    # consensus which lags the boolean verdict), so it is checked explicitly in step 3.
    urlscan_status = urlscan_result.get("urlscan_status", "SAFE")

    # Step 2: weighted combination
    weighted_score = (gsb_score * _GSB_WEIGHT) + (urlscan_score * _URLSCAN_WEIGHT)

    # Step 3: map to api_status. Explicit urlscan boolean verdict takes priority over
    # the numeric score alone, since score can be low even when malicious is true.
    if weighted_score >= _MALICIOUS_THRESHOLD or urlscan_status == "MALICIOUS":
        api_status = "MALICIOUS"
    elif weighted_score >= _SUSPICIOUS_THRESHOLD or urlscan_status == "SUSPICIOUS":
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


############################################
# This function is to process one or more URLs through the full scan
# pipeline: GSB, urlscan.io, DB blacklist, and RDAP run concurrently,
# then redirect chain, script analysis, homograph detection, and verdict
# merging are applied before saving each result to the database.
############################################
@router.post("")
def scan_url(request: ScanRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    scan_results = []
    try:
        urls = request.urls

        if not urls:
            raise HTTPException(status_code=400, detail="At least one URL is required.")

        for url in urls:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise HTTPException(status_code=400, detail=f"Invalid URL: {url}")
            if not _is_ssrf_safe(url):
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
            # initial_url = what the user submitted (always correct)
            # final_url   = page.url from urlscan (destination after all redirects)
            initial_url = url
            final_url   = urlscan_result["initial_url"] or url
            redirect_url = final_url if final_url != url else None

            redirect_chain     = extract_redirect_chain(initial_url, raw_result)

            # Supplementary GSB check on redirect destinations: the concurrent GSB
            # check only covered the initial URL. Threats may be listed under the
            # final URL (e.g. after an http to https redirect or a path redirect).
            redirect_urls = list({
                u for u in (redirect_chain or []) + ([redirect_url] if redirect_url else [])
                if u and u != initial_url
            })
            if redirect_urls:
                extra_gsb = check_google_safe_browsing(redirect_urls)
                for _, extra_result in extra_gsb.items():
                    if extra_result["flagged"]:
                        gsb["flagged"] = True
                        for t in extra_result["threat_types"]:
                            if t not in gsb["threat_types"]:
                                gsb["threat_types"].append(t)

            script_analysis    = analyze_scripts(raw_result, initial_url)
            homograph_analysis = detect_homograph_risk(initial_url)
            ssl_info           = extract_ssl_info(raw_result)

            final_status = compare_async_results(gsb, urlscan_result, blacklist_check)

            # Also check every URL in the redirect chain against URLRules.
            # The concurrent blacklist_check only covered the initial URL. A blacklisted
            # redirect target (e.g. the final destination after a short-link hop) would
            # otherwise be missed. Batch both queries to avoid N+1 per hop.
            if final_status != "MALICIOUS" and redirect_chain:
                hop_domains = []
                for hop_url in redirect_chain:
                    extracted = tldextract.extract(hop_url)
                    hop_domains.append(
                        extracted.registered_domain or extracted.netloc or urlparse(hop_url).netloc
                    )
                if hop_domains:
                    hop_blacklisted = db.query(models.URLRules).filter(
                        models.URLRules.URLDomain.in_(hop_domains),
                        models.URLRules.ListType == models.ListTypeEnum.BLACKLIST,
                    ).first()
                    hop_approved = db.query(models.BlacklistRequest).filter(
                        models.BlacklistRequest.URLDomain.in_(hop_domains),
                        models.BlacklistRequest.Status == models.RequestStatus.APPROVED,
                    ).first()
                    if hop_blacklisted or hop_approved:
                        final_status = "MALICIOUS"

            # Escalation: only applied when DB rules haven't already set MALICIOUS.
            if final_status != "MALICIOUS":
                if script_analysis:
                    if script_analysis["malicious_scripts"]:
                        final_status = "MALICIOUS"
                    elif final_status == "SAFE" and (
                        script_analysis["crypto_miners"]
                        or script_analysis["script_risk_score"] >= 70
                    ):
                        final_status = "SUSPICIOUS"
                if final_status == "SAFE" and homograph_analysis["is_homograph"]:
                    final_status = "SUSPICIOUS"

            # Classify why urlscan.io couldn't complete so the frontend can show
            # a scenario-specific message instead of a generic "unavailable".
            unavailable_reason = None
            if raw_result is None and final_status == "SAFE":
                rdap_ok = (
                    not domain_info.get("error")
                    and domain_info.get("total_days") is not None
                )
                final_status = "UNAVAILABLE"
                unavailable_reason = "scanner_blocked" if rdap_ok else "domain_unreachable"

            domain_age_days = domain_info.get("total_days")

            scan_record = models.ScanHistory(
                UserID=current_user["user_id"],
                InitialURL=initial_url,
                RedirectURL=redirect_url,
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
                GsbFlagged=gsb.get("flagged", False),
                GsbThreatTypes=gsb.get("threat_types") or [],
                Brands=urlscan_result.get("brands") or [],
                Tags=urlscan_result.get("tags") or [],
            )
            db.add(scan_record)
            db.commit()
            db.refresh(scan_record)

            scan_results.append({
                "scan_id": scan_record.ScanID,
                "user_id": current_user["user_id"],
                "uuid": urlscan_result["uuid"],
                "initial_url": initial_url,
                "redirect_url": redirect_url,
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
                "unavailable_reason": unavailable_reason,
            })

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    return scan_results
