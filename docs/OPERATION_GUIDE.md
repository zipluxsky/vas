# Vascular_P Operation Guide

## 1. Overview
`Vascular_P` is a standalone project running entirely within Docker containers. It exposes a web API and handles background tasks asynchronously. 

The architecture consists of:
- **`vascular-api`**: A FastAPI application serving HTTP requests.
- **`vascular-worker`**: A Celery worker node responsible for executing background tasks.

It is designed to interoperate with `AirFlows_P` via a shared Redis instance acting as the Celery message broker.

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
`Vascular_P` is connected to the `airflow_shared_net` Docker network, allowing it to communicate seamlessly with AirFlows_P's infrastructure.

### Triggering Tasks from Airflow
`Vascular_P`'s Celery worker listens to a dedicated queue named **`vascular_tasks`**.
AirFlows_P can trigger Vascular_P functions natively without making HTTP calls, simply by pushing tasks to this shared Celery Queue via the common Redis broker (`redis://redis:6379/0`).

**Example: Triggering a Vascular_P task from an Airflow DAG**
You can use a `CeleryOperator` or a `PythonOperator` in AirFlows_P to dispatch messages to the shared Redis broker, targeting the `vascular_tasks` queue.

---

## 5. Local Development
To run `Vascular_P` locally on your machine:

1. Ensure Docker and Docker Compose are installed.
2. (Optional) If you are running it alongside Airflow locally, make sure the `airflow_shared_net` network exists:
   ```bash
   docker network create airflow_shared_net
   ```
3. Run the following command in the root `Vascular_P` directory:
   ```bash
   docker compose up -d --build
   ```
4. The API will be available at `http://localhost:8000`. 
5. You can view the API documentation (Swagger UI) at `http://localhost:8000/docs`.
