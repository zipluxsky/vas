# Vascular_P Operation Guide

## 1. Overview
`Vascular_P` is a standalone project running entirely within Docker containers. It exposes a web API and handles background tasks asynchronously. 

The architecture consists of:
- **`vascular-api`**: A FastAPI application serving HTTP requests.
- **`vascular-worker`**: A Celery worker node responsible for executing background tasks.
- **`vascular-redis`**: A dedicated Redis instance used only by Vascular as the Celery broker and result backend.

Vascular uses its **own Redis** (`vascular-redis` in docker-compose). It interoperates with `AirFlows_P` by exposing HTTP endpoints that enqueue tasks; Airflow triggers those endpoints (Option A). Vascular does not share its broker with Airflow.

---

## 2. CI/CD & Deployment Strategy
The project uses a single GitLab CI/CD pipeline (`.gitlab-ci.yml`) optimized for performance and server constraints.

### Deployment Logic
- **Code Changes**: If source code (e.g., `project/`, `Dockerfile`) is modified, the pipeline triggers a full `docker compose build` and `docker compose up -d` to recreate the image and restart the containers.
- **Config/Data Changes Only**: If changes are isolated to the `configs/` or `data/` directories, the pipeline **bypasses the image build process**. It mounts the Docker Named Volumes to a temporary Alpine container and directly synchronizes the files. This is significantly faster and prevents unnecessary service downtime.

### Host Machine Constraints
Due to restricted `sudo` privileges on the host machine (where only Docker commands can be run with sudo), standard bind mounts (e.g., `-v ./configs:/app/configs`) are completely avoided to prevent file permission issues. We exclusively use **Docker Named Volumes**.

---

## 3. Storage & Volumes
The project utilizes Docker Named Volumes to persist state and configuration:
- **`vascular-configs`**: Maps to `/app/configs` inside the containers.
- **`vascular-data`**: Maps to `/app/data` inside the containers.

*Note: If you need to manually inspect or modify these files on the host, you cannot directly access a host directory. You must use a temporary docker container to read/write from the volume.*

---

## 4. Interaction with AirFlows_P
`vascular-api` is attached to the `airflow_shared_net` Docker network so that Airflow can reach the API (e.g. `http://vascular-api:8000`). Vascular's Celery broker is **not** shared with Airflow; it uses `vascular-redis` on the internal `vascular_internal` network.

### Triggering Tasks from Airflow (Option A — recommended)
Airflow triggers Vascular tasks by **calling Vascular's HTTP API**. The API enqueues the task on Vascular's own Celery broker (`vascular-redis`); the `vascular-worker` consumes from that broker.

- **Endpoints:**  
  - `POST /api/v1/communicators/process` — enqueues the communicator files processing task (HTTP 202, returns `task_id`).  
  - `POST /api/v1/front-office/trigger-upload-document` — enqueues the upload_document task; optional JSON body: `document_type`, `file_path`, `original_filename`.
- **Example (Airflow XML DAG):** Use a trigger with `url="http://vascular-api:8000/api/v1/communicators/process"` and `method="post"`. See AirFlows_P `dags/dag_definitions/vascular_http_example.xml`.

No shared Redis or `VASCULAR_CELERY_BROKER_URL` is required on the Airflow side when using Option A. The `vascular_tasks` queue is consumed by `vascular-worker`; tasks are submitted via the API, not by Airflow writing to the same broker.

---

## 5. Base Image and Sybase Config
The application image is built **on top of the `vascular_base` image**, which provides Python 3.11, Microsoft ODBC 18, and Sybase 16 SDK. You must build and tag the base image before building the Vascular_P app image.

### Building the base image
From the root of the `Vascular_P` repository (with `installer/` and `configs/sybase_config/` in place):

```bash
docker build -f Base_Image_Docker_File -t vascular_base .
```

The base image bakes in `configs/sybase_config/interfaces` and `configs/sybase_config/odbc.ini` at build time. The app image uses an **entrypoint** that, at container start, copies any **non-empty** files from the mounted `configs/sybase_config/` (e.g. from the `vascular-configs` volume) over the built-in paths. So you can deploy real Sybase/ODBC config later by updating the config in the volume (or in the repo and re-syncing) **without rebuilding the image**.

- **Placeholder config**: Repo `configs/sybase_config/` currently contains placeholder files. The base image build and the app both work with these.
- **Real config**: When you have real `interfaces`, `odbc.ini`, and optionally `odbcinst.ini`, put them in `configs/sybase_config/` (or sync them into the `vascular-configs` volume). Ensure the `isql_path` in `configs/python_config/datasource.json` points to the Sybase `isql` binary in the container (e.g. `/opt/sybase16/OCS-16_0/bin/isql`) if you use the ISQL integration.

**CI/CD**: The GitLab pipeline runs `docker compose build` for the app image. The runner must have the `vascular_base` image available (build it manually or add a pipeline job that runs `docker build -f Base_Image_Docker_File -t vascular_base .` before deploy, if the `installer/` assets are available in the build context).

---

## 6. Local Development
To run `Vascular_P` locally on your machine:

1. Build the base image and tag it as `vascular_base` (see section 5).
2. Ensure Docker and Docker Compose are installed.
3. (Optional) If you are running it alongside Airflow locally, make sure the `airflow_shared_net` network exists:
   ```bash
   docker network create airflow_shared_net
   ```
4. Run the following command in the root `Vascular_P` directory:
   ```bash
   docker compose up -d --build
   ```
5. The API will be available at `http://localhost:8000`. 
6. You can view the API documentation (Swagger UI) at `http://localhost:8000/docs`.
