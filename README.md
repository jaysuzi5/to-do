# To-Do

Personal task manager for Jay and Suzanne. Supports named task lists with priority levels, Google OAuth login, and Amazon Alexa voice integration ("Alexa, ask my chores to add wash the windows to Jay's list").

**Live:** https://todo.jaycurtis.org

## Stack

- Python 3.12 / Django 6.0
- PostgreSQL on Kubernetes
- django-allauth — email + Google OAuth
- Bootstrap 5 + WhiteNoise
- OpenTelemetry (OTLP) wrapping gunicorn
- Docker multi-arch → Kubernetes (namespace `to-do`) via Cloudflare tunnel

## Local Development

```bash
uv sync
cp .env.example .env       # fill in real values
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

## Deploy

```bash
# Build and push multi-arch image
docker buildx build --platform linux/amd64,linux/arm64 -t jaysuzi5/to-do:latest --push .

# First deploy (or after adding new k8s env vars)
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/deployment.yaml

# Subsequent deploys
kubectl rollout restart deployment to-do -n to-do
kubectl rollout status deployment/to-do -n to-do
```

## Models

**TaskList** — owned by a user, has a name, slug, and optional description.  
**Task** — belongs to a TaskList; has title, priority (low/medium/high/urgent), status (pending/in_progress/completed), optional due date, and an `added_via_alexa` flag.

## Alexa Integration

The `POST /api/alexa/add-task/` endpoint accepts signed Alexa requests. It maps Alexa user IDs to Django accounts and adds tasks via the `AddTaskIntent`. The skill token is gated by the `ALEXA_SKILL_TOKEN` env var. Invocation name: **"my chores"** (skill ID: `amzn1.ask.skill.5d420c5c-ed51-4e3a-b76c-0fbd842bea15`).

## Backups

Four k8s CronJobs write PostgreSQL dumps to an NFS PVC: every 6 hours (local), daily/monthly/yearly to S3 with retention.
