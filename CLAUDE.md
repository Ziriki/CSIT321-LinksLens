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
- **Backend API:** FastAPI (`backend/`) — real scan pipeline using Google Safe Browsing + urlscan.io
- **Database:** MySQL 8.0 (port 3306)
- **Server:** AWS EC2 t2.medium, Ubuntu 24.04 LTS
- **Reverse Proxy:** Nginx with Certbot SSL
- **Containerization:** Docker Compose (FastAPI + Streamlit + MySQL on `fyp_net` bridge network)
- **CI/CD:** GitHub Actions → SSH into EC2 → sync code, rebuild Docker, copy static HTML
- **External Services:** urlscan.io API (`URLSCAN_API_KEY`), Google Safe Browsing v5 (`GOOGLE_SAFE_BROWSING_API_KEY`), Resend for email (`RESEND_KEY`)

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

The backend is **flat** — all models are in `backend/models.py`, all Pydantic schemas in `backend/schemas.py`. No `app/` subdirectory or `services/`/`utils/` structure.

**Controller pattern:** Each controller in `backend/controllers/` defines a FastAPI `APIRouter` with `prefix="/api/<resource>"` and implements standard CRUDL endpoints. All routers are imported and registered in `main.py`.

**Controllers and their prefixes:**
- `auth_controller.py` → `/api/auth` (login/logout)
- `user_role_controller.py` → `/api/roles`
- `user_account_controller.py` → `/api/accounts` (includes forgot/reset-password)
- `user_details_controller.py` → `/api/details`
- `user_preferences_controller.py` → `/api/preferences`
- `action_history_controller.py` → `/api/history`
- `app_feedback_controller.py` → `/api/feedback`
- `blacklist_request_controller.py` → `/api/blacklist-requests`
- `url_rules_controller.py` → `/api/url-rules`
- `scan_history_controller.py` → `/api/scans`
- `scan_feedback_controller.py` → `/api/scan-feedback`
- `url_scan_controller.py` → `/scan` (external scanning pipeline — not a CRUDL controller)

**Note:** API routes use `/api/` prefix. The `/scan` endpoint is the exception — it is top-level and drives the full scan pipeline.

**`/scan` pipeline (`url_scan_controller.py`):**
1. `POST /scan` accepts `{ "urls": str | list[str] }` — single string or list, always normalised to a list
2. **Google Safe Browsing v5** — batch `GET /v5alpha1/urls:search` with all URLs in one round-trip; exponential backoff on 429/5xx; non-blocking (failures fall through to urlscan.io)
3. **urlscan.io** — each URL submitted separately to `POST /api/v1/scan/` with `visibility: public`; result polled after 10s initial wait then every 5s up to 12 attempts
4. Verdicts merged — most severe status wins: GSB `MALWARE/SOCIAL_ENGINEERING` → MALICIOUS; GSB `UNWANTED_SOFTWARE/POTENTIALLY_HARMFUL_APPLICATION` → SUSPICIOUS; urlscan.io `malicious: true` → MALICIOUS; urlscan.io `score ≥ 50` → SUSPICIOUS; otherwise SAFE
5. Each result saved to `ScanHistory`; returns a list of result objects (one per URL)

`POST /scan` accepts `{ urls: string | string[] }` and returns an array of results.

**Pipeline per URL:**
1. **Google Safe Browsing v5** — batch GET to `safebrowsing.googleapis.com/v5alpha1/urls:search`; non-blocking (returns SAFE defaults on failure)
2. **urlscan.io submission** — POST to `urlscan.io/api/v1/scan/` with `visibility: public`
3. **Poll for result** — waits 10s, then polls every 5s up to 12 attempts (70s total timeout)
4. **Merge verdicts** — most severe status wins between GSB and urlscan.io
5. **Save to `ScanHistory`** — stores `InitialURL`, `RedirectURL`, `StatusIndicator`, `ServerLocation`, `ScreenshotURL`

**Status thresholds:** `malicious: true` → MALICIOUS; `score ≥ 50` → SUSPICIOUS; otherwise SAFE.

**Response shape per URL:**
```json
{
  "scan_id", "initial_url", "redirect_url", "status_indicator",
  "score", "server_location", "screenshot_url", "brands", "tags",
  "result_url", "gsb_flagged", "gsb_threat_types", "scanned_at"
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

**Password reset flow (`user_account_controller.py`):**
1. `POST /api/accounts/forgot-password` → generates token, saves `PasswordResetToken` row (15-min expiry), sends link via Resend from `noreply@linkslens.com`
2. `POST /api/accounts/reset-password` → validates token is unused/unexpired, updates `PasswordHash`, marks token used

## Mobile App (`linkslens-frontend/`)

**Routing:** Expo Router (file-based). All screens live in `app/`. `_layout.tsx` is the root stack — `setColorScheme` must be inside `useEffect`, not called directly during render.

**API client:** `lib/api.ts` — `API_BASE_URL` defaults to `https://api.linkslens.com` (override with `EXPO_PUBLIC_API_URL`).

**Auth (implemented):**
- `index.tsx` → calls `login(email, password)` from `lib/api.ts` → `POST /api/auth/login` with `ClientType: "mobile"` → JWT stored via `expo-secure-store`
- `lib/api.ts` exports `saveToken`, `getToken`, `clearToken`, `authHeaders()` — all authenticated requests use `authHeaders()` which attaches `Authorization: Bearer <token>`
- `expo-secure-store` is registered as an Expo plugin in `app.json` and is a native module — requires `expo run:android` build

**Scan flow (implemented):**
- `scan.tsx` → user picks OCR image or manual entry
- `scan-image.tsx` → ML Kit OCR extracts text, editable `TextInput` lets user correct it, navigates to `scan-processing` with `url` param
- `scan-link.tsx` → manual URL entry, navigates to `scan-processing`
- `scan-processing.tsx` → calls `scanUrl(url)` from `lib/api.ts` → `POST /scan` (with JWT) → navigates to `scan-results`
- `scan-results.tsx` → displays `status_indicator`, `score`, `gsb_threat_types`, `initial_url`

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

**Tables (11):** `UserRole`, `UserAccount`, `UserDetails`, `UserPreferences`, `AppFeedback`, `ActionHistory`, `URLRules`, `BlacklistRequest`, `ScanHistory`, `ScanFeedback`, `PasswordResetToken`

**Enum columns** defined as Python `enum.Enum` subclasses in `models.py`, re-imported into `schemas.py`: `RequestStatus`, `ListTypeEnum`, `ScanStatusEnum`, `SuggestedStatusEnum`, `ClientTypeEnum`.

## Code Style & Conventions

- **Python:** PEP 8, type hints throughout. FastAPI route handlers should be `async`. Required env vars must `raise ValueError` on missing — never fall back silently.
- **TypeScript/JavaScript:** Functional components with hooks only. No class components.
- **Naming:** snake_case for Python, camelCase for JS/TS, PascalCase for DB columns and SQLAlchemy model attributes.
- **Schemas:** Follow the `Base / Create / Update / Response` Pydantic pattern in `schemas.py`. `Response` schemas always set `model_config = ConfigDict(from_attributes=True)`.
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

## Reference Documents

- `DB_Creation_Script.sql` — Full database schema
- `UserStories.txt` — Complete list of user stories
- `HighLevelArchitecture.png` — System architecture diagram
