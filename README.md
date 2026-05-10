# LinksLens

**LinksLens** is a mobile-first URL security scanner. Users submit links via camera OCR, QR code scanning, gallery image, or manual input and receive an instant safety verdict powered by Google Safe Browsing v4, urlscan.io sandbox analysis, script-level inspection, and IDN homograph detection.

| | |
|---|---|
| **FYP Group** | FYP-26-S1-03P |
| **Spec** | CSIT-26-S1-05 |
| **Platform** | Android (mobile app), Web (admin portal) |
| **Domain** | [linkslens.com](https://linkslens.com) |

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
- [Security](#security)
- [Team](#team)

---

## Features

### Mobile App (Users)

- Scan URLs via **camera OCR**, **QR code scanner**, **gallery image selection**, or **manual input**
- **QR phishing detection ("quishing")** — decodes QR codes live and runs them through the full security pipeline
- **SAFE / SUSPICIOUS / MALICIOUS** verdict with a risk score, screenshot preview, and detailed analysis (script risk, tech stack, ad detection)
- **IDN homograph detection** — flags Unicode-spoofed domains (e.g. Cyrillic 'а' replacing Latin 'a')
- View **redirect chains** and **server location** for every scan
- **Open scanned URL** in a preferred browser (Chrome, Firefox, Edge, or system default) directly from results
- **Export scan report** as an image to the device gallery
- **Android share intent** — pipe any link from another app straight into LinksLens
- Browse **scan history** with keyword search and status filter; clear entire history
- Submit **scan feedback** to flag incorrect verdicts; submit **app feedback** to report issues
- **Haptic feedback** on scan completion
- Dark / Light theme toggle; **onboarding tutorial** on first launch
- Account registration, email verification, profile editing, and **password reset via email** with per-email and per-IP rate limiting

### Admin Portal (Moderators & Administrators)

- **Dashboard** — system health overview (user counts, scan stats, external service status)
- **Moderation** — review and approve/reject user-submitted blacklist requests
- **Scan Feedback** — view and resolve disputed scan verdicts
- **URL Registry** — manually add or remove domains from the blacklist or whitelist
- **User Management** — view, update, and deactivate user accounts
- **App Feedback** — review feedback submitted by mobile users
- **Action History Log** — full audit trail of user activity
- **Scan History** — browse all historical scans across all users; scan new URLs directly from the portal
- **Threat Intelligence** — global threat heatmap (Folium) with clickable country zoom and a live feed of recent malicious/suspicious scans

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                          Clients                            │
│  ┌───────────────────┐        ┌───────────────────────────┐ │
│  │   Mobile App      │        │  Admin / Mod Web Portal   │ │
│  │   React Native    │        │  Streamlit                │ │
│  │   (Expo)          │        │  admin.linkslens.com      │ │
│  └─────────┬─────────┘        └────────────┬──────────────┘ │
└────────────┼─────────────────────────────── ┼───────────────┘
             │  HTTPS (JWT Bearer)             │  HTTPS (Cookie)
             ▼                                ▼
┌─────────────────────────────────────────────────────────────┐
│               Nginx Reverse Proxy (SSL/TLS)                 │
│                       linkslens.com                         │
└───────────────────────┬─────────────────────────────────────┘
                        │
            ┌───────────▼────────────┐
            │    FastAPI Backend     │
            │    api.linkslens.com   │  :8000
            │    (Docker container)  │
            └───────────┬────────────┘
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
       ┌──────────┐    ┌──────────────────────┐
       │ MySQL 8  │    │   External APIs       │
       │  :3306   │    │   · Google Safe       │
       │ (Docker) │    │     Browsing v4       │
       └──────────┘    │   · urlscan.io        │
                       │   · Resend (email)    │
                       └──────────────────────┘
```

All backend services (FastAPI, MySQL, Streamlit) run in Docker containers on a shared `fyp_net` bridge network. Ports are bound to `127.0.0.1` only — Nginx is the sole public entry point.

---

## Project Structure

```
CSIT321-LinksLens/
├── backend/                   # FastAPI REST API
│   ├── controllers/           # 12 APIRouter controllers (one per resource)
│   ├── main.py                # App entry point and router registration
│   ├── models.py              # SQLAlchemy ORM models + ScanRequest schema
│   ├── schemas.py             # Pydantic request/response schemas
│   ├── database.py            # DB engine and session factory
│   ├── dependencies.py        # JWT auth middleware and RBAC helpers
│   ├── utils.py               # Shared helpers (hashing, email, name formatting)
│   ├── seed_data.py           # Seed script for roles and test users
│   ├── requirements.txt
│   └── Dockerfile
│
├── admin/                     # Streamlit admin/moderator portal
│   ├── pages/                 # 9 Streamlit pages (Dashboard → Threat Intelligence)
│   ├── controllers/           # Business logic per page
│   ├── models/api_client.py   # HTTP client wrapping the backend API
│   ├── app.py                 # Entry point (login page)
│   ├── config.py              # Backend URL configuration
│   └── utils.py               # Shared UI helpers (pagination, search, status colours)
│
├── linkslens-frontend/        # React Native + Expo mobile app
│   ├── app/                   # Screens (Expo Router file-based routing)
│   ├── lib/
│   │   ├── api.ts             # All backend API calls + token management
│   │   ├── types.ts           # Shared TypeScript types and enums
│   │   ├── notifications.ts   # Push notification helpers
│   │   ├── browsers.ts        # Browser deep-link map
│   │   └── navigation.tsx     # Bottom navigation config
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
    └── deploy.yml             # GitHub Actions CI/CD pipeline to AWS EC2
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Mobile App | React Native + Expo, NativeWind (Tailwind CSS), Expo Router |
| Admin Portal | Python 3, Streamlit |
| Backend API | Python 3, FastAPI, SQLAlchemy |
| Database | MySQL 8.0 |
| Authentication | JWT (Bearer token for mobile, HttpOnly cookie for web) |
| URL Scanning | Google Safe Browsing v4, urlscan.io |
| OCR | ML Kit Text Recognition (on-device, Android) |
| Email | Resend (`noreply@linkslens.com`) |
| Containerisation | Docker, Docker Compose |
| Server | AWS EC2 t3.medium, Ubuntu 24.04 LTS |
| Reverse Proxy | Nginx + Certbot (Let's Encrypt SSL) |
| CI/CD | GitHub Actions |

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- Docker and Docker Compose
- MySQL 8.0 (for local development without Docker)
- Android device or emulator
- Expo CLI: `npm install -g expo-cli`

---

### Environment Variables

Create a `.env` file in the project root (for Docker Compose) or in `backend/` for local development:

```env
# Database
MYSQL_ROOT_PASSWORD=your_root_password
MYSQL_DATABASE=LinksLens-DB
MYSQL_USER=your_db_user
MYSQL_PASSWORD=your_db_password
MYSQL_HOST=db                        # Use "localhost" for local dev (no Docker)

# JWT
SECRET_KEY=your_secret_key_here      # Required — no default
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120

# External APIs
URLSCAN_API_KEY=your_urlscan_key
GOOGLE_SAFE_BROWSING_API_KEY=your_gsb_key
RESEND_KEY=your_resend_key
```

For the mobile app, create `linkslens-frontend/.env`:

```env
EXPO_PUBLIC_API_URL=https://api.linkslens.com
# For local Android emulator: http://10.0.2.2:8000
```

---

### Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs are available at `http://localhost:8000/docs` (local development only).

---

### Admin Portal (Streamlit)

```bash
cd admin
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

Portal available at `http://localhost:8501`.

---

### Mobile App (React Native + Expo)

> The app uses ML Kit OCR and `expo-secure-store`, both native modules. **Expo Go is not supported** — a custom dev client or release build is required.

```bash
cd linkslens-frontend
npm install

# Development build (requires a connected Android device or emulator)
npx expo run:android

# Release APK
npx expo run:android --variant release
# Output: android/app/build/outputs/apk/release/app-release.apk

# Clean rebuild (required after changing icons, splash screen, or native config)
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

# Tail backend logs
docker compose logs -f backend
```

---

### Database Initialisation

```bash
# Create schema
mysql -u root -p LinksLens-DB < DB_Creation_Script.sql

# Seed initial roles and test users
python backend/seed_data.py
```

---

## Live Environments

| URL | Service | Description |
|---|---|---|
| `linkslens.com` | Static site | Marketing landing page + password reset pages (Nginx, `/var/www/linkslens`) |
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

`POST /scan` accepts a single URL or a list of up to 10 URLs. Four checks run concurrently per URL via `ThreadPoolExecutor`, then post-processing operates on the data already in memory:

1. **Google Safe Browsing v4** — batch lookup against Google's threat database; exponential backoff on rate limits
2. **urlscan.io** — submits each URL for full sandboxed page analysis (public visibility); raw result retained for downstream steps
3. **RDAP domain age** — queries `rdap.org` for registration date and age breakdown; non-blocking
4. **DB blacklist check** — checks `URLRules` and approved `BlacklistRequest` entries

Post-processing (sequential, ~0ms each):

5. **Result polling** — waits 3s, then polls at progressive intervals for up to ~89s total
6. **Redirect chain** — built from `data.requests` in the urlscan.io result; no extra network call
7. **SSL/TLS info** — extracted from the first HTTPS request in the urlscan.io result that contains security details
8. **Script analysis** — classifies scripts from urlscan.io's `data.lists.scripts` (ad networks, crypto miners, malicious CDNs, obfuscated filenames, mixed content, Wappalyzer tech stack)
9. **Homograph detection** — uses `unicodedata` (stdlib) to detect Unicode script mixing in domain labels (e.g. Cyrillic + Latin)
10. **Verdict merge** — most severe result wins:
    - GSB `MALWARE` / `SOCIAL_ENGINEERING` → **MALICIOUS**
    - GSB `UNWANTED_SOFTWARE` / `POTENTIALLY_HARMFUL_APPLICATION` → **SUSPICIOUS**
    - urlscan.io `malicious: true` → **MALICIOUS**
    - urlscan.io `score ≥ 50` → **SUSPICIOUS**
    - Known malicious script CDN loaded → **MALICIOUS**
    - Crypto miners or IDN homograph detected → at least **SUSPICIOUS**
    - Otherwise → **SAFE**
11. **URLRules override** — a matching entry in the `URLRules` table takes final precedence: BLACKLIST → MALICIOUS, WHITELIST → SAFE
12. **Persist** — saves result to `ScanHistory` with `InitialURL`, `RedirectURL`, `RedirectChain`, `StatusIndicator`, `DomainAgeDays`, `ServerLocation`, `IpAddress`, `AsnName`, `PageTitle`, `ApexDomain`, `SslInfo`, `ScreenshotURL`, `ScriptAnalysis`, `HomographAnalysis`, `GsbFlagged`, `GsbThreatTypes`, `Brands`, `Tags`

---

## API Overview

All routes are prefixed `/api/` except the scan endpoint.

| Controller | Prefix | Notes |
|---|---|---|
| Auth | `/api/auth` | Login (web cookie / mobile JWT), logout |
| User Accounts | `/api/accounts` | CRUDL + register, email verification, forgot/reset password |
| User Details | `/api/details` | Profile information |
| User Preferences | `/api/preferences` | Settings JSON blob |
| User Roles | `/api/roles` | Role management |
| Scan History | `/api/scans` | Per-user scan records |
| Scan Feedback | `/api/scan-feedback` | Dispute incorrect scan verdicts |
| Blacklist Requests | `/api/blacklist-requests` | User-submitted domain flag requests |
| URL Rules | `/api/url-rules` | Admin-managed blacklist/whitelist |
| App Feedback | `/api/feedback` | General app feedback |
| Action History | `/api/history` | Audit log |
| URL Scanner | `/scan` | Main scan pipeline (not a CRUDL endpoint) |

**Auth:** Mobile clients send `Authorization: Bearer <token>`. Web clients use an HttpOnly cookie. JWT payload: `{ sub: UserID, role: RoleID, exp }`.

Interactive API docs are available at `http://localhost:8000/docs` (local development only — disabled in production).

---

## CI/CD

Pushing to `main` triggers a GitHub Actions workflow that:

1. SSHs into the AWS EC2 instance
2. Hard-resets the server repository to match `origin/main`
3. Writes all secrets into a `.env` file on the server
4. Copies `website/` to `/var/www/linkslens` (Nginx static files)
5. Runs `docker compose up -d --build --remove-orphans`
6. Prunes unused Docker images

**Required GitHub secrets:** `HOST`, `USERNAME`, `SSH_KEY`, `DB_ROOT_PASSWORD`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `RESEND_API_KEY`, `URLSCAN_API_KEY`, `GOOGLE_SAFE_BROWSING_API_KEY`

---

## Security

### Infrastructure (Nginx)

**HTTPS enforcement** — All HTTP traffic (port 80) is redirected to HTTPS via `301` across all domains. TLS certificates are issued by Let's Encrypt (Certbot) with strong DH parameters (`ssl-dhparams.pem`).

**Server version suppression** — `server_tokens off` prevents Nginx from disclosing its version in response headers and error pages.

**Security headers** — Applied at the reverse-proxy level so they are present on every response regardless of the backend:

| Header | `api.linkslens.com` | `admin.linkslens.com` | `linkslens.com` |
|---|---|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | `max-age=31536000; includeSubDomains` | `max-age=31536000; includeSubDomains` |
| `X-Frame-Options` | `DENY` | `SAMEORIGIN` | `DENY` |
| `X-Content-Type-Options` | `nosniff` | `nosniff` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | `strict-origin-when-cross-origin` | `no-referrer` |
| `Content-Security-Policy` | — | — | (see below) |

> `no-referrer` on the main site prevents the password reset token from leaking via the HTTP `Referer` header when the user clicks the reset link.

**Content Security Policy (main site):**
```
default-src 'self';
script-src 'self' https://cdn.tailwindcss.com 'unsafe-inline';
style-src 'self' 'unsafe-inline';
connect-src 'self' https://api.linkslens.com;
img-src 'self' data:;
font-src 'self';
object-src 'none';
frame-ancestors 'none';
base-uri 'self';
form-action 'self' https://api.linkslens.com
```

**Rate limiting** — API requests are limited to 30 requests/minute per IP (`limit_req_zone`), with a burst allowance of 10 requests using `nodelay` to reject excess traffic immediately rather than queuing it.

**Active threat blocking** — The API server block drops connections (`return 444` — no response) for:
- Common scanner and vulnerability probe paths (`.env`, `.git`, `actuator`, `wp-login`, `swagger`, `phpinfo`, etc.)
- Non-standard HTTP methods (only `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS` are permitted)
- Known vulnerability scanner user agents (`masscan`, `zgrab`, `nuclei`, `sqlmap`, `nikto`, `nmap`, `dirbuster`, and others)

**WebSocket proxying** — The admin portal block passes `Upgrade` and `Connection` headers to support Streamlit's WebSocket-based live updates.

---

### Application (FastAPI)

| Threat | Mitigation |
|---|---|
| JWT secret missing at startup | `ValueError` raised — server refuses to start |
| Login brute-force | DB-based rate limit: 10 failures per IP per 15 min → 429; counter resets on success |
| SSRF via scan endpoint | Hostname resolved to IP; private, loopback, link-local, and multicast ranges rejected before scanning |
| Unbounded scan input | Max 10 URLs per request; 422 returned if exceeded |
| Scan ID enumeration (403 vs 404) | Unauthorised scan access returns 404 to prevent probing other users' scans |
| Feedback UserID spoofing | `UserID` overridden from JWT; scan ownership verified server-side |
| Email enumeration on registration | Duplicate email returns a generic 400 message |
| Blacklist request spam | Max 5 submissions per user per day → 429 |
| Password reset rate limiting | Per-email (3/hr) + per-IP (10/hr); sweep-invalidates all unused tokens on successful reset |
| Password reset token in Referer header | `<meta name="referrer" content="no-referrer">` on static reset pages |
| Token storage | Only SHA-256 hashes stored in DB; raw tokens sent to users only |

---

## Team

**FYP-26-S1-03P** — Final Year Project, CSIT-26-S1-05

| Name | Role |
|---|---|
| Stephanie Yap Yen Yee | Team Leader |
| Chong Meng Zhi | Full-Stack Developer |
| Siow Wen Sheng Tobias Ezra | Frontend Developer |
| Ryan Lim Ruiyan | Backend Developer |
