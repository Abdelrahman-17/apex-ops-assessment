from app.main import create_app


def client_for(tmp_path):
    app = create_app({"TESTING": True, "DATABASE_PATH": str(tmp_path / "test.db")})
    return app.test_client()


def test_health_endpoint_returns_ok(tmp_path):
    response = client_for(tmp_path).get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_readiness_checks_database(tmp_path):
    response = client_for(tmp_path).get("/ready")
    assert response.status_code == 200
    assert response.json["dependency"] == "sqlite"


def test_create_operation_returns_201(tmp_path):
    response = client_for(tmp_path).post("/api/v1/operations", json={"name": "Check API"})
    assert response.status_code == 201
    assert response.json["name"] == "Check API"
    assert response.json["status"] == "pending"


def test_list_operations_returns_created_record(tmp_path):
    client = client_for(tmp_path)
    client.post("/api/v1/operations", json={"name": "Check API"})
    response = client.get("/api/v1/operations")
    assert response.status_code == 200
    assert len(response.json["items"]) == 1


def test_empty_name_is_rejected(tmp_path):
    response = client_for(tmp_path).post("/api/v1/operations", json={"name": "  "})
    assert response.status_code == 400


def test_overlong_name_is_rejected(tmp_path):
    response = client_for(tmp_path).post("/api/v1/operations", json={"name": "x" * 121})
    assert response.status_code == 400


def test_unknown_route_returns_json_404(tmp_path):
    response = client_for(tmp_path).get("/does-not-exist")
    assert response.status_code == 404
    assert response.json["error"] == "not_found"


def test_metrics_endpoint_exposes_prometheus_counters(tmp_path):
    client = client_for(tmp_path)
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "apex_http_requests_total" in response.text


def test_request_id_header_is_returned(tmp_path):
    response = client_for(tmp_path).get("/health", headers={"X-Request-ID": "test-request-123"})
    assert response.headers["X-Request-ID"] == "test-request-123"
