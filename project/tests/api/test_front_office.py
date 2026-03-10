import pytest
from unittest.mock import patch, AsyncMock


def test_file_confirmation_returns_html(client):
    """GET /api/v1/front-office/file_confirmation returns 200 and HTML with report title."""
    with patch("app.api.routers.front_office.run_file_confirmation", new_callable=AsyncMock) as m:
        m.return_value = (
            "<!DOCTYPE html><html><head><title>File Confirmation Report</title></head>"
            "<body><h1>File Confirmation Report</h1><p>Success: True</p></body></html>"
        )
        response = client.get(
            "/api/v1/front-office/file_confirmation",
            params={"trade_date": "20250110", "cpty": "all", "by": "email"},
        )
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "File Confirmation Report" in response.text
    m.assert_called_once()
    cmd = m.call_args[0][0]
    assert cmd.trade_date == "20250110"
    assert cmd.cpty == "all"
    assert cmd.by == "email"


def test_file_confirmation_default_params(client):
    """GET /api/v1/front-office/file_confirmation with no params uses defaults."""
    with patch("app.api.routers.front_office.run_file_confirmation", new_callable=AsyncMock) as m:
        m.return_value = "<html><body>OK</body></html>"
        response = client.get("/api/v1/front-office/file_confirmation")
    assert response.status_code == 200
    m.assert_called_once()
    cmd = m.call_args[0][0]
    assert cmd.trade_date == "19000101"
    assert cmd.cpty == "all"
    assert cmd.by == "email"
    assert cmd.send_file is True
