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

- **Mobile App:** React Native + Expo (`linkslens-frontend/`) — currently scaffolded, not yet implemented
- **Admin Portal:** Streamlit (`admin/`) — currently a stub with mock data; has `controllers/`, `models/`, `pages/` subdirectories
- **Backend API:** FastAPI + Playwright Engine (`backend/`)
- **Database:** MySQL 8.0 (port 3306)
- **Server:** AWS EC2 t2.medium, Ubuntu 24.04 LTS
- **Reverse Proxy:** Nginx with Certbot SSL
- **Containerization:** Docker Compose (FastAPI + Streamlit + MySQL containers on `fyp_net` bridge network)
- **CI/CD:** GitHub Actions → SSH into EC2 → sync code, rebuild Docker, copy static HTML
- **External Services:** Google Safe Browsing v5 (`GOOGLE_SAFE_BROWSING_API_KEY`) + urlscan.io (`URLSCAN_API_KEY`)

## Actual Directory Structure

```
linkslens/
├── mobile-app/           # React Native + Expo (stub only)
├── backend/
│   ├── main.py           # FastAPI entry point — registers all routers
│   ├── models.py         # All SQLAlchemy ORM models in one file
│   ├── schemas.py        # All Pydantic request/response schemas in one file
│   ├── database.py       # SQLAlchemy engine, SessionLocal, Base, get_db()
│   ├── controllers/      # One file per resource (CRUDL route handlers)
│   ├── requirements.txt
│   └── Dockerfile
├── admin/
│   ├── app.py            # Streamlit entry point (stub with mock data)
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
- `url_scan_controller.py` → `/scan` (external scanning pipeline — not a CRUDL controller)

**Note:** API routes use `/api/` prefix, NOT `/api/v1/`. The `/scan` endpoint is an exception — it is a top-level route that drives the urlscan.io integration.

**`/scan` pipeline (`url_scan_controller.py`):**
1. `POST /scan` accepts `{ "urls": str | list[str] }` — single string or list, always normalised to a list
2. **Google Safe Browsing v5** — batch `GET /v5alpha1/urls:search` with all URLs in one round-trip; exponential backoff on 429/5xx; non-blocking (failures fall through to urlscan.io)
3. **urlscan.io** — each URL submitted separately to `POST /api/v1/scan/` with `visibility: public`; result polled after 10s initial wait then every 5s up to 12 attempts
4. Verdicts merged — most severe status wins: GSB `MALWARE/SOCIAL_ENGINEERING` → MALICIOUS; GSB `UNWANTED_SOFTWARE/POTENTIALLY_HARMFUL_APPLICATION` → SUSPICIOUS; urlscan.io `malicious: true` → MALICIOUS; urlscan.io `score ≥ 50` → SUSPICIOUS; otherwise SAFE
5. Each result saved to `ScanHistory`; returns a list of result objects (one per URL)

**Auth flow:** Login via `POST /api/auth/login` with `ClientType: "web"` or `"mobile"`. Web clients receive an HttpOnly cookie (`access_token`); mobile clients receive the JWT in the response body. Logout for web clears the cookie; logout for mobile is client-side only.

**Database session:** Use `Depends(get_db)` from `database.py` to inject a session. `models.Base.metadata.create_all(bind=engine)` in `main.py` auto-creates tables on startup.

## Database (MySQL 8.0)

Database name: `LinksLens-DB`. Credentials come from environment variables (see `.env.example`).

**Tables (10):** `UserRole`, `UserAccount`, `UserDetails`, `UserPreferences`, `AppFeedback`, `ActionHistory`, `URLRules`, `BlacklistRequest`, `ScanHistory`, `ScanFeedback`

**Key relationships:** `UserAccount.RoleID → UserRole.RoleID`. Most tables cascade-delete on `UserAccount.UserID`. `ScanFeedback.ScanID → ScanHistory.ScanID`.

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

# Mobile app (local development) — not yet implemented
cd mobile-app
npm install
npx expo start

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

## Known Limitations (FYP Scope)

- Single EC2 instance — no horizontal scaling.
- Playwright not yet integrated — `/scan` currently delegates entirely to urlscan.io; local browser analysis is not yet implemented.
- Admin dashboard is a stub with hardcoded mock data; not yet connected to the real database.
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
