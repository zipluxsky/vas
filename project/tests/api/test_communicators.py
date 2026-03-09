import pytest
from unittest.mock import patch
from datetime import datetime

def test_get_communicators(client, mock_db_service):
    # Setup mock return value
    mock_data = [
        {"id": 1, "name": "Comm 1", "type": "email", "active": True, "created_at": datetime(2023, 1, 1)},
        {"id": 2, "name": "Comm 2", "type": "sms", "active": False, "created_at": datetime(2023, 1, 2)}
    ]
    mock_db_service.get_communicators.return_value = mock_data

    response = client.get("/api/v1/communicators/")
    
    assert response.status_code == 200
    expected_data = [
        {"id": 1, "name": "Comm 1", "type": "email", "active": True, "created_at": "2023-01-01T00:00:00", "config": None, "updated_at": None},
        {"id": 2, "name": "Comm 2", "type": "sms", "active": False, "created_at": "2023-01-02T00:00:00", "config": None, "updated_at": None}
    ]
    assert response.json() == expected_data
    mock_db_service.get_communicators.assert_called_once_with(skip=0, limit=100)

def test_get_communicator_by_id_success(client, mock_db_service):
    mock_data = {"id": 1, "name": "Comm 1", "type": "email", "active": True, "created_at": datetime(2023, 1, 1)}
    mock_db_service.get_communicator_by_id.return_value = mock_data

    response = client.get("/api/v1/communicators/1")
    
    assert response.status_code == 200
    expected_data = {"id": 1, "name": "Comm 1", "type": "email", "active": True, "created_at": "2023-01-01T00:00:00", "config": None, "updated_at": None}
    assert response.json() == expected_data
    mock_db_service.get_communicator_by_id.assert_called_once_with(1)

def test_get_communicator_by_id_not_found(client, mock_db_service):
    mock_db_service.get_communicator_by_id.return_value = None

    response = client.get("/api/v1/communicators/99")
    
    assert response.status_code == 404
    assert response.json() == {"detail": "Communicator not found"}

@patch("app.api.routers.communicators.process_communicator_files.delay")
def test_trigger_processing(mock_delay, client):
    # Mock celery task return
    class MockTask:
        id = "mock-task-id-123"
    mock_delay.return_value = MockTask()

    response = client.post("/api/v1/communicators/process")
    
    assert response.status_code == 200
    assert response.json() == {
        "status": "accepted",
        "message": "Processing task scheduled successfully with ID: mock-task-id-123",
        "details": None
    }
    mock_delay.assert_called_once()

