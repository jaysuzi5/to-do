# To-Do App — Roadmap

Personal task management for Jay (jaysuzi5@gmail.com) and Suzanne (jaysuziq@gmail.com),
with Alexa voice integration for hands-free task entry.

---

## Phase 1 — Foundation & Web Interface ✅ (Current)

### 1.1 Claude Setup Files
- [x] `.claudeignore`
- [x] `CLAUDE.md`
- [x] `.vscode/tasks.json`

### 1.2 Django Project Structure
- [x] `pyproject.toml` with uv
- [x] `config/` layout (settings, urls, wsgi, asgi, middleware, logging)
- [x] `tasks/` app (models, views, forms, urls, admin, context_processors)
- [x] `manage.py`
- [x] `Dockerfile` (multi-arch, uv, collectstatic, gunicorn + OTEL)

### 1.3 Data Models
- [x] `TaskList` — named list per user (slug, owner FK, is_default)
- [x] `Task` — title, priority (low/medium/high/urgent), status (pending/in_progress/completed), due_date, notes, added_via_alexa flag

### 1.4 Web Interface
- [x] Dashboard — all lists with stats + progress bars
- [x] Task list view — filtered by status/priority, quick-add bar, sidebar
- [x] Task row component — toggle complete, edit, delete, overdue highlight
- [x] Task add/edit form (full fields)
- [x] Task list create/delete
- [x] Bootstrap 5 design system with dark mode

### 1.5 Authentication
- [x] django-allauth (email + Google OAuth)
- [x] Auth templates (login, signup, logout)
- [x] All views behind LoginRequiredMixin

---

## Phase 2 — Database & Local Deployment ✅

### 2.1 PostgreSQL Setup
- [x] Create database on shared k8s PostgreSQL instance (192.168.86.201:30004, owner: jcurtis)
- [x] Fill in `.env` with real credentials (pulled from cluster secret, gitignored)
- [x] Run `uv run python manage.py migrate` — all tables created
- [x] Run `uv run python manage.py createsuperuser` — run in k8s pod (jaysuzi5@gmail.com)

### 2.2 User Setup
- [x] Create accounts for Jay (jaysuzi5@gmail.com) and Suzanne (jaysuziq@gmail.com)
- [x] Create default task lists: "Jay's To Do List" and "Suzanne's To Do List"
- [x] Verify login and task management works end-to-end

### 2.3 Google OAuth
- [x] Google Cloud Console → OAuth 2.0 Client ID (Web Application)
- [x] Add redirect URIs: `http://localhost:8000/accounts/google/login/callback/` and `https://todo.jaycurtis.org/accounts/google/login/callback/`
- [x] Django Admin → Social Applications → Add Google app

---

## Phase 3 — Kubernetes Deployment ✅ (Complete)

### 3.1 Kubernetes Secrets
- [x] Created `k8s/temp.yaml` (gitignored), sealed with kubeseal, temp file shredded
- [x] `k8s/secrets.yaml` committed (SealedSecret — encrypted blobs only)
- [x] `kubectl apply -f k8s/secrets.yaml` — live and decrypted in cluster
- [x] Namespace `to-do` created

### 3.2 Docker Build & Push
- [x] `docker buildx build --platform linux/amd64,linux/arm64 -t jaysuzi5/to-do:latest --push .`
- [x] `.dockerignore` added — `.env` excluded from build context
- [x] Dockerfile: dummy env vars for `collectstatic` build step (no real secrets in image)

### 3.3 Kubernetes Deploy
- [x] `kubectl apply -f k8s/deployment.yaml` — Deployment + Service created
- [x] Added `DJANGO_SETTINGS_MODULE=config.settings` env var (required before OTel instruments Django)
- [x] Readiness probe updated to `/health/` with `Host: todo.jaycurtis.org` header
- [x] `/health/` endpoint added (unauthenticated, skipped by request logger)
- [x] Pod `1/1 Running`, health check returns 200
- [x] Superuser `jaysuzi5@gmail.com` created — change password via Django Admin on first login

### 3.4 Cloudflare Tunnel
- [x] Cloudflare Zero Trust → Tunnels → Edit → Add route:
  - Subdomain: `todo`
  - Domain: `jaycurtis.org`
  - Type: HTTP
  - URL: `to-do.to-do.svc.cluster.local:80`
- [x] Verify `https://todo.jaycurtis.org` loads

---

## Phase 4 — Database Backups ✅

- [x] `kubectl apply -f k8s/backup-pvc.yaml` — 5Gi NFS PVC bound
- [x] `kubectl apply -f k8s/cronjob-backup.yaml` — 4 cronjobs created
  - `to-do-backup-local` — pg_dump to PVC every 6 hours, 7-day retention
  - `to-do-backup-cloud-daily` — S3 upload daily at 2 AM → `to-do/backups/daily/YYYY/MM/DD/`
  - `to-do-backup-cloud-monthly` — S3 upload 1st of month at 3 AM → `to-do/backups/monthly/YYYY/MM/`
  - `to-do-backup-cloud-yearly` — S3 upload Jan 1st at 4 AM → `to-do/backups/yearly/YYYY/`
- [x] Verify: `kubectl get cronjobs -n to-do` — all 4 active
- [x] Test local backup: job completed, 120KB dump verified on PVC
- [x] AWS IAM user has `s3:PutObject` on `jay-curtis-backup` (shared with other projects)
- [x] `aws_access_key_id` / `aws_secret_access_key` added to k8s SealedSecret

---

## Phase 5 — Alexa Skill Integration ✅ (Complete)

This phase adds voice-driven task entry. Users say things like:
- "Alexa, add wash the windows to Jay's To Do List"
- "Alexa, tell To-Do to add groceries to Suzanne's list"

### 5.1 API Endpoint
- [x] `tasks/api.py` with `AlexaAddTaskView` at `POST /api/alexa/add-task/`
- [x] Authentication: Bearer token (direct API) or Alexa request signature (Alexa webhook)
  - Direct: `Authorization: Bearer <ALEXA_SKILL_TOKEN>`
  - Body: `{"user": "jay"|"suzanne", "task": "wash the windows", "list": "Jay's To Do List"}`
  - Response: `{"status": "ok", "task_id": <id>}`
- [x] User name → email mapping: `{"jay": "jaysuzi5@gmail.com", "suzanne": "jaysuziq@gmail.com"}`
- [x] List matching: exact → partial → default list → first list
- [x] Sets `added_via_alexa=True` on created tasks
- [x] Wired into `config/urls.py` under `api/`
- [x] `ALEXA_SKILL_TOKEN` added to k8s SealedSecret

### 5.2 Alexa Developer Console (manual)
- [x] Log in at developer.amazon.com/alexa
- [x] Create new skill: "To-Do" (Custom, Self-Hosted) — skill ID: `amzn1.ask.skill.5d420c5c-ed51-4e3a-b76c-0fbd842bea15`
- [x] Invocation name: "my chores" (changed from "my to do list" — conflicted with Alexa's built-in list management)
- [x] Define Intents:
  - `AddTaskIntent` — slots: `Task` (`AMAZON.SearchQuery`), `UserName` (custom: Jay, Suzanne), `ListName` (custom: To Do, Shopping)
  - Sample utterances: "add {Task} to {UserName} {ListName} list", "add {Task} to {UserName} {ListName}", "add {Task} to {UserName} list"
  - Note: Alexa NLU rejects `{Slot}'s` (possessive after slot brace) — utterances use space-separated slot references
- [x] Fulfillment: HTTPS endpoint → `https://todo.jaycurtis.org/api/alexa/add-task/`
- [x] Account linking: not needed (request signature verification is the security layer)
- [x] Interaction model built successfully (4/26/2026)

### 5.3 Lambda / Endpoint Handler
- [x] Handles `LaunchRequest`, `SessionEndedRequest`, `IntentRequest`
- [x] Handles built-ins: `AMAZON.HelpIntent`, `AMAZON.CancelIntent`, `AMAZON.StopIntent`
- [x] Parses `AddTaskIntent` slots, maps user, calls `Task.objects.create()`
- [x] Returns Alexa-formatted JSON with spoken confirmation
- [x] Error responses: unknown user, no list found → friendly spoken message

### 5.4 Testing (after Alexa console setup)
- [x] Test via Alexa Developer Console simulator
  - Console Manual JSON and Simulator both blocked by wildcard cert (`*.jaycurtis.org`)
  - Cert type set to "sub-domain with wildcard CA cert" in endpoint config — correct setting for real device requests
  - Console test proxy has a known limitation: it ignores the cert type setting and rejects wildcards directly
  - Tested via Direct API (Bearer token) instead — all handler paths verified
- [x] Verify tasks appear in web UI with Alexa icon indicator
  - `added_via_alexa=True` confirmed on DB records; `_task_row.html:23-25` renders `bi-alexa` icon
- [x] Test edge cases: unknown list name, ambiguous user, missing slot values
  - Unknown list name → falls back to default/first list ✓
  - Unknown user → friendly "I don't know who X is" error ✓
  - Missing task → returns `task is required` ✓
  - User exists in map but no account in DB (Suzanne not yet created) → "Account not found" ✓
  - Note: Suzanne's account (`jaysuziq@gmail.com`) needs to be created before Alexa can add tasks for her

### 5.5 Alexa Skill Security
- [x] Timestamp verification — reject requests older than 150 seconds
- [x] Certificate URL validation — must be from `s3.amazonaws.com/echo.api/`
- [x] Certificate validity window checked
- [x] SAN verified to include `echo-api.amazon.com`
- [x] RSA-SHA1 signature verification using `cryptography` library (already a dependency)

---

## Phase 6 — Enhancements ⬜ (Future)

- [ ] Task reordering via drag-and-drop
- [ ] Recurring tasks (daily, weekly, monthly)
- [ ] Email reminders for overdue/due-today tasks
- [ ] Shared lists (multiple owners)
- [ ] Mobile-optimized PWA (add to home screen)
- [ ] Alexa: query tasks ("What's on my list?"), mark complete by voice
- [ ] Alexa: multi-turn conversation ("Add another task?")
- [ ] Push notifications via web-push or FCM
- [ ] Import/export (CSV, iCal)
