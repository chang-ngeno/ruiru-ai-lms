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

## Deploy on Render + Neon

1. **Neon:** create a project, copy the connection string (use the *pooled* one). It looks like
   `postgresql://USER:PASSWORD@ep-xxxx-pooler.region.aws.neon.tech/DB?sslmode=require`. Any of `postgres://`, `postgresql://` or `postgresql+psycopg2://` works.
2. **Render:** push this folder to GitHub, then *New > Blueprint* and select the repo (`render.yaml` creates the API and the site).
   When prompted, set `DATABASE_URL` (Neon string), `GOOGLE_CLIENT_ID` and `ADMIN_EMAILS`. `SECRET_KEY` is generated for you.
3. **Frontend as a Docker service instead of a Static Site?** Set these environment variables on it (use your API's address):
   `BACKEND_URL=https://lms-api.onrender.com`, `BACKEND_HOST=lms-api.onrender.com`, `VITE_GOOGLE_CLIENT_ID=<your client id>`. nginx listens on Render's `$PORT` automatically.
   (With the Static Site from `render.yaml`, skip this.) Otherwise, in `render.yaml` the site proxies `/api/*` to `https://lms-api.onrender.com`. If Render gave your API a different URL, edit that line, commit and redeploy.
   Keeping the API on the same origin as the site is what lets the sign-in cookie work.
4. **Google Cloud:** add the site's URL (`https://lms-web.onrender.com` or your domain) to *Authorised JavaScript origins*.
5. Open the API service logs. A healthy start prints `=== Container starting`, `Connecting to postgresql+psycopg2://<neon host>...`, `Database is ready.`, `Seeded 3 paths and 60 lessons.` and `Starting gunicorn on port 10000`. Leave Render's *Docker Command* and *Pre-Deploy Command* fields empty.

Common deploy errors:

| Log message | Fix |
|---|---|
| `SECRET_KEY is not set` | Add `SECRET_KEY` in the service's Environment tab |
| `WARNING: DATABASE_URL points at localhost` | `DATABASE_URL` is missing or wrong; paste the Neon string |
| `password authentication failed` / `endpoint ... not found` | Copy the string again from Neon; reset the role password if needed |
| `SSL connection has been closed unexpectedly` | Use the pooled Neon host; the app already recycles connections |
| `No open ports detected` | Fixed: the container now listens on Render's `$PORT` |
| nginx: `host not found in upstream "backend"` | Old config. Use the new `nginx.conf.template` and set `BACKEND_URL` and `BACKEND_HOST` on the frontend service |
| Sign-in works then logs out immediately | `COOKIE_SECURE=true` needs HTTPS (Render provides it) and the site must proxy `/api` (see step 3) |

## Payments (M-Pesa) and course access

Learners pay by M-Pesa (Daraja STK Push). **Access follows the money**: the price is split into one share per week, and each share paid opens that week.

| Rule | Detail |
|---|---|
| Free preview | Lesson 1 of every path is open without paying |
| Instalments | Any amount from KES 100 up to the balance. 25% of the net price opens Week 1, 50% opens Weeks 1-2, 75% Weeks 1-3, 100% everything, plus downloads and the certificate |
| Resources | Open with the first payment (25%) |
| Workspace pass | Active from the first payment (25% of the price) for 30 days, shown as a QR code in the app |
| Net price | Path price minus the learner's discount. A 100% discount or a price of 0 opens everything |
| Admins | Always see everything |

**Learner flow:** *Payments* page > pick an amount or enter one > enter phone number > approve the prompt on the phone > the page updates by itself. Receipts and history are shown there.

**Admin (trainer dashboard):**
* **Payments** tab: every payment with status and receipt. "Review" means Safaricom reported a different amount than requested; nothing is unlocked until you check the M-Pesa statement and record a manual payment.
* **Discounts** tab: create codes (percent or KES off) limited to one path, a number of uses, an expiry date, or one named learner (for example a scholarship). Switch codes on or off.
* **Learners** tab > *Billing*: record a cash or bank payment, or give one learner a percent or KES discount with a reason (100% = scholarship).
* **Pricing** tab: change a path's price. Learners who have not paid yet get the new price; those who have paid keep their quote.

### Set up M-Pesa

1. **Sandbox first.** Create an account at developer.safaricom.co.ke, create an app with the *M-Pesa Express* product, and copy the consumer key and secret. Use the sandbox shortcode (174379) and the passkey shown in the portal's simulator.
2. Set the `MPESA_*` variables (see `.env.example` / `render.yaml`). `MPESA_CALLBACK_BASE` must be the **public https address of your site** (for example `https://learn.imperialenterprise.co.ke`); Safaricom posts results to `<base>/api/mpesa/callback/<MPESA_CALLBACK_SECRET>`, which the site's nginx forwards to Flask. It will not work on `localhost` unless you use a tunnel such as ngrok.
3. Pay a small amount from the sandbox, check the *Payments* tab, and confirm the lessons unlock.
4. **Go live:** apply to Safaricom for production (Go-Live) for your Paybill or Till, then switch `MPESA_ENV=production`, and set the production shortcode, passkey, consumer key/secret. **Paybill or Till?** Both work; the settings differ:

| Setting | Paybill | Till (Buy Goods) |
|---|---|---|
| `MPESA_TRANSACTION_TYPE` | `CustomerPayBillOnline` | `CustomerBuyGoodsOnline` |
| `MPESA_SHORTCODE` | your Paybill number | the store / head-office number Safaricom gave for the Till's STK Push |
| `MPESA_PARTY_B` | leave empty | **your Till number** |
| `MPESA_PASSKEY` | the passkey for that shortcode | the passkey for that shortcode |
| Sandbox testing | works with the test shortcode 174379 | **not available**: test in production with a live Till |

If you use a Till and leave the transaction type at the default, Safaricom rejects the request ("Invalid TransactionType"). In the trainer dashboard, open the **M-Pesa** tab: it shows these settings, warns about anything missing, and has a **Send KES 1 test prompt** button that shows Safaricom's exact answer (the test is not credited to anyone). Check Safaricom's current Daraja documentation for exact requirements.

| Safaricom message | Usual cause |
|---|---|
| `Invalid TransactionType` | Till used without `MPESA_TRANSACTION_TYPE=CustomerBuyGoodsOnline` (or a typo in it) |
| `Invalid Access Token` / 401 | Consumer key and secret do not match `MPESA_ENV` (sandbox keys with production, or the reverse) |
| `Merchant does not exist` / wrong credentials | Shortcode, party B (Till number) and passkey do not belong together |
| `Invalid CallBackURL` | `MPESA_CALLBACK_BASE` is not a public https address |

No Safaricom account yet? Set `MPESA_SIMULATE=true` (with `DEV_AUTH=true`) to try the whole flow locally; the Payments page shows "Simulate success / cancel" buttons.

### Refunds (admin approval)

* A learner who has paid can **request a refund** on the *Payments* page with a reason. Nothing changes until an admin decides.
* The app shows a **guide amount** based on your policy: **full** if the learner has not started any paid lesson; **partial** (default 50%) if they started and ask within 3 days of their first payment; **none** after that. These numbers are settings (`REFUND_PARTIAL_DAYS`, `REFUND_PARTIAL_PERCENT`). It is only a guide: the admin can approve any amount up to what the learner paid and has not had back.
* Admins work in the **Refunds** tab: *Approve* (with an amount and note), *Reject* (a reason is required), then, after sending the money from your M-Pesa or bank, *Paid out* with the reference. Admins can also start a refund for a learner from *Learners > Billing*.
* **Approving takes effect immediately:** the amount is deducted from what the learner has paid, so lessons for weeks they no longer cover lock again, the workspace pass stops if they fall under the 25% threshold, and the Collected totals go down.
* **The money itself is sent by you, not by the app.** Automatic reversals through Daraja need extra approval from Safaricom (an initiator account and security credential), so they are not included yet; the screen tells you how much to send and records the reference.

### Workspace pass (tied to payment)

* *Workspace* page: a pass with the learner's name, status, **QR code** and a code like `WS-1A-1B2C3D4E`. It is **active** once the learner has paid at least `WORKSPACE_MIN_PERCENT` (25%) of their price (or has a 100% scholarship), and lasts `WORKSPACE_DAYS` (30) from the first payment. A refund that drops them below the threshold switches it off.
* **Front desk** (admin): open the *Front desk* tab and type the code, or scan the QR with the phone camera (it opens this screen already signed in as admin). The screen shows **ALLOWED / NOT ALLOWED**, the learner's name and photo, and logs every scan.
* Codes are signed, so they cannot be made up, but they can be shown by someone else: always check the name and photo.
* Admins can extend or reset one learner's end date from *Learners > Billing*.

### Everyday operations (admin)

* **Receipts:** every successful payment has a printable receipt (Payments page > Receipt).
* **Waiting payments:** if a learner paid but nothing unlocked, open *Payments* > **Check waiting payments with Safaricom**. This asks Safaricom about every pending payment. To do it automatically, run `flask --app wsgi reconcile-payments` every 5 minutes (on Render: a Cron Job service with the same environment variables and that command).
* **Accounting:** *Payments* and *Refunds* each have **Download CSV** (spreadsheet-safe: cells that start with `=`, `+`, `-` or `@` are neutralised).
* **Activity tab:** an audit log of every admin action on payments, refunds, discounts, prices, learner paths and workspace dates (who, when, what).
* **Home-screen app:** learners can "Add to Home screen" on their phone. Link previews on WhatsApp use `frontend/public/og-image.png`; set your real address in `frontend/.env.production` (`VITE_SITE_URL`).

### Learners' data rights

*Profile > Your data*: **Download my data** (JSON of everything held) and **Delete my account** (erases name, email, notes, progress and the phone numbers on payments; keeps only amounts, dates and receipts for accounting). Administrator accounts cannot be deleted from the app.

### Moving existing learners over

Turning the paywall on locks lessons for anyone who has not paid. To switch over smoothly: set `PAYWALL_ENABLED=false`, record payments or give discounts to the learners already studying (Learners > Billing), then set it back to `true`.

### How payments are protected

* The callback URL contains a secret, and a payment is only credited if Safaricom's checkout id matches a pending payment and the amount equals what was requested. Repeated callbacks are ignored.
* If a callback is late or lost, the Payments page asks Safaricom directly (STK query) after 30 seconds, so a learner is never stuck.
* Phone numbers are normalised to the 2547XXXXXXXX / 2541XXXXXXXX format; the learner's number is masked in lists.
* Discount codes cannot be stacked, and every code and manual discount is stored with who created it.
* Only whole shillings are accepted (STK Push does not allow cents).

## Editing the course

Lessons live in `backend/seed_data/lessons_<path>.json`; path text is in `paths.json`; downloads are listed in `resources.json` and stored in `backend/resources`. Edit, then run `flask --app wsgi seed` (or restart the container). Learner progress is kept because lessons are updated in place by path and lesson number.

## API summary

`GET /api/paths` &middot; `POST /api/auth/google {credential, path_slug}` &middot; `POST /api/auth/logout` &middot; `GET /api/me` &middot; `POST /api/me/path` &middot;
`GET /api/lessons` &middot; `GET /api/lessons/:n` &middot; `PUT /api/lessons/:n/progress` &middot; `POST|DELETE /api/lessons/:n/complete` &middot; `POST /api/lessons/:n/quiz` &middot;
`GET /api/progress` &middot; `GET /api/billing` &middot; `POST /api/billing/discount|pay` &middot; `POST /api/mpesa/callback/:secret` &middot; `/api/admin/payments|discounts|paths` &middot; `GET /api/glossary` &middot; `GET /api/resources[/key]` &middot; `GET /api/certificate` &middot; `POST /api/coach` &middot; `GET /api/admin/overview|learners` &middot; `PATCH /api/admin/learners/:id/path`

Security notes: HttpOnly SameSite=Lax session cookie; every write needs an `X-Requested-With` header (CSRF defence); lessons and downloads are limited to the learner's own path; the Google token is verified server-side; auth and coach endpoints are rate limited.

## Project layout

```
backend/   Flask app (app/), seed_data/, resources/, tests/, Dockerfile
frontend/  Vite + React + Tailwind (src/pages, src/components, src/lib), nginx.conf, Dockerfile
docker-compose.yml   .env.example
```
