import pytest
from unittest.mock import AsyncMock


def test_communicators_ping(client):
    """GET /api/v1/communicators/ping returns 200 and status ok."""
    response = client.get("/api/v1/communicators/ping")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_email_sender_success(client, mock_email_service):
    """POST /api/v1/communicators/email_sender with valid body sends email and returns ok."""
    mock_email_service.send = AsyncMock(return_value=None)
    body = {
        "project": "test-project",
        "function": "test-fn",
        "html_body": "<p>test</p>",
        "env": "dev",
        "subject_suffix": None,
        "attachments": None,
    }
    response = client.post("/api/v1/communicators/email_sender", json=body)
    assert response.status_code == 200
    data = response.json()
    assert data.get("ok") is True
    assert "log" in data
    mock_email_service.send.assert_called_once()
    call_kw = mock_email_service.send.call_args[1]
    assert call_kw["project"] == "test-project"
    assert call_kw["function"] == "test-fn"


def test_email_sender_validation_error(client):
    """POST /api/v1/communicators/email_sender with missing required fields returns 422."""
    response = client.post("/api/v1/communicators/email_sender", json={})
    assert response.status_code == 422
    assert "detail" in response.json()
