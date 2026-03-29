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

**Note:** API routes use `/api/` prefix. The `/scan` endpoint is the exception — it is top-level and drives the full scan pipeline. System health is at `/api/health` (admin only).

**`/scan` pipeline (`url_scan_controller.py`):**
`POST /scan` accepts `{ "urls": str | list[str] }` — single string or list, always normalised to a list. Returns an array of results (one per URL).

1. **Google Safe Browsing v4** — batch `POST` to `safebrowsing.googleapis.com/v4/threatMatches:find` with all URLs in one round-trip; exponential backoff on 429/5xx; non-blocking (failures return SUSPICIOUS defaults so urlscan.io still runs)
2. **urlscan.io submission** — each URL submitted separately to `POST urlscan.io/api/v1/scan/` with `visibility: public`
3. **Poll for result** — waits 10s, then polls every 5s up to 12 attempts (70s total timeout)
4. **Merge verdicts** — most severe status wins: GSB `MALWARE/SOCIAL_ENGINEERING` → MALICIOUS; GSB `UNWANTED_SOFTWARE/POTENTIALLY_HARMFUL_APPLICATION` → SUSPICIOUS; urlscan.io `malicious: true` → MALICIOUS; urlscan.io `score ≥ 50` → SUSPICIOUS; otherwise SAFE
5. **WHOIS domain age** — `get_domain_age_days(domain)` does a WHOIS lookup and computes the domain's age in days; saved to `ScanHistory.DomainAgeDays`; non-blocking (failures return `None`)
6. **Check internal URLRules** — if the domain is in the `URLRules` table, BLACKLIST overrides to MALICIOUS, WHITELIST overrides to SAFE (admin/moderator rules have final say)
7. **Save to `ScanHistory`** — stores `InitialURL`, `RedirectURL`, `StatusIndicator`, `DomainAgeDays`, `ServerLocation`, `ScreenshotURL`

**Response shape per URL:**
```json
{
  "scan_id", "user_id", "uuid", "initial_url", "redirect_url",
  "status_indicator", "score", "domain_age_days", "server_location", "ip_address",
  "screenshot_url", "brands", "tags", "result_url",
  "scanned_at", "gsb_flagged", "gsb_threat_types"
}
```

## Auth Flow

**Login:** `POST /api/auth/login` with `{ EmailAddress, Password, ClientType: "web"|"mobile" }`.
- Web → HttpOnly cookie (`access_token`)
- Mobile → JWT returned in response body (`access_token` field)

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

**Token security:** Both `EmailVerificationToken` and `PasswordResetToken` store only the SHA-256 hash of the raw token in the database. The raw token is sent to the user; the hash is stored. `hash_token()`, `normalize_expiry()`, and `send_email()` in `utils.py` are shared across all token endpoints.

**Design decision:** Password reset is web-only. The mobile "Forgot Password?" button opens `https://linkslens.com/reset-password` in the device browser via `Linking.openURL`. No in-app reset screen.

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
- `scan-processing.tsx` → calls `scanUrl(url)` from `lib/api.ts` → `POST /scan` (with JWT) → navigates to `scan-results`
- `scan-results.tsx` → displays `status_indicator`, `score`, `gsb_threat_types`, `initial_url`

**Shared frontend utilities:**
- `lib/types.ts` — `statusToRisk()`, `countScansThisMonth()`, shared TypeScript types
- `lib/navigation.tsx` — `bottomNavItems` shared across all screens with the bottom nav bar

**Not yet implemented (UI stubs):** Scan history loading, profile, feedback submission, all settings screens.

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
- `ScanHistory.RedirectURL` stores only one redirect, not the full chain.
- `UserPreferences.Preferences` is a JSON blob — not queryable field-by-field.
- `ScanFeedback` has no `CreatedAt` timestamp.
- `BlacklistRequest` has no rejection reason field.
- No Redis caching — repeated scans re-run the full pipeline.
- WHOIS lookups in the scan pipeline may time out on some domains; `DomainAgeDays` will be `null` in those cases.

## User Stories

### User (Mobile App)

**URL Input & Scanning:**
1. As a user, I want to use my device camera to take photos of links so that I can perform a URL scan.
2. As a user, I want to select images from my photo gallery so that I can scan URLs from past images.
3. As a user, I want to manually input a URL into the application so that I can still use the application if the image scan doesn't work.
4. As a user, I want to share my current browsing link to the application so that I don't have to open the app to share a link.

**Scan Results & Display:**
5. As a user, I want the system to display link redirects so that I can see the actual destination of shortened links.
6. As a user, I want to be able to toggle between different scan result modes so that I can read my scan in different levels of detail.
7. As a user, I want to see a status indicator of the website immediately after scanning so that I will easily understand if it is safe to open.
8. As a user, I want to view the raw text content of the page so that I can read articles without advertisements.
9. As a user, I want to export a scan report so that I can share the scan results to other people.
10. As a user, I want to be able to share my scan report directly to messaging apps so that I can message others about the scan quickly.

**Scan History:**
11. As a user, I want to see my scan history so that I can track what I browsed in the past.
12. As a user, I want to search my scan history by keywords to find a specific scan.
13. As a user, I want to filter my scan history by status indicator of the scan so that I can easily view scans that matter to me.
14. As a user, I want to clear my entire scan history so that I can protect my privacy.

**Feedback & Requests:**
15. As a user, I want to log feedback about a scan so that I can alert the system where there is an incorrect categorization.
16. As a user, I want to submit a domain blacklist request so that I can flag a suspicious website for moderator review.
17. As a user, I want to submit feedback about the application so that I can report issues or suggest improvements to the team.

**Preferences & UX:**
18. As a user, I want to toggle between Dark and Light themes so that I can view the application comfortably around different light sources.
19. As a user, I want the device to vibrate when a scan completes so that I am physically alerted.
20. As a user, I want to receive a push notification when a scan is completed so that I am alerted.
21. As a user, I want to select my preferred browser so that I can start using the link after a scan.
22. As a user, I want to receive a tutorial when I first open the app that I can learn how to use the application.
23. As a user, I want to select the language of my scan report so that I can share it to others without manually translating.
24. As a user, I want to be able to have seamless transfer between the application and my browser of choice so that I can have a smooth user experience.

**Account Management:**
25. As a user, I want to register a user account so that I can use the application.
26. As a user, I want to update my user account information so that my details remain accurate.
27. As a user, I want to log in to the system so that I can access the application.
28. As a user, I want to log out of the system so that I can keep my user account secure when not in use.
29. As a user, I want to reset my password via email so that I can regain access to my account if I forget my credentials.
30. As a user, I want to view and update my application preferences in one place so that I can manage all my settings conveniently.

### Moderator (Web Portal)

31. As a moderator, I want to view the domain registration age so that I can better assess the website's credibility.
32. As a moderator, I want to see the geographical location of the server hosting the website so that I can judge its credibility.
33. As a moderator, I want to see a safe static screenshot of the webpage without actually visiting it so that I can judge its credibility.
34. As a moderator, I want to be able to approve or reject user blacklist requests, so that I can update the application blacklist database.
35. As a moderator, I want to view unresolved scan feedback so that I can identify incorrectly categorised URLs.
36. As a moderator, I want to mark scan feedback as resolved so that I can track which disputes have been addressed.

### Administrator (Web Portal)

37. As an administrator, I want to be able to see an overview of the system health so that I can accurately plan for routine maintenance.
38. As an administrator, I want to view all user accounts so that I can manage user accounts.
39. As an administrator, I want to update user accounts so that I can make changes to user details and roles.
40. As an administrator, I want to deactivate user accounts so that inactive or invalid users are removed.
41. As an administrator, I want to view user feedback about the application so that I can plan for changes and improvements to the application.
42. As an administrator, I want to manually add a domain to the blacklist or whitelist so that I can make immediate corrections outside of the automated process.
43. As an administrator, I want to remove a domain from the blacklist or whitelist so that I can correct entries that were incorrectly flagged.
44. As an administrator, I want to view the action history of users so that I can audit activity and investigate suspicious behaviour.
