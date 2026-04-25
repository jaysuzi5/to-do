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

## Phase 2 — Database & Local Deployment ⬜

### 2.1 PostgreSQL Setup
- [ ] Create database: `PGPASSWORD='...' psql -h 192.168.86.201 -p 30004 -U jcurtis -d postgres -c 'CREATE DATABASE "to-do" OWNER jcurtis;'`
- [ ] Fill in `.env` with real credentials
- [ ] Run `uv run python manage.py migrate`
- [ ] Run `uv run python manage.py createsuperuser`

### 2.2 User Setup
- [ ] Create accounts for Jay (jaysuzi5@gmail.com) and Suzanne (jaysuziq@gmail.com)
- [ ] Create default task lists: "Jay's To Do List" and "Suzanne's To Do List"
- [ ] Verify login and task management works end-to-end

### 2.3 Google OAuth
- [ ] Google Cloud Console → OAuth 2.0 Client ID (Web Application)
- [ ] Add redirect URIs: `http://localhost:8000/accounts/google/login/callback/` and `https://todo.jaycurtis.org/accounts/google/login/callback/`
- [ ] Django Admin → Social Applications → Add Google app

---

## Phase 3 — Kubernetes Deployment ⬜

### 3.1 Kubernetes Secrets
- [ ] Create `k8s/temp.yaml` with base64-encoded values (see CLAUDE.md)
- [ ] `kubeseal -f k8s/temp.yaml -o yaml > k8s/secrets.yaml`
- [ ] `kubectl apply -f k8s/secrets.yaml`
- [ ] `rm k8s/temp.yaml`

### 3.2 Docker Build & Push
- [ ] `docker buildx build --platform linux/amd64,linux/arm64 -t jaysuzi5/to-do:latest --push .`

### 3.3 Kubernetes Deploy
- [ ] `kubectl apply -f k8s/deployment.yaml`
- [ ] Verify pod starts: `kubectl get pods -n to-do`
- [ ] Check logs: `kubectl logs -n to-do -l app=to-do -f`
- [ ] Run createsuperuser in pod

### 3.4 Cloudflare Tunnel
- [ ] Cloudflare Zero Trust → Tunnels → Edit → Add route:
  - Subdomain: `todo`
  - Domain: `jaycurtis.org`
  - Type: HTTP
  - URL: `to-do.to-do.svc.cluster.local:80`
- [ ] Verify `https://todo.jaycurtis.org` loads

---

## Phase 4 — Database Backups ⬜

- [ ] `kubectl apply -f k8s/backup-pvc.yaml`
- [ ] `kubectl apply -f k8s/cronjob-backup.yaml`
- [ ] Verify: `kubectl get cronjobs -n to-do`
- [ ] Test local backup: `kubectl create job --from=cronjob/to-do-backup-local test-backup -n to-do`
- [ ] Ensure AWS IAM user has `s3:PutObject` on `jay-curtis-backup`
- [ ] Add `aws_access_key_id` / `aws_secret_access_key` to k8s secrets

---

## Phase 5 — Alexa Skill Integration ⬜

This phase adds voice-driven task entry. Users say things like:
- "Alexa, add wash the windows to Jay's To Do List"
- "Alexa, tell To-Do to add groceries to Suzanne's list"

### 5.1 API Endpoint
- [ ] Add `tasks/api.py` with `AlexaAddTaskView`:
  - `POST /api/alexa/add-task/`
  - Authentication: Bearer token (`ALEXA_SKILL_TOKEN` secret)
  - Request body: `{"user": "jay"|"suzanne", "task": "wash the windows", "list": "Jay's To Do List"}`
  - Response: `{"status": "ok", "task_id": <id>}`
  - Sets `added_via_alexa=True` on created task
- [ ] User name → email mapping: `{"jay": "jaysuzi5@gmail.com", "suzanne": "jaysuziq@gmail.com"}`
- [ ] Wire into `config/urls.py` under `api/`

### 5.2 Alexa Developer Console
- [ ] Log in at developer.amazon.com/alexa
- [ ] Create new skill: "To-Do" (Custom, Self-Hosted)
- [ ] Invocation name: "my to-do list" (or "to-do")
- [ ] Define Intents:
  - `AddTaskIntent` — "add {Task} to {UserName}'s {ListName}"
  - Slots: `Task` (free-form utterance), `UserName` (Jay|Suzanne), `ListName` (custom slot)
- [ ] Fulfillment: HTTPS endpoint → `https://todo.jaycurtis.org/api/alexa/add-task/`
- [ ] Account linking: not needed (bearer token auth)

### 5.3 Lambda / Endpoint Handler
- [ ] Alexa sends JSON payload to the endpoint
- [ ] Django view parses `intentName`, extracts slots, maps user, calls `Task.objects.create()`
- [ ] Returns Alexa-formatted JSON response: `{"version": "1.0", "response": {"outputSpeech": {...}}}`
- [ ] Error handling: unknown user, unknown list → friendly Alexa spoken response

### 5.4 Local Alexa Testing
- [ ] Test via Alexa Developer Console simulator before live device testing
- [ ] Verify tasks appear in web UI with Alexa icon indicator
- [ ] Test edge cases: unknown list name, ambiguous user

### 5.5 Alexa Skill Security
- [ ] Request signature verification (Alexa sends `SignatureCertChainUrl` header)
- [ ] Timestamp verification (reject requests older than 150 seconds)
- [ ] Use `ask-sdk-core` or `alexa-skills-kit-sdk` Python package for validation
- [ ] Add `alexa-skills-kit-sdk-for-python` to `pyproject.toml`

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
