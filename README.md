# LinksLens

**LinksLens** is a mobile-first URL security scanner that helps users determine whether a web link is safe before visiting it. Users submit URLs via camera OCR, gallery image selection, or manual input and receive an instant safety assessment powered by Google Safe Browsing and urlscan.io.

**FYP Project ID:** CSIT-26-S1-05

---

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Variables](#environment-variables)
  - [Backend (FastAPI)](#backend-fastapi)
  - [Admin Portal (Streamlit)](#admin-portal-streamlit)
  - [Mobile App (React Native + Expo)](#mobile-app-react-native--expo)
  - [Docker (Full Stack)](#docker-full-stack)
  - [Database Initialisation](#database-initialisation)
- [Live Environments](#live-environments)
- [User Roles](#user-roles)
- [Scan Pipeline](#scan-pipeline)
- [API Overview](#api-overview)
- [CI/CD](#cicd)
- [Known Limitations](#known-limitations)

---

## Features

### Mobile App (Users)
- Scan URLs via **camera OCR**, **QR code camera scanner**, **gallery image**, or **manual input**
- **QR phishing detection ("quishing")** — live camera decodes QR codes and runs them through the full security pipeline
- Instant **SAFE / SUSPICIOUS / MALICIOUS** verdict with score
- View **redirect chains** and **server location**
- **IDN Homograph detection** — flags Unicode-spoofed domains (e.g., Cyrillic 'а' replacing Latin 'a')
- Browse **scan history** with search and filter
- Submit **scan feedback** to flag incorrect results
- Submit **blacklist requests** for suspicious domains
- Dark / Light theme toggle
- Account registration, login, and **password reset via email** — `forgot-password.html` (email entry) and `reset-password.html` (token-based new password form) served from the static site; rate-limited to 3 requests per email and 10 per IP per hour

### Admin Portal (Moderators & Administrators)
- **Dashboard** — system health overview (user counts, scan stats, service status)
- **Moderation** — review and approve/reject user blacklist requests
- **Scan Feedback** — view and resolve disputed scan results
- **URL Registry** — manually add/remove domains from blacklist or whitelist
- **User Management** — view, update, and deactivate user accounts
- **App Feedback** — review feedback submitted by users
- **Action History Log** — audit trail of all user activity
- **Scan History** — browse all historical scans across all users
- **Threat Intelligence** — global threat heatmap (Folium) + recent defanged malicious/suspicious scan feed

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                        Clients                           │
│  ┌──────────────────┐       ┌──────────────────────────┐ │
│  │  Mobile App       │       │  Admin/Mod Web Portal    │ │
│  │  React Native     │       │  Streamlit               │ │
│  │  (Expo)           │       │  admin.linkslens.com     │ │
│  └────────┬─────────┘       └──────────┬───────────────┘ │
└───────────┼──────────────────────────── ┼────────────────┘
            │  HTTPS (JWT Bearer)          │  HTTPS (Cookie)
            ▼                             ▼
┌──────────────────────────────────────────────────────────┐
│              Nginx Reverse Proxy (SSL/TLS)                │
│                     linkslens.com                        │
└──────────────────┬───────────────────────────────────────┘
                   │
       ┌───────────▼────────────┐
       │   FastAPI Backend      │
       │   api.linkslens.com    │  :8000
       │   (Docker container)   │
       └───────────┬────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
  ┌──────────┐     ┌─────────────────────┐
  │ MySQL 8  │     │  External APIs       │
  │ :3306    │     │  - Google Safe       │
  │ (Docker) │     │    Browsing v4       │
  └──────────┘     │  - urlscan.io        │
                   │  - Resend (email)    │
                   └─────────────────────┘
```

All three backend services (FastAPI, MySQL, Streamlit) run in Docker containers on a shared `fyp_net` bridge network. Ports are bound to `127.0.0.1` only — Nginx is the sole public entry point.

---

## Project Structure

```
CSIT321-LinksLens/
├── backend/                   # FastAPI REST API
│   ├── controllers/           # 12 APIRouter controllers (one per resource)
│   ├── main.py                # App entry point, router registration
│   ├── models.py              # SQLAlchemy ORM models + ScanRequest schema
│   ├── schemas.py             # Pydantic request/response schemas
│   ├── database.py            # DB engine and session factory
│   ├── dependencies.py        # JWT auth middleware and RBAC helpers
│   ├── utils.py               # Shared helpers (hashing, name formatting)
│   ├── seed_data.py           # Seed script for roles and test users
│   ├── requirements.txt
│   └── Dockerfile
│
├── admin/                     # Streamlit admin/moderator portal
│   ├── pages/                 # 8 Streamlit pages (Dashboard → Scan Feedback)
│   ├── controllers/           # Business logic per page
│   ├── models/api_client.py   # HTTP client wrapping the backend API
│   ├── app.py                 # Entry point (login page)
│   ├── config.py              # Backend URL config
│   └── utils.py
│
├── linkslens-frontend/        # React Native + Expo mobile app
│   ├── app/                   # 18 screens (Expo Router file-based routing)
│   ├── lib/
│   │   ├── api.ts             # All backend API calls + token management
│   │   ├── types.ts           # Shared TypeScript types
│   │   └── navigation.tsx     # Navigation helpers
│   ├── components/            # Reusable UI components
│   └── assets/                # Icons, splash screens, images
│
├── website/                   # Static marketing site (served by Nginx)
│   ├── index.html
│   ├── forgot-password.html   # Email entry form for password reset
│   ├── reset-password.html    # Token-based new password form
│   └── style.css
│
├── docker-compose.yml         # Orchestrates backend + db + admin
├── DB_Creation_Script.sql     # Full MySQL schema
└── .github/workflows/
    └── deploy.yml             # GitHub Actions CI/CD to AWS EC2
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Mobile App | React Native + Expo 55, NativeWind (Tailwind CSS), Expo Router |
| Admin Portal | Python 3, Streamlit |
| Backend API | Python 3, FastAPI, SQLAlchemy |
| Database | MySQL 8.0 |
| Authentication | JWT (Bearer token for mobile, HttpOnly cookie for web) |
| URL Scanning | Google Safe Browsing v4, urlscan.io |
| Email | Resend (`noreply@linkslens.com`) |
| OCR | ML Kit Text Recognition (on-device, Android) |
| Containerisation | Docker, Docker Compose |
| Server | AWS EC2 t3.medium, Ubuntu 24.04 LTS |
| Reverse Proxy | Nginx + Certbot (SSL) |
| CI/CD | GitHub Actions |

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- Docker and Docker Compose
- MySQL 8.0 (for local dev without Docker)
- Android device or emulator (for mobile app)
- Expo CLI: `npm install -g expo-cli`

### Environment Variables

Create a `.env` file in the project root (used by Docker Compose) or in `backend/` for local development:

```env
# Database
MYSQL_ROOT_PASSWORD=your_root_password
MYSQL_DATABASE=LinksLens-DB
MYSQL_USER=your_db_user
MYSQL_PASSWORD=your_db_password
MYSQL_HOST=db                        # Use "localhost" for local dev (without Docker)

# JWT
SECRET_KEY=your_secret_key_here      # Must be set — no default
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120

# External APIs
URLSCAN_API_KEY=your_urlscan_key
GOOGLE_SAFE_BROWSING_API_KEY=your_gsb_key
RESEND_KEY=your_resend_key
```

For the mobile app, create `linkslens-frontend/.env`:
```env
EXPO_PUBLIC_API_URL=https://api.linkslens.com   # Or http://10.0.2.2:8000 for local Android emulator
```

---

### Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`

---

### Admin Portal (Streamlit)

```bash
cd admin
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

Portal available at `http://localhost:8501`

---

### Mobile App (React Native + Expo)

> The app uses ML Kit OCR and `expo-secure-store`, both native modules. **Expo Go is not supported** — a custom dev client or release build is required.

```bash
cd linkslens-frontend
npm install

# Development (requires connected Android device or emulator)
npx expo run:android

# Build release APK
npx expo run:android --variant release
# Output: android/app/build/outputs/apk/release/app-release.apk

# Clean rebuild (required after changing icons, splash, or native config)
npx expo prebuild --clean
npx expo run:android
```

---

### Docker (Full Stack)

```bash
# Build and start all services (backend + db + admin)
docker compose up -d --build

# Stop all services
docker compose down

# View backend logs
docker compose logs -f backend
```

---

### Database Initialisation

```bash
# Create schema
mysql -u root -p LinksLens-DB < DB_Creation_Script.sql

# Seed initial data (roles, test users)
python backend/seed_data.py
```

---

## Live Environments

| URL | Service | Description |
|---|---|---|
| `linkslens.com` | Static site | Marketing landing page + `forgot-password` and `reset-password` pages (Nginx, `/var/www/linkslens`) |
| `api.linkslens.com` | FastAPI | REST API backend (port 8000) |
| `admin.linkslens.com` | Streamlit | Moderator and Administrator web portal (port 8501) |

---

## User Roles

| Role | ID | Access | Responsibilities |
|---|---|---|---|
| Administrator | 1 | Web portal | Manage all users, system health, URL rules, oversee moderators |
| Moderator | 2 | Web portal | Review blacklist requests, resolve scan feedback disputes |
| User | 3 | Mobile app | Scan URLs, view own history, submit feedback |

---

## Scan Pipeline

`POST /scan` accepts a URL (or list of URLs) and runs the following steps:

1. **Google Safe Browsing v4** — batch lookup against Google's threat database; exponential backoff on rate limits; failures fall back to SUSPICIOUS so the pipeline continues
2. **urlscan.io submission** — submits each URL for full page analysis (public visibility)
3. **Result polling** — waits 10s, then polls every 5s for up to 70s total
4. **Script-level analysis** — `analyze_scripts()` classifies scripts from the urlscan.io result (ad networks, crypto miners, malicious domains, obfuscated filenames, etc.)
5. **Homograph detection** — `detect_homograph_risk()` uses `unicodedata` (stdlib) to detect Unicode script mixing in domain labels (e.g., Cyrillic + Latin); IDN homographs on an otherwise-safe page are escalated to SUSPICIOUS
6. **Verdict merge** — most severe result wins:
   - GSB `MALWARE` / `SOCIAL_ENGINEERING` → **MALICIOUS**
   - GSB `UNWANTED_SOFTWARE` / `POTENTIALLY_HARMFUL_APPLICATION` → **SUSPICIOUS**
   - urlscan.io `malicious: true` → **MALICIOUS**
   - urlscan.io `score ≥ 50` → **SUSPICIOUS**
   - Crypto miners detected → at least **SUSPICIOUS**
   - IDN homograph detected → at least **SUSPICIOUS**
   - Otherwise → **SAFE**
7. **URLRules override** — domain in `URLRules` table takes final precedence: BLACKLIST → MALICIOUS, WHITELIST → SAFE
8. **Persist** — saves result to `ScanHistory` including redirect URL, server location, screenshot URL, script analysis, and homograph analysis

---

## API Overview

All routes are prefixed with `/api/` except the scan endpoint.

| Controller | Prefix | Notes |
|---|---|---|
| Auth | `/api/auth` | Login (web cookie / mobile JWT), logout |
| User Accounts | `/api/accounts` | CRUDL + forgot/reset password |
| User Details | `/api/details` | Profile information |
| User Preferences | `/api/preferences` | Settings JSON blob |
| User Roles | `/api/roles` | Role management |
| Scan History | `/api/scans` | Per-user scan records |
| Scan Feedback | `/api/scan-feedback` | Dispute incorrect scan results |
| Blacklist Requests | `/api/blacklist-requests` | User-submitted domain flag requests |
| URL Rules | `/api/url-rules` | Admin-managed blacklist/whitelist |
| App Feedback | `/api/feedback` | General app feedback |
| Action History | `/api/history` | Audit log |
| URL Scanner | `/scan` | Main scan pipeline (not a CRUDL endpoint) |

**Auth:** Mobile uses `Authorization: Bearer <token>`. Web uses HttpOnly cookie. JWT payload: `{ sub: UserID, role: RoleID, exp }`.

---

## CI/CD

Pushing to `main` triggers a GitHub Actions workflow that:

1. SSHs into the AWS EC2 instance
2. Hard-resets the server repo to match `origin/main`
3. Writes all secrets into a `.env` file on the server
4. Copies `website/` to `/var/www/linkslens` (Nginx static files)
5. Runs `docker compose up -d --build --remove-orphans`
6. Prunes unused Docker images

Required GitHub secrets: `HOST`, `USERNAME`, `SSH_KEY`, `DB_ROOT_PASSWORD`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `RESEND_API_KEY`, `URLSCAN_API_KEY`, `GOOGLE_SAFE_BROWSING_API_KEY`

---

## Known Limitations

- Single EC2 instance — no horizontal scaling or load balancing
- Most mobile screens (settings, preferences, browser selection) are UI stubs not yet wired to the backend
- `ScanHistory.RedirectURL` stores only the final redirect, not the full chain
- `UserPreferences.Preferences` is an unstructured JSON blob — not queryable field-by-field
- `ScanFeedback` has no `CreatedAt` timestamp
- `BlacklistRequest` has no rejection reason field
- No caching — repeated scans re-run the full pipeline each time
