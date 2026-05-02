# To-Do API — Integration Guide

This document describes the REST API for the To-Do application and contains everything
needed to implement a dashboard card (e.g. in a home-lab hub) that shows open tasks,
marks tasks complete, and adds new tasks.

---

## Base URL

```
https://todo.jaycurtis.org/api/
```

Interactive Swagger docs (no auth required):
```
https://todo.jaycurtis.org/api/docs/
```

OpenAPI 3.0 schema (JSON):
```
https://todo.jaycurtis.org/api/schema/
```

---

## Authentication

Every API endpoint requires a static bearer token.

```
Authorization: Bearer <TODO_API_TOKEN>
```

The token value comes from the `TODO_API_TOKEN` environment variable / k8s secret.
Requests without a valid token receive `401 Unauthorized`.

---

## Endpoints

### GET /api/v1/lists/

Returns all task lists across all users.

**Query parameters**

| Parameter | Type   | Required | Description                                    |
|-----------|--------|----------|------------------------------------------------|
| `owner`   | string | No       | Filter by username. Valid values: `jay`, `suzanne` |

**Example request**
```bash
curl https://todo.jaycurtis.org/api/v1/lists/?owner=jay \
  -H "Authorization: Bearer <token>"
```

**Example response** `200 OK`
```json
[
  {
    "id": 3,
    "name": "Default",
    "slug": "3-default",
    "owner": "Jay Curtis",
    "is_default": true,
    "pending_count": 4,
    "created_at": "2025-01-15T12:00:00Z"
  }
]
```

---

### GET /api/v1/lists/{list_id}/tasks/

Returns all **open** tasks (status `pending` or `in_progress`) for the given list,
ordered by `due_date` then `created_at`.

**Path parameters**

| Parameter | Type    | Description    |
|-----------|---------|----------------|
| `list_id` | integer | Task list ID   |

**Example request**
```bash
curl https://todo.jaycurtis.org/api/v1/lists/3/tasks/ \
  -H "Authorization: Bearer <token>"
```

**Example response** `200 OK`
```json
[
  {
    "id": 42,
    "title": "Wash the windows",
    "priority": "medium",
    "status": "pending",
    "due_date": "2026-05-10",
    "is_overdue": false,
    "created_at": "2026-05-01T09:00:00Z",
    "added_via_alexa": false
  },
  {
    "id": 43,
    "title": "Schedule HVAC service",
    "priority": "high",
    "status": "pending",
    "due_date": null,
    "is_overdue": false,
    "created_at": "2026-05-02T10:30:00Z",
    "added_via_alexa": false
  }
]
```

**Task field reference**

| Field           | Type    | Description                                               |
|-----------------|---------|-----------------------------------------------------------|
| `id`            | integer | Task ID — use this for complete / future edits            |
| `title`         | string  | Task description                                          |
| `priority`      | string  | `low`, `medium`, `high`, or `urgent`                      |
| `status`        | string  | `pending` or `in_progress` (completed tasks are excluded) |
| `due_date`      | date    | ISO 8601 date string, or `null` if not set                |
| `is_overdue`    | boolean | `true` when `due_date < today` and task is not complete   |
| `created_at`    | datetime| ISO 8601 datetime                                         |
| `added_via_alexa` | boolean | `true` when added via Alexa voice command               |

---

### POST /api/v1/lists/{list_id}/tasks/

Adds a new task to the given list.

**Path parameters**

| Parameter | Type    | Description    |
|-----------|---------|----------------|
| `list_id` | integer | Task list ID   |

**Request body** `application/json`

| Field      | Type   | Required | Default    | Description                            |
|------------|--------|----------|------------|----------------------------------------|
| `title`    | string | Yes      | —          | Task description (max 500 chars)       |
| `priority` | string | No       | `medium`   | `low`, `medium`, `high`, or `urgent`   |
| `due_date` | date   | No       | `null`     | ISO 8601 date string, e.g. `2026-05-15` |
| `notes`    | string | No       | `""`       | Additional notes                       |

**Example request**
```bash
curl -X POST https://todo.jaycurtis.org/api/v1/lists/3/tasks/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Pick up dry cleaning", "priority": "low"}'
```

**Example response** `201 Created`
```json
{
  "id": 44,
  "title": "Pick up dry cleaning",
  "priority": "low",
  "status": "pending",
  "due_date": null,
  "is_overdue": false,
  "created_at": "2026-05-02T14:00:00Z",
  "added_via_alexa": false
}
```

---

### POST /api/v1/tasks/{task_id}/complete/

Marks a task as complete. Idempotent — safe to call on an already-completed task.

**Path parameters**

| Parameter | Type    | Description |
|-----------|---------|-------------|
| `task_id` | integer | Task ID     |

**Request body**: none (empty POST)

**Example request**
```bash
curl -X POST https://todo.jaycurtis.org/api/v1/tasks/42/complete/ \
  -H "Authorization: Bearer <token>"
```

**Example response** `200 OK`
```json
{
  "id": 42,
  "title": "Wash the windows",
  "priority": "medium",
  "status": "completed",
  "due_date": "2026-05-10",
  "is_overdue": false,
  "created_at": "2026-05-01T09:00:00Z",
  "added_via_alexa": false
}
```

---

## Error responses

All errors return JSON with an `error` key.

| Status | Meaning                                |
|--------|----------------------------------------|
| `400`  | Bad request — invalid input            |
| `401`  | Missing or invalid `Authorization` header |
| `404`  | Task list or task not found            |

---

## Known list IDs

| Owner   | List name | ID | Notes       |
|---------|-----------|----|-------------|
| Jay     | Default   | 3  | Primary list |

Confirm IDs via `GET /api/v1/lists/?owner=jay`.

---

## Secrets setup

### Local development

Generate a token and add it to `.env`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Add to .env:
TODO_API_TOKEN=<generated-value>
```

### Kubernetes (production)

Add `todo_api_token` to `k8s/temp.yaml`, seal it, and re-apply:

```yaml
# k8s/temp.yaml  (gitignored — delete immediately after sealing)
apiVersion: v1
kind: Secret
metadata:
  name: to-do
  namespace: to-do
type: Opaque
stringData:
  todo_api_token: "<your-token>"
```

```bash
kubeseal --format yaml < k8s/temp.yaml > k8s/secrets.yaml
rm k8s/temp.yaml
kubectl apply -f k8s/secrets.yaml
kubectl rollout restart deployment to-do -n to-do
```

---

## Dashboard card implementation guide

This section gives Claude Code everything it needs to build a to-do card in the
home-lab hub project.

### Card requirements

- Show all open tasks from Jay's Default list (list ID 3)
- Display task title, priority badge, and overdue indicator
- "Complete" button on each task row — calls the complete endpoint and removes the row
- "Add task" input at the bottom — calls the add endpoint on submit
- Auto-refresh every 60 seconds (or on focus)

### Priority badge colours (Bootstrap 5 compatible)

| Priority | Badge class       |
|----------|-------------------|
| urgent   | `badge bg-danger` |
| high     | `badge bg-warning text-dark` |
| medium   | `badge bg-primary` |
| low      | `badge bg-secondary` |

### Suggested implementation approach

Use a single React/Vue component (or vanilla JS widget) that:

1. On mount, calls `GET /api/v1/lists/3/tasks/` and renders the task list.
2. On "Complete" click, calls `POST /api/v1/tasks/{id}/complete/`, then removes
   the task from local state (no need to re-fetch).
3. On "Add" submit, calls `POST /api/v1/lists/3/tasks/` with `{"title": "..."}`,
   then prepends the returned task object to local state.
4. Stores the bearer token in the dashboard's secret store / env config — never
   hardcoded in source.

### Minimal fetch wrapper (JavaScript)

```js
const TODO_BASE = 'https://todo.jaycurtis.org/api/v1';
const TODO_TOKEN = process.env.TODO_API_TOKEN; // inject from env

async function apiFetch(path, options = {}) {
  const res = await fetch(`${TODO_BASE}${path}`, {
    ...options,
    headers: {
      'Authorization': `Bearer ${TODO_TOKEN}`,
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.status === 204 ? null : res.json();
}

// Usage
const tasks     = await apiFetch('/lists/3/tasks/');
const newTask   = await apiFetch('/lists/3/tasks/', { method: 'POST', body: JSON.stringify({ title }) });
const completed = await apiFetch(`/tasks/${id}/complete/`, { method: 'POST' });
```

### CORS note

If the dashboard card makes requests **from the browser** (client-side fetch) to
`todo.jaycurtis.org`, the API server must return CORS headers for the dashboard's
origin. To enable this, add `django-cors-headers` to the to-do project and configure
`CORS_ALLOWED_ORIGINS` with the dashboard's URL. If requests are made **server-side**
(e.g. a backend proxy or SSR), CORS is not needed.
