# AI Training for Everyone: LMS (Ruiru, Kenya)

A learning platform for the three course paths (Beginner, Intermediate, Advanced), themed from the programme poster.
Learners **choose one path when they sign up**, then follow 20 daily lessons with labs, self-checks, notes, progress, streaks and a certificate.

**Stack:** React 18 + Vite + Tailwind CSS &middot; Flask + SQLAlchemy &middot; PostgreSQL &middot; Google sign-in (OAuth 2.0 / OpenID Connect) &middot; Docker Compose.

## What is inside

| Area | Features |
|---|---|
| Public site | Poster-style landing page, the three paths, what you will learn, workspace perks, WhatsApp booking |
| Sign-up | Step 1 choose a path, step 2 continue with Google. The path is stored on the new account |
| Learner app | Dashboard (progress ring, streak, achievements, today's action), course roadmap, lessons, resources, glossary, profile, certificate |
| Lesson page | Objectives, concepts, worked template or code, lab checklist (saved), practice prompts with copy, self-check quiz (score saved), takeaways, glossary, homework, autosaved notes |
| Resources | Per-path downloads: notes handbook, printable workbook, 20 slide decks (ZIP), outline. Only your own path's files |
| AI Coach (optional) | Chat that turns the lesson into one action. Off until `ANTHROPIC_API_KEY` is set |
| Trainer dashboard | Admins see learners by path, progress, and can move a learner to another path |

The 60 lessons and the downloadable materials are the content produced earlier for each path (`backend/seed_data`, `backend/resources`).

## Run it with Docker (recommended)

```bash
cp .env.example .env        # fill in SECRET_KEY, GOOGLE_CLIENT_ID, ADMIN_EMAILS
docker compose up --build   # open http://localhost:8080
```
The backend creates the tables and loads the course content on every start (safe to repeat).

## Google sign-in (do this once)

1. Go to Google Cloud Console, **APIs & Services > OAuth consent screen**. Choose External, add the app name and your email, publish when ready.
2. **Credentials > Create credentials > OAuth client ID > Web application.**
3. Under **Authorised JavaScript origins** add `http://localhost:8080`, `http://localhost:5173` (dev server) and your real domain (`https://learn.yourdomain.com`). No redirect URI is needed for the popup button.
4. Copy the Client ID into `.env` as `GOOGLE_CLIENT_ID` and rebuild (`docker compose up --build`); the frontend bakes it in at build time.
5. Put your own email in `ADMIN_EMAILS`. When you first sign in with that email you become an administrator.

How it works: the browser gets a signed ID token from Google; Flask verifies it (signature, audience, issuer, verified email) and issues its own HttpOnly session cookie. Passwords are never handled.

## Local development without Docker

```bash
# 1. database
docker run -d --name lms-db -e POSTGRES_USER=lms -e POSTGRES_PASSWORD=lms -e POSTGRES_DB=lms -p 5432:5432 postgres:16-alpine

# 2. backend  (http://localhost:5000)
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://lms:lms@localhost:5432/lms DEV_AUTH=true GOOGLE_CLIENT_ID=your-id
flask --app wsgi init-db && flask --app wsgi seed && flask --app wsgi run --debug
pytest -q                    # API tests (in-memory SQLite)

# 3. frontend (http://localhost:5173, proxies /api to :5000)
cd ../frontend && npm install
echo "VITE_DEV_AUTH=true" > .env.local     # shows "sign in without Google" on your laptop
npm run dev
```
`DEV_AUTH` and `VITE_DEV_AUTH` must stay `false` in production: they allow signing in with any email.

## Going live

* Serve over HTTPS and set `COOKIE_SECURE=true`.
* Use a long random `SECRET_KEY` and a strong `POSTGRES_PASSWORD`; back up the `pgdata` volume.
* Add your domain to Google's authorised origins.
* The in-memory rate limiter is per process; use Redis (or your proxy's limits) if you scale beyond one server.

## Editing the course

Lessons live in `backend/seed_data/lessons_<path>.json`; path text is in `paths.json`; downloads are listed in `resources.json` and stored in `backend/resources`. Edit, then run `flask --app wsgi seed` (or restart the container). Learner progress is kept because lessons are updated in place by path and lesson number.

## API summary

`GET /api/paths` &middot; `POST /api/auth/google {credential, path_slug}` &middot; `POST /api/auth/logout` &middot; `GET /api/me` &middot; `POST /api/me/path` &middot;
`GET /api/lessons` &middot; `GET /api/lessons/:n` &middot; `PUT /api/lessons/:n/progress` &middot; `POST|DELETE /api/lessons/:n/complete` &middot; `POST /api/lessons/:n/quiz` &middot;
`GET /api/progress` &middot; `GET /api/glossary` &middot; `GET /api/resources[/key]` &middot; `GET /api/certificate` &middot; `POST /api/coach` &middot; `GET /api/admin/overview|learners` &middot; `PATCH /api/admin/learners/:id/path`

Security notes: HttpOnly SameSite=Lax session cookie; every write needs an `X-Requested-With` header (CSRF defence); lessons and downloads are limited to the learner's own path; the Google token is verified server-side; auth and coach endpoints are rate limited.

## Project layout

```
backend/   Flask app (app/), seed_data/, resources/, tests/, Dockerfile
frontend/  Vite + React + Tailwind (src/pages, src/components, src/lib), nginx.conf, Dockerfile
docker-compose.yml   .env.example
```
