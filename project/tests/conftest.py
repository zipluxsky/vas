import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.main import app
from app.api.deps import get_db_service, get_email_service, verify_token
from app.services.db_service import DatabaseService
from app.services.email_service import EmailService

@pytest.fixture
def mock_db_service():
    mock = MagicMock(spec=DatabaseService)
    # Configure default mock behaviors here if needed
    return mock

@pytest.fixture
def mock_email_service():
    mock = MagicMock(spec=EmailService)
    mock.send_email.return_value = True
    mock.send_report.return_value = True
    return mock

def mock_verify_token():
    return {"sub": "testuser", "role": "admin"}

@pytest.fixture
def client(mock_db_service, mock_email_service):
    # Override the dependencies for testing
    app.dependency_overrides[get_db_service] = lambda: mock_db_service
    app.dependency_overrides[get_email_service] = lambda: mock_email_service
    app.dependency_overrides[verify_token] = mock_verify_token
    
    with TestClient(app) as c:
        yield c
        
    # Clean up overrides after test
    app.dependency_overrides.clear()
