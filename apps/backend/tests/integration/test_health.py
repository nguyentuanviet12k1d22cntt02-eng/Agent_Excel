from fastapi.testclient import TestClient

import tutor_backend


def test_health_reports_database_ok(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "version": tutor_backend.__version__}


def test_openapi_docs_are_served(client: TestClient):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"].startswith("Gia sư AI Excel")
