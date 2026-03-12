"""Redis-backed pipeline context for passing intermediate data between
Celery tasks that form a multi-step pipeline.

Each pipeline run is identified by a *pipeline_key* (typically
``pipeline:<dag_run_id>``).  Individual steps store their output under
``<pipeline_key>:<step_name>`` with a configurable TTL so keys are
automatically cleaned up.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import redis

logger = logging.getLogger(__name__)

_DEFAULT_TTL = 86400  # 24 hours


def _get_redis_client() -> redis.Redis:
    url = (
        os.getenv("PIPELINE_REDIS_URL")
        or os.getenv("CELERY_BROKER_URL")
        or "redis://localhost:6379/0"
    )
    return redis.Redis.from_url(url, decode_responses=True)


class PipelineContext:
    """Read/write JSON-serialisable data for a specific pipeline run."""

    def __init__(self, pipeline_key: str, ttl: int = _DEFAULT_TTL) -> None:
        self.pipeline_key = pipeline_key
        self.ttl = ttl
        self._redis = _get_redis_client()

    def _full_key(self, step_name: str) -> str:
        return f"{self.pipeline_key}:{step_name}"

    def write(self, step_name: str, data: dict[str, Any]) -> None:
        key = self._full_key(step_name)
        self._redis.set(key, json.dumps(data, default=str), ex=self.ttl)
        logger.debug("Pipeline write %s (%d bytes)", key, len(json.dumps(data, default=str)))

    def read(self, step_name: str) -> dict[str, Any]:
        key = self._full_key(step_name)
        raw = self._redis.get(key)
        if raw is None:
            raise KeyError(f"Pipeline context key not found: {key}")
        return json.loads(raw)

    def delete(self, step_name: str) -> None:
        self._redis.delete(self._full_key(step_name))

    def cleanup(self) -> None:
        """Delete all keys belonging to this pipeline run."""
        pattern = f"{self.pipeline_key}:*"
        cursor = 0
        while True:
            cursor, keys = self._redis.scan(cursor, match=pattern, count=100)
            if keys:
                self._redis.delete(*keys)
            if cursor == 0:
                break
