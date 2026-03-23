# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LinksLens is a mobile-first weblink security scanner. Users submit URLs (via camera OCR, gallery image, manual input, or browser share) and receive a safety assessment. Three user roles: **User** (mobile app), **Moderator** (web portal), **Administrator** (web portal).

- **FYP Project ID:** CSIT-26-S1-05
- **Domain:** linkslens.com
- **Live Environments:**
  - `linkslens.com` — Static marketing website (Nginx serves from `/var/www/linkslens`)
  - `admin.linkslens.com` — Moderator/Admin web portal (Streamlit on port 8501)
  - `api.linkslens.com` — Backend API (FastAPI on port 8000)

## Architecture

- **Mobile App:** React Native + Expo (`linkslens-frontend/`) — UI fully implemented with NativeWind (Tailwind CSS), Expo Router, and on-device ML Kit OCR; backend integration pending
- **Admin Portal:** Streamlit (`admin/`) — fully wired to backend via `admin/models/api_client.py`; all pages use real API calls
- **Backend API:** FastAPI + Playwright Engine (`backend/`)
- **Database:** MySQL 8.0 (port 3306)
- **Server:** AWS EC2 t2.medium, Ubuntu 24.04 LTS
- **Reverse Proxy:** Nginx with Certbot SSL
- **Containerization:** Docker Compose (FastAPI + Streamlit + MySQL containers on `fyp_net` bridge network)
- **CI/CD:** GitHub Actions → SSH into EC2 → sync code, rebuild Docker, copy static HTML
- **External Services:** urlscan.io API for URL reputation scanning (`URLSCAN_API_KEY` in `.env`), Resend for transactional email (`RESEND_KEY` in `.env`)

## Actual Directory Structure

```
linkslens/
├── linkslens-frontend/   # React Native + Expo (NativeWind, Expo Router, ML Kit OCR)
│   ├── app/              # File-based routes (18 screens)
│   ├── components/       # ui-components.tsx — shared UI primitives
│   └── package.json
├── backend/
│   ├── main.py           # FastAPI entry point — registers all routers
│   ├── models.py         # All SQLAlchemy ORM models in one file
│   ├── schemas.py        # All Pydantic request/response schemas in one file
│   ├── database.py       # SQLAlchemy engine, SessionLocal, Base, get_db()
│   ├── dependencies.py   # get_current_user() and require_role() auth helpers
│   ├── seed_data.py      # Faker-based test data generator (run manually)
│   ├── controllers/      # One file per resource (CRUDL route handlers)
│   ├── requirements.txt
│   └── Dockerfile
├── admin/
│   ├── app.py            # Streamlit entry point + login
│   ├── models/
│   │   └── api_client.py # HTTP wrapper calling backend API (uses Bearer token)
│   ├── controllers/      # One file per page (auth, user, moderation, etc.)
│   ├── pages/            # Streamlit multi-page app (8 pages)
│   ├── requirements.txt
│   └── Dockerfile
├── website/              # Static HTML marketing site
├── docker-compose.yml
└── CLAUDE.md
```

## Backend Code Architecture

The backend is **flat** — all models are in `backend/models.py` and all Pydantic schemas are in `backend/schemas.py`. There is no `app/` subdirectory or `services/`/`utils/` structure yet.

**Pattern for each resource:** Each controller in `backend/controllers/` defines a FastAPI `APIRouter` with a `prefix="/api/<resource>"` and implements standard CRUDL endpoints. Routers are imported and registered in `main.py`.

**Current controllers and their prefixes:**
- `auth_controller.py` → `/api/auth` (login/logout)
- `user_role_controller.py` → `/api/roles`
- `user_account_controller.py` → `/api/accounts`
- `user_details_controller.py` → `/api/details`
- `user_preferences_controller.py` → `/api/preferences`
- `action_history_controller.py` → `/api/history`
- `app_feedback_controller.py` → `/api/feedback`
- `blacklist_request_controller.py` → `/api/blacklist-requests`
- `url_rules_controller.py` → `/api/url-rules`
- `scan_history_controller.py` → `/api/scans`
- `scan_feedback_controller.py` → `/api/scan-feedback`
- `urlscan_controller.py` → `/scan` (external scanning pipeline — not a CRUDL controller)

**Note:** API routes use `/api/` prefix, NOT `/api/v1/`. The `/scan` endpoint is an exception — it is a top-level route that drives the urlscan.io integration.

**urlscan.io scan flow (`urlscan_controller.py`):**
1. `POST /scan` receives `{ url }` from the mobile app
2. Submits to `https://urlscan.io/api/v1/scan/` using `URLSCAN_API_KEY` with `visibility: private`
3. Polls `https://urlscan.io/api/v1/result/{uuid}/` — waits 10s, then retries every 5s up to 12 attempts
4. Maps the result to: `uuid`, `status` (SAFE / SUSPICIOUS / MALICIOUS), `score`, `redirect_url`, `server_location`, `ip_address`, `screenshot_url`, `brands`, `tags`
5. Status thresholds: `malicious: true` → MALICIOUS; `score ≥ 50` → SUSPICIOUS; otherwise SAFE

**Password reset flow (`user_account_controller.py`):**
1. `POST /api/accounts/forgot-password` receives `{ EmailAddress }` — always returns a generic message (no email enumeration)
2. Generates a `secrets.token_urlsafe(32)` token, saves a `PasswordResetToken` row with 15-minute expiry
3. Sends a reset link via Resend (`RESEND_KEY` env var) from `noreply@linkslens.com`
4. `POST /api/accounts/reset-password` receives `{ Token, NewPassword }` — validates token is unused and not expired, updates `PasswordHash`, marks token as used

**Auth flow:** Login via `POST /api/auth/login` with `ClientType: "web"` or `"mobile"`. Web clients receive an HttpOnly cookie (`access_token`); mobile clients receive the JWT in the response body. Logout for web clears the cookie; logout for mobile is client-side only.

**Auth middleware (`dependencies.py`):**
- `get_current_user()` — extracts JWT from HttpOnly cookie (web) or `Authorization: Bearer` header (mobile); returns `{"user_id": int, "role_id": int}`
- `require_role(*role_ids)` — factory for route-level RBAC; usage: `Depends(require_role(1))` for admin-only, `Depends(require_role(1, 2))` for admin/moderator

**Database session:** Use `Depends(get_db)` from `database.py` to inject a session. `models.Base.metadata.create_all(bind=engine)` in `main.py` auto-creates tables on startup.

## Database (MySQL 8.0)

Database name: `LinksLens-DB`. Credentials come from environment variables (no `.env.example` checked in — see CI/CD secrets):

```
MYSQL_ROOT_PASSWORD, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD
MYSQL_HOST=db          # "db" in Docker, "localhost" for local dev
SECRET_KEY             # JWT signing key — must not have a default
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120
RESEND_KEY             # Resend API key for transactional email (password reset)
```

**Tables (11):** `UserRole`, `UserAccount`, `UserDetails`, `UserPreferences`, `AppFeedback`, `ActionHistory`, `URLRules`, `BlacklistRequest`, `ScanHistory`, `ScanFeedback`, `PasswordResetToken`

**Key relationships:** `UserAccount.RoleID → UserRole.RoleID`. Most tables cascade-delete on `UserAccount.UserID`. `ScanFeedback.ScanID → ScanHistory.ScanID`. `PasswordResetToken.UserID → UserAccount.UserID`.

**Enum columns** use Python `enum.Enum` subclasses defined in `models.py` and re-imported into `schemas.py`: `RequestStatus`, `ListTypeEnum`, `ScanStatusEnum`, `SuggestedStatusEnum`, `ClientTypeEnum`.

## Commands

```bash
# Docker (on EC2 server)
docker-compose up -d --build       # Build and start all services
docker-compose down                # Stop all services
docker-compose logs -f backend     # Tail backend logs
docker-compose logs -f admin       # Tail admin logs

# Backend (local development) — run from backend/ directory
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# API docs available at http://localhost:8000/docs

# Admin dashboard (local development)
cd admin
pip install -r requirements.txt
streamlit run app.py --server.port 8501

# Mobile app (local development)
cd linkslens-frontend
npm install
npx expo start
# Linting: npm run lint | Formatting: npm run format

# Database
mysql -u root -p LinksLens-DB < DB_Creation_Script.sql   # Initialize schema
```

## Code Style & Conventions

- **Python:** PEP 8, type hints throughout. FastAPI route handlers should be `async`.
- **TypeScript/JavaScript (Mobile):** Functional components with hooks only — no class components.
- **Naming:** snake_case for Python variables/functions, camelCase for JS/TS, PascalCase for database columns and SQLAlchemy model attributes.
- **Schemas:** Follow the existing `Base / Create / Update / Response` Pydantic schema pattern in `schemas.py`. `Response` schemas always set `model_config = ConfigDict(from_attributes=True)` (or `class Config: from_attributes = True`).
- **Controllers:** Follow existing CRUDL pattern. Use `model_dump(exclude_unset=True)` for partial updates.
- **Environment variables:** Use `python-dotenv` with `load_dotenv()`. Required secrets (e.g., `SECRET_KEY`) must raise on missing value — never silently fall back to a default.

## Security Guidelines

- **URL Input Validation:** Validate scheme (http/https only). Block private IP ranges (127.x, 10.x, 172.16-31.x, 192.168.x) and AWS metadata endpoint (169.254.169.254) to prevent SSRF.
- **Playwright Sandboxing:** Never disable browser sandboxing in production. Set timeouts and resource limits.
- **Rate Limiting:** Enforce on scan endpoints at both Nginx and FastAPI levels.
- **Password Handling:** Always use bcrypt via `passlib`. Never log or return `PasswordHash`.
- **CORS:** Restrict allowed origins to known domains only.
- **JWT:** `SECRET_KEY` must come from environment. Token payload includes `sub` (UserID as string) and `role` (RoleID).
- **Role enforcement:** All data-modifying endpoints must verify JWT and check role permissions (not yet fully implemented — currently unenforced).

## Roles & Permissions

| Role          | RoleID | Access       | Key Actions                                                  |
|---------------|--------|--------------|--------------------------------------------------------------|
| Administrator | 1      | Web portal   | Manage users, view system health, oversee moderators         |
| Moderator     | 2      | Web portal   | Review blacklist requests, resolve scan feedback             |
| User          | 3      | Mobile only  | Scan URLs, view own history, submit feedback, request blacklist |

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
24. As a user, I want to be able to associate a scan with a person so that I can track my scans to specific individuals in the future.
25. As a user, I want to be able to have seamless transfer between the application and my browser of choice so that I can have a smooth user experience.

**Account Management:**
26. As a user, I want to register a user account so that I can use the application.
27. As a user, I want to update my user account information so that my details remain accurate.
28. As a user, I want to log in to the system so that I can access the application.
29. As a user, I want to log out of the system so that I can keep my user account secure when not in use.
30. As a user, I want to reset my password via email so that I can regain access to my account if I forget my credentials.
31. As a user, I want to view and update my application preferences in one place so that I can manage all my settings conveniently.

### Moderator (Web Portal)

30. As a moderator, I want to view the domain registration age so that I can better assess the website's credibility.
31. As a moderator, I want to see the geographical location of the server hosting the website so that I can judge its credibility.
32. As a moderator, I want to see a safe static screenshot of the webpage without actually visiting it so that I can judge its credibility.
33. As a moderator, I want to be able to approve or reject user blacklist requests, so that I can update the application blacklist database.
34. As a moderator, I want to view unresolved scan feedback so that I can identify incorrectly categorised URLs.
35. As a moderator, I want to mark scan feedback as resolved so that I can track which disputes have been addressed.

### Administrator (Web Portal)

36. As an administrator, I want to be able to see an overview of the system health so that I can accurately plan for routine maintenance.
37. As an administrator, I want to be able to have my blacklist & whitelist automatically maintain so that I can better allocate manpower elsewhere.
38. As an administrator, I want to be able to perform sampling of my moderators request so that I can determine if my moderators are competent.
39. As an administrator, I want to view all user accounts so that I can manage user accounts.
40. As an administrator, I want to update user accounts so that I can make changes to user details and roles.
41. As an administrator, I want to deactivate user accounts so that inactive or invalid users are removed.
42. As an administrator, I want to view user feedback about the application so that I can plan for changes and improvements to the application.
43. As an administrator, I want to manually add a domain to the blacklist or whitelist so that I can make immediate corrections outside of the automated process.
44. As an administrator, I want to remove a domain from the blacklist or whitelist so that I can correct entries that were incorrectly flagged.
45. As an administrator, I want to view the action history of users so that I can audit activity and investigate suspicious behaviour.

## Known Limitations (FYP Scope)

- Single EC2 instance — no horizontal scaling.
- Playwright not yet integrated — `/scan` endpoint in `main.py` returns mock data.
- Mobile app UI is complete but has no backend integration — scan buttons log to console.
- `ScanHistory.RedirectURL` stores only one redirect, not the full chain.
- `UserPreferences.Preferences` is a JSON blob — not queryable field-by-field via SQL.
- `ScanFeedback` has no `CreatedAt` timestamp.
- `BlacklistRequest` has no rejection reason field.
- No Redis caching — repeated scans re-run the full pipeline.
- Role/permission enforcement on API endpoints is not yet implemented.

## Reference Documents

- `DB_Creation_Script.sql` — Full database schema
- `UserStories.txt` — Complete list of user stories
- `HighLevelArchitecture.png` — System architecture diagram
