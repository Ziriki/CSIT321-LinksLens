# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LinksLens is a mobile-first weblink security scanner. Users submit URLs (via camera OCR, gallery image, or manual input) and receive a safety assessment. Three user roles: **User** (mobile app), **Moderator** (web portal), **Administrator** (web portal).

- **FYP Project ID:** CSIT-26-S1-05
- **Domain:** linkslens.com
- **Live Environments:**
  - `linkslens.com` — Static marketing website (Nginx serves from `/var/www/linkslens`)
  - `admin.linkslens.com` — Moderator/Admin web portal (Streamlit on port 8501)
  - `api.linkslens.com` — Backend API (FastAPI on port 8000)

## Project Spec Requirements

The official project spec (CSIT-26-S1-05) lists these key functionalities. All must be fulfilled:

| Requirement | Status | Implementation |
|---|---|---|
| URL observation from browser or camera captures | ✅ Done | ML Kit OCR (`scan-image.tsx`), manual input (`scan-link.tsx`), Android share intent (pending) |
| Link security analysis against common security risks | ✅ Done | Google Safe Browsing v4 + urlscan.io in `/scan` pipeline |
| Security notification | ✅ Done | `expo-notifications` local push on scan complete (`lib/notifications.ts`) |
| Comprehensive security analysis based on script level inspection | ✅ Done | `analyze_scripts()` in `url_scan_controller.py` — classifies scripts from urlscan.io result |
| Potentially reduce Ad intensive websites | ✅ Done | `ad_heavy` flag + `ad_count` in `ScriptAnalysis` — surfaced in scan response |

## Architecture

- **Mobile App:** React Native + Expo (`linkslens-frontend/`) — NativeWind (Tailwind CSS), Expo Router, on-device ML Kit OCR. Scan pipeline wired to backend; auth and most other screens still UI-only stubs.
- **Admin Portal:** Streamlit (`admin/`) — fully wired to backend via `admin/models/api_client.py`
- **Backend API:** FastAPI (`backend/`) — real scan pipeline using Google Safe Browsing v4 + urlscan.io
- **Database:** MySQL 8.0 (port 3306)
- **Server:** AWS EC2 t2.medium, Ubuntu 24.04 LTS
- **Reverse Proxy:** Nginx with Certbot SSL
- **Containerization:** Docker Compose (FastAPI + Streamlit + MySQL on `fyp_net` bridge network)
- **CI/CD:** GitHub Actions → SSH into EC2 → sync code, rebuild Docker, copy static HTML
- **External Services:** urlscan.io API (`URLSCAN_API_KEY`), Google Safe Browsing v4 (`GOOGLE_SAFE_BROWSING_API_KEY`), Resend for email (`RESEND_KEY`)

## Commands

```bash
# Docker (on EC2 server)
docker-compose up -d --build       # Build and start all services
docker-compose down                # Stop all services
docker-compose logs -f backend     # Tail backend logs

# Backend (local development) — run from backend/ directory
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# API docs at http://localhost:8000/docs

# Admin dashboard (local development)
cd admin
pip install -r requirements.txt
streamlit run app.py --server.port 8501

# Mobile app — development
cd linkslens-frontend
npm install
npx expo start --dev-client        # Requires custom dev client (MLKit is a native module)

# Mobile app — build release APK
npx expo run:android --variant release
# Output: android/app/build/outputs/apk/release/app-release.apk

# Mobile app — clean rebuild (after changing native assets/icons)
npx expo prebuild --clean
npx expo run:android

# Mobile app — clear stale Gradle build cache
cd android && gradlew.bat clean && cd ..   # Windows
npx expo run:android --variant release

# Mobile linting/formatting
npm run lint
npm run format

# Database
mysql -u root -p LinksLens-DB < DB_Creation_Script.sql   # Initialize schema
```

## Backend Code Architecture

The backend is **flat** — all models are in `backend/models.py`, all Pydantic schemas in `backend/schemas.py` (exception: `ScanRequest` Pydantic model lives in `models.py`). Shared helpers are in `backend/utils.py` (`get_fullname`, `get_password_hash`, `verify_password`, `hash_token`, `normalize_expiry`, `send_email`).

**Controller pattern:** Each controller in `backend/controllers/` defines a FastAPI `APIRouter` with `prefix="/api/<resource>"` and implements standard CRUDL endpoints. All routers are imported and registered in `main.py`.

**Controllers and their prefixes:**
- `auth_controller.py` → `/api/auth` (login/logout)
- `user_role_controller.py` → `/api/roles`
- `user_account_controller.py` → `/api/accounts` (includes register, verify-email, forgot-password, reset-password)
- `user_details_controller.py` → `/api/details`
- `user_preferences_controller.py` → `/api/preferences`
- `action_history_controller.py` → `/api/history`
- `app_feedback_controller.py` → `/api/feedback`
- `blacklist_request_controller.py` → `/api/blacklist-requests`
- `url_rules_controller.py` → `/api/url-rules`
- `scan_history_controller.py` → `/api/scans`
- `scan_feedback_controller.py` → `/api/scan-feedback`
- `url_scan_controller.py` → `/scan` (external scanning pipeline — not a CRUDL controller)

**Note:** API routes use `/api/` prefix. The `/scan` endpoint is the exception — it is top-level and drives the full scan pipeline. System health is at `/api/health` (admin only) — live-checks all external services and returns operational work-queue metrics.

**`/scan` pipeline (`url_scan_controller.py`):**
`POST /scan` accepts `{ "urls": str | list[str] }` — single string or list, always normalised to a list. Returns an array of results (one per URL).

**Parallelism:** GSB runs first (single batch round-trip). Then all URLs are processed in parallel via `ThreadPoolExecutor` — each URL runs urlscan.io + WHOIS concurrently inside its own inner executor. DB operations are always in the main thread (SQLAlchemy sessions are not thread-safe). Total scan time is ~18–22s regardless of URL count.

1. **Google Safe Browsing v4** — batch `POST` to `safebrowsing.googleapis.com/v4/threatMatches:find`; exponential backoff on 429/5xx; non-blocking
2. **urlscan.io submission** — each URL submitted to `POST urlscan.io/api/v1/scan/` with `visibility: public`; runs concurrently with WHOIS per URL
3. **Poll for result** — waits 10s, then polls every 5s up to 12 attempts (70s total timeout)
4. **WHOIS domain age** — `get_domain_age_days(domain)` runs concurrently with urlscan.io polling; non-blocking (failures return `None`)
5. **Script-level analysis** — `analyze_scripts(raw_result)` parses urlscan.io result for: ad networks, crypto miners, known malicious script domains, IP-hosted scripts, mixed content (HTTP on HTTPS), free-hosting abuse, obfuscated filenames, trusted CDN recognition, technology stack (Wappalyzer), and a composite `script_risk_score` (0–100). Crypto miners on an otherwise-SAFE page → escalated to SUSPICIOUS.
6. **Merge verdicts** — most severe wins: GSB `MALWARE/SOCIAL_ENGINEERING` → MALICIOUS; GSB `UNWANTED_SOFTWARE/POTENTIALLY_HARMFUL_APPLICATION` → SUSPICIOUS; urlscan.io `malicious: true` → MALICIOUS; urlscan.io `score ≥ 50` → SUSPICIOUS; crypto miners found → at least SUSPICIOUS; otherwise SAFE. If urlscan.io failed entirely AND GSB has no signal → UNAVAILABLE
7. **Check internal URLRules** — BLACKLIST overrides to MALICIOUS, WHITELIST overrides to SAFE (final say)
8. **Save to `ScanHistory`** — stores `InitialURL`, `RedirectURL`, `RedirectChain`, `StatusIndicator`, `DomainAgeDays`, `ServerLocation`, `ScreenshotURL`, `ScriptAnalysis`

**Response shape per URL:**
```json
{
  "scan_id", "user_id", "uuid", "initial_url", "redirect_url", "redirect_chain",
  "status_indicator", "score", "domain_age_days", "server_location", "ip_address",
  "screenshot_url", "brands", "tags", "result_url", "scanned_at",
  "gsb_flagged", "gsb_threat_types",
  "script_analysis": {
    "total", "trusted_count", "ad_count", "ad_heavy",
    "crypto_miners", "malicious_scripts", "suspicious_patterns",
    "tech_stack", "script_risk_score"
  }
}
```

## Auth Flow

**Login:** `POST /api/auth/login` with `{ EmailAddress, Password, ClientType: "web"|"mobile" }`.
- Web → HttpOnly cookie (`access_token`) **+ token in response body** (so Streamlit portal can read it)
- Mobile → JWT returned in response body only

**Client type enforcement (login):**
- Admin (RoleID 1) and Moderator (RoleID 2) → must use `ClientType: "web"` — rejected with 403 if mobile
- User (RoleID 3) → must use `ClientType: "mobile"` — rejected with 403 if web
- Admin portal (`admin/models/api_client.py`) sends `ClientType: "web"` and reads token from response body

**JWT payload:** `{ sub: UserID (string), role: RoleID, exp }`

**Auth middleware (`dependencies.py`):**
- `get_current_user()` — extracts JWT from cookie (web) or `Authorization: Bearer` header (mobile); returns `{"user_id": int, "role_id": int}`
- `require_role(*role_ids)` — route-level RBAC; e.g. `Depends(require_role(1))` for admin-only

**Registration & email verification flow (`user_account_controller.py`):**
1. `POST /api/accounts/register` — creates account with `IsActive=False`, creates `UserDetails` with `FullName`, generates SHA-256-hashed `EmailVerificationToken` (24h expiry), sends verification link via Resend
2. `POST /api/accounts/verify-email` — validates token is unused/unexpired, sets `IsActive=True`, marks token used
3. Login on an unverified account returns HTTP 403 "Please verify your email address before logging in."

**Password reset flow (`user_account_controller.py`):**
1. `POST /api/accounts/forgot-password` → generates token, saves `PasswordResetToken` row (15-min expiry), sends link via Resend from `noreply@linkslens.com`
2. `POST /api/accounts/reset-password` → validates token is unused/unexpired, updates `PasswordHash`, marks token used

**Token security:** Both `EmailVerificationToken` and `PasswordResetToken` store only the SHA-256 hash of the raw token in the database. `hash_token()`, `normalize_expiry()`, and `send_email()` in `utils.py` are shared across all token endpoints.

**Design decision:** Password reset is web-only. The mobile "Forgot Password?" button opens `https://linkslens.com/reset-password` in the device browser via `Linking.openURL`. No in-app reset screen.

## Admin Portal (`admin/`)

**Pages and role access:**

| Page | Admin | Moderator |
|---|:---:|:---:|
| `1_Dashboard.py` — System health | ✅ | ❌ hidden |
| `2_Blacklist_Requests.py` — Review blacklist requests | ✅ | ✅ |
| `3_User_Management.py` — Manage user accounts | ✅ | ❌ hidden |
| `4_App_Feedback.py` — View app feedback | ✅ | ❌ hidden |
| `5_Action_History_Log.py` — Audit log | ✅ | ❌ hidden |
| `6_URL_Registry.py` — Blacklist/whitelist domains | ✅ | ✅ |
| `7_Scan_History.py` — All scan records | ✅ | ✅ |
| `8_Scan_Feedback.py` — Resolve scan disputes | ✅ | ✅ |

**Sidebar hiding:** `_hide_pages_for_moderator()` in `admin/controllers/auth_controller.py` injects CSS to hide admin-only pages. Called from both `require_role()` and `render_sidebar()` so it applies on every page including the home page. Selectors match on filename substrings (`1_Dashboard`, `3_User_Management`, etc.) — list stored in `_MODERATOR_HIDDEN_PAGES` module-level constant.

**Session state:** Auth stores `"_decoded_user"` dict (not `"user_id"`). `require_role()` return value must be captured as `current_user`. `_decoded_user` is cleared at the start of every `handle_login()` call to prevent stale cache from previous sessions.

## Mobile App (`linkslens-frontend/`)

**Routing:** Expo Router (file-based). All screens live in `app/`. `_layout.tsx` is the root stack — `setColorScheme` must be inside `useEffect`, not called directly during render.

**API client:** `lib/api.ts` — `API_BASE_URL` defaults to `https://api.linkslens.com` (override with `EXPO_PUBLIC_API_URL`).

**Auth (implemented):**
- `index.tsx` → calls `login(email, password)` from `lib/api.ts` → `POST /api/auth/login` with `ClientType: "mobile"` → JWT stored via `expo-secure-store`
- `signup.tsx` → calls `signup(fullName, email, password)` → `POST /api/accounts/register` → shows "check your email" confirmation screen
- `lib/api.ts` exports `saveToken`, `getToken`, `clearToken`, `authHeaders()` — all authenticated requests use `authHeaders()` which attaches `Authorization: Bearer <token>`
- `expo-secure-store` is registered as an Expo plugin in `app.json` and is a native module — requires `expo run:android` build

**Scan flow (implemented):**
- `scan.tsx` → user picks OCR image or manual entry
- `scan-image.tsx` → ML Kit OCR extracts text, editable `TextInput` lets user correct it, navigates to `scan-processing` with `url` param
- `scan-link.tsx` → manual URL entry, navigates to `scan-processing`
- `scan-processing.tsx` → shows simulated progress messages timed to backend pipeline steps (7 stages, 0–21s) → calls `scanUrl(url)` → on result fires local push notification via `lib/notifications.ts` → navigates to `scan-results`
- `scan-results.tsx` → displays `status_indicator`, `score`, `gsb_threat_types`, `initial_url`

**Notifications (`lib/notifications.ts`):**
- `initNotificationHandler()` — called in `_layout.tsx` on startup; sets foreground banner behaviour
- `requestNotificationPermission()` — called in `_layout.tsx`; prompts OS permission dialog on first launch
- `notifyScanComplete(status, url)` — fires immediate local notification; fails silently
- `expo-notifications ~0.31.2` registered as Expo plugin in `app.json`; requires rebuild after adding

**Types (`lib/types.ts`):**
- `ScanStatus` — `'SAFE' | 'SUSPICIOUS' | 'MALICIOUS' | 'UNAVAILABLE'` (backend status values)
- `RiskLevel` — `'safe' | 'suspicious' | 'malicious'` (frontend display values)
- `statusToRisk()`, `countScansThisMonth()`, shared interfaces

**Not yet implemented (UI stubs):** Scan history loading, profile, feedback submission, all settings screens. `script_analysis` data from scan response not yet displayed.

**MLKit note:** `@infinitered/react-native-mlkit-text-recognition` is a native module — requires `expo run:android` (custom dev client), not Expo Go.

**Icon/splash changes:** Require `npx expo prebuild --clean` + `npx expo run:android` to take effect. Uninstall the old APK from the device first.

## Database (MySQL 8.0)

Database name: `LinksLens-DB`.

**Required environment variables:**
```
MYSQL_ROOT_PASSWORD, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD
MYSQL_HOST=db          # "db" in Docker, "localhost" for local dev
SECRET_KEY             # JWT signing key — must not have a default
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120
URLSCAN_API_KEY
GOOGLE_SAFE_BROWSING_API_KEY
RESEND_KEY
```

**Tables (12):** `UserRole`, `UserAccount`, `UserDetails`, `UserPreferences`, `AppFeedback`, `ActionHistory`, `URLRules`, `BlacklistRequest`, `ScanHistory`, `ScanFeedback`, `PasswordResetToken`, `EmailVerificationToken`

**`ScanHistory` columns (current):** `ScanID`, `UserID`, `InitialURL`, `RedirectURL`, `RedirectChain` (JSON), `StatusIndicator` (ENUM incl. UNAVAILABLE), `DomainAgeDays`, `ServerLocation`, `ScreenshotURL`, `ScriptAnalysis` (JSON), `ScannedAt`

**Pending DB migrations (must be run on server if not yet applied):**
```sql
ALTER TABLE `ScanHistory`
  ADD COLUMN `RedirectChain` JSON NULL AFTER `RedirectURL`;

ALTER TABLE `ScanHistory`
  MODIFY COLUMN `StatusIndicator`
  ENUM('SAFE','SUSPICIOUS','MALICIOUS','UNAVAILABLE','PENDING') NOT NULL DEFAULT 'PENDING';

ALTER TABLE `ScanHistory`
  ADD COLUMN `ScriptAnalysis` JSON NULL AFTER `ScreenshotURL`;

-- Run only if columns still exist (were removed from model):
ALTER TABLE `ScanHistory`
  DROP COLUMN `RawText`,
  DROP COLUMN `AssociatedPerson`;
```

**Connection pool:** `pool_pre_ping=True, pool_recycle=3600` on the SQLAlchemy engine — prevents "MySQL server has gone away" errors on long-idle connections.

**Enum columns** defined as Python `enum.Enum` subclasses in `models.py`, re-imported into `schemas.py`: `RequestStatus`, `ListTypeEnum`, `ScanStatusEnum`, `SuggestedStatusEnum`, `ClientTypeEnum`.

## Code Style & Conventions

- **Python:** PEP 8, type hints throughout. Route handlers use sync `def` (not `async`). Required env vars must `raise ValueError` on missing — never fall back silently.
- **TypeScript/JavaScript:** Functional components with hooks only. No class components.
- **Naming:** snake_case for Python, camelCase for JS/TS, PascalCase for DB columns and SQLAlchemy model attributes.
- **Schemas:** Follow the `Base / Create / Update / Response` Pydantic pattern in `schemas.py`. `Response` schemas always set `class Config: from_attributes = True`.
- **Partial updates:** Use `model_dump(exclude_unset=True)` in PUT handlers.

## Roles & Permissions

| Role          | RoleID | Access     | Key Actions                                              |
|---------------|--------|------------|----------------------------------------------------------|
| Administrator | 1      | Web portal | Manage users, system health, URL rules, oversee mods     |
| Moderator     | 2      | Web portal | Review blacklist requests, resolve scan feedback         |
| User          | 3      | Mobile app | Scan URLs, view own history, submit feedback             |

## Known Limitations (FYP Scope)

- Single EC2 instance — no horizontal scaling.
- Most mobile screens (history, profile, feedback, settings) are UI-only stubs with no backend calls.
- `UserPreferences.Preferences` is a JSON blob — not queryable field-by-field.
- `ScanFeedback` has no `CreatedAt` timestamp.
- `BlacklistRequest` has no rejection reason field.
- No Redis caching — repeated scans re-run the full pipeline.
- WHOIS lookups in the scan pipeline may time out on some domains; `DomainAgeDays` will be `null` in those cases.
- Script analysis `_MALICIOUS_SCRIPT_DOMAINS` list is manually maintained — not fetched from a live threat feed.

## User Stories

### User (Mobile App)

**Account Management:**
1. As a user, I want to register a user account so that I can use the application.
2. As a user, I want to update my user account information so that my details remain accurate.
3. As a user, I want to log in to the system so that I can access the application.
4. As a user, I want to log out of the system so that I can keep my user account secure when not in use.
5. As a user, I want to reset my password so that I can recover my account.

**URL Input & Scanning:**
6. As a user, I want to manually input a URL into the application so that I can still use the application if the image scan doesn't work.
7. As a user, I want to select images from my photo gallery so that I can scan URLs from past images.
8. As a user, I want to use my device camera to take photos of links so that I can perform a URL scan.
9. As a user, I want the application to capture photos directly from my camera so that I can upload photos easily.
10. As a user, I want to receive a push notification when a scan is completed so that I am alerted.

**Scan Results & Display:**
11. As a user, I want to see a status indicator of the website immediately after scanning so that I will easily understand if it is safe to open.
12. As a user, I want to be able to toggle between different scan result modes so that I can read my scan in different levels of detail.
13. As a user, I want to see a safe static screenshot of the webpage without actually visiting it so that I can judge its credibility.
14. As a user, I want the system to display link redirects so that I can see the actual destination of shortened links.

**Scan History:**
15. As a user, I want to see my scan history so that I can track what I browsed in the past.
16. As a user, I want to search my scan history by keywords to find a specific scan.
17. As a user, I want to filter my scan history by status indicator of the scan so that I can easily view scans that matter to me.
18. As a user, I want to clear my entire scan history so that I can protect my privacy.
19. As a user, I want to export a scan report as an image so that I can share the scan results to other people.

**Feedback:**
20. As a user, I want to log feedback about a scan so that I can alert the system where there is an incorrect categorization.

**Preferences & UX:**
21. As a user, I want to select my preferred browser so that I can start using the link after a scan.
22. As a user, I want the device to vibrate when a scan completes so that I am physically alerted.
23. As a user, I want to toggle between Dark and Light themes so that I can view the application comfortably around different light sources.
24. As a user, I want to share my current browsing link to the application so that I don't have to open the app to share a link.
25. As a user, I want to receive a tutorial when I first open the app that I can learn how to use the application.

### Moderator (Web Portal)

26. As a moderator, I want to submit malicious URLs so that I can update the application blacklist database.
27. As a moderator, I want to see the geographical location of the server hosting the website so that I can judge its credibility.
28. As a moderator, I want to view the domain registration age so that I can better assess the website's credibility.

### Administrator (Web Portal)

29. As an administrator, I want to view all user accounts so that I can manage user accounts.
30. As an administrator, I want to update user accounts so that I can make changes to user details and roles.
31. As an administrator, I want to deactivate user accounts so that inactive or invalid users are removed.
32. As an administrator, I want to be able to see an overview of the system health so that I can accurately plan for routine maintenance.
33. As an administrator, I want to view user feedback about the application so that I can plan for changes and improvements to the application.
