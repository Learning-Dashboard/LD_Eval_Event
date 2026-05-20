from unittest.mock import Mock

import API_calls.StudentDatafromLDRESTAPI as student_api


def test_fetch_projects_sends_ld_api_key(monkeypatch):
    response = Mock()
    response.json.return_value = []
    response.raise_for_status.return_value = None
    mock_get = Mock(return_value=response)

    monkeypatch.setattr(student_api, "BASE_GESSI_URL", "http://tomcat:8080/api")
    monkeypatch.setattr(student_api, "LD_HEADERS", {"X-LD-API-Key": "test-ld-api-key"})
    monkeypatch.setattr(student_api.requests, "get", mock_get)

    assert student_api.fetch_projects() == []
    mock_get.assert_called_once_with(
        "http://tomcat:8080/api/projects",
        headers={"X-LD-API-Key": "test-ld-api-key"},
        timeout=60,
    )


def test_fetch_project_details_sends_ld_api_key(monkeypatch):
    response = Mock()
    response.json.return_value = {"id": 1}
    response.raise_for_status.return_value = None
    mock_get = Mock(return_value=response)

    monkeypatch.setattr(student_api, "BASE_GESSI_URL", "http://tomcat:8080/api")
    monkeypatch.setattr(student_api, "LD_HEADERS", {"X-LD-API-Key": "test-ld-api-key"})
    monkeypatch.setattr(student_api.requests, "get", mock_get)

    assert student_api.fetch_project_details(1) == {"id": 1}
    mock_get.assert_called_once_with(
        "http://tomcat:8080/api/projects/1",
        headers={"X-LD-API-Key": "test-ld-api-key"},
        timeout=60,
    )
