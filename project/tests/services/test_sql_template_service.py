import pytest
from pathlib import Path
from app.services.sql_template_service import SqlTemplateService

@pytest.fixture
def mock_template_dir(tmp_path):
    # Create mock template files
    (tmp_path / "test_query.sql").write_text("SELECT * FROM table WHERE id = {id}")
    (tmp_path / "test_query_shell.template").write_text("SELECT * FROM table WHERE name = '${name}'")
    (tmp_path / "test_query_no_ext").write_text("SELECT * FROM test")
    
    # Nested template
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    (nested_dir / "query.sql").write_text("SELECT {field} FROM nested")
    
    return tmp_path

@pytest.fixture
def sql_service(mock_template_dir):
    # Initialize service with our temp directory
    return SqlTemplateService(template_dirs=[mock_template_dir])

def test_get_query_basic(sql_service):
    query = sql_service.get_query("test_query")
    assert query == "SELECT * FROM table WHERE id = {id}"

def test_get_query_with_braces_param(sql_service):
    query = sql_service.get_query("test_query", params={"id": 123})
    assert query == "SELECT * FROM table WHERE id = 123"

def test_get_query_with_shell_param(sql_service):
    query = sql_service.get_query("test_query_shell", params={"name": "Alice"})
    assert query == "SELECT * FROM table WHERE name = 'Alice'"

def test_get_query_no_extension(sql_service):
    query = sql_service.get_query("test_query_no_ext")
    assert query == "SELECT * FROM test"

def test_get_query_nested(sql_service):
    query = sql_service.get_query("nested/query", params={"field": "status"})
    assert query == "SELECT status FROM nested"

def test_get_query_not_found(sql_service):
    with pytest.raises(FileNotFoundError):
        sql_service.get_query("non_existent_query")

def test_get_query_multiple_params(tmp_path):
    (tmp_path / "complex.sql").write_text("SELECT {a} FROM {b} WHERE id = ${c}")
    service = SqlTemplateService(template_dirs=[tmp_path])
    
    query = service.get_query("complex", params={"a": "name", "b": "users", "c": 99})
    assert query == "SELECT name FROM users WHERE id = 99"
