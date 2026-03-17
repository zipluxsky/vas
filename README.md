# Vascular_P

Document Management and Processing API — FastAPI application with Celery workers.

## Using the API (Router URLs)

Base URL (default): `http://localhost:8000`  
API prefix: **`/api/v1`**

Endpoints do not require authentication unless you enable `verify_token` on routes.  
When auth is enabled, use: `Authorization: Bearer <your_token>`.

### Health check (no auth)

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/health` | Service health and version |

Example:
```bash
curl http://localhost:8000/health
```

---

### Front Office

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/v1/front-office/file_confirmation` | Generate File Confirmation report (HTML). |

**Query parameters (all optional):**

- `trade_date`: YYYYMMDD (default `19000101` → use today)
- `cpty`: counterparty filter (default `all`)
- `by`: delivery mode `email` or `download` (default `email`)
- `env`: environment `dev`, `uat`, or `prod` (default `prod`)
- `versioning`: report version (default `1`)
- `send_file`: whether to send file e.g. by email (default `true`)

Example:
```bash
curl "http://localhost:8000/api/v1/front-office/file_confirmation?trade_date=20250110&cpty=all&by=email"
```

---

### Communicators

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/v1/communicators/ping` | Communicators health check. |
| POST | `/api/v1/communicators/email_sender` | Send email using matrix configuration (project/function/html_body, optional attachments). |

**POST `/api/v1/communicators/email_sender` body (JSON):**

- `project` (required): string
- `function` (required): string
- `html_body` (optional): string, default `""`
- `env` (optional): string
- `subject_suffix` (optional): string
- `attachments` (optional): list of file paths; only paths under `ATTACHMENT_ALLOWED_DIR` are allowed (set in env).

Example:
```bash
curl -X POST "http://localhost:8000/api/v1/communicators/email_sender" \
  -H "Content-Type: application/json" \
  -d '{"project":"myproject","function":"alerts","html_body":"<p>Hello</p>"}'
```

Ping example:
```bash
curl http://localhost:8000/api/v1/communicators/ping
```

---

### Web Portal (port 8000)

| Path | Description |
|------|-------------|
| `GET /` | Login page (portal entry). |
| `GET /main` | Main page with side menu (Reports, Settings, Admin) shown by user permission. |

Set `SECRET_KEY` in the environment for login. Default login: **admin** / **admin**. Other users in `project/app/core/users.json` (override via `configs/python_config/users.json`): **user**, **viewer** (password **password**). Roles: `admin` (all menu items), `user` (Reports, Settings), `viewer` (Reports only). Login API: `POST /api/v1/login/access-token` (form: `username`, `password`). Current user: `GET /api/v1/me` (Bearer token).

---

### Authentication (optional)

If you enable `Depends(verify_token)` on routes, set `SECRET_KEY` in the environment and use a JWT Bearer token:

- **Header:** `Authorization: Bearer <token>`

Interactive docs (Swagger): **`http://localhost:8000/docs`**  
Separate docs: **`/docs/communicators`**, **`/docs/front-office`**

---

### Summary of router URLs

| Router | Endpoint | Method |
|--------|----------|--------|
| Health | `/health` | GET |
| Front Office | `/api/v1/front-office/file_confirmation` | GET |
| Communicators | `/api/v1/communicators/ping` | GET |
| Communicators | `/api/v1/communicators/email_sender` | POST |

For deployment, set `SECRET_KEY` and optional `ATTACHMENT_ALLOWED_DIR` in the environment. See `docs/OPERATION_GUIDE.md` for run and deployment details.
