# Vascular_P

Document Management and Processing API — FastAPI application with Celery workers.

## Using the API (Router URLs)

Base URL (default): `http://localhost:8000`  
API prefix: **`/api/v1`**

All endpoints under `/api/v1` (except the health check) require **Bearer token** authentication.  
Include the header: `Authorization: Bearer <your_token>`.

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
| POST | `/api/v1/front-office/upload-document` | Upload a document; saved under `uploads/` and logged. |

**Query/body:**

- `file` (required): multipart file upload
- `document_type` (optional): string, default `"general"`

Example:
```bash
curl -X POST "http://localhost:8000/api/v1/front-office/upload-document" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/file.pdf" \
  -F "document_type=general"
```

---

### Communicators

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/v1/communicators/` | List communicators (paginated). |
| GET | `/api/v1/communicators/{communicator_id}` | Get one communicator by ID. |
| POST | `/api/v1/communicators/process` | Trigger background processing of communicator files (Celery). |

**List (GET `/api/v1/communicators/`):**

- `skip` (optional): offset, default `0`
- `limit` (optional): max count, default `100`

Example:
```bash
curl -X GET "http://localhost:8000/api/v1/communicators/?skip=0&limit=100" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Trigger processing (POST `/api/v1/communicators/process`):**

No body. Schedules the `process_communicator_files` Celery task.

Example:
```bash
curl -X POST "http://localhost:8000/api/v1/communicators/process" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Authentication

Endpoints use **OAuth2 Bearer** (JWT). Obtain a token from your auth provider or the login endpoint (if configured), then:

- **Header:** `Authorization: Bearer <token>`

Interactive docs (Swagger): **`http://localhost:8000/docs`** — use “Authorize” to set the token and try the router URLs from the browser.

---

### Summary of router URLs

| Router | Endpoint | Method |
|--------|----------|--------|
| Health | `/health` | GET |
| Front Office | `/api/v1/front-office/upload-document` | POST |
| Communicators | `/api/v1/communicators/` | GET |
| Communicators | `/api/v1/communicators/process` | POST |
| Communicators | `/api/v1/communicators/{communicator_id}` | GET |

For deployment, base URL and auth are environment-dependent; replace `http://localhost:8000` and `YOUR_TOKEN` with your host and token. See `docs/OPERATION_GUIDE.md` for run and deployment details.
