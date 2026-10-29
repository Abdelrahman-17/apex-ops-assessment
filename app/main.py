"""Small operations API with health, readiness, metrics, and structured logs."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from flask import Flask, Response, g, jsonify, request

APP_VERSION = os.getenv("APP_VERSION", "dev")
DATABASE_PATH = os.getenv("DATABASE_PATH", "./apex_ops.db")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            payload["request_id"] = record.request_id
        return json.dumps(payload, ensure_ascii=False)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), handlers=[handler], force=True)
logger = logging.getLogger("apex_ops")
_metrics_lock = Lock()
_request_count = 0
_error_count = 0
_start_time = time.monotonic()


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(TESTING=False, DATABASE_PATH=DATABASE_PATH)
    if test_config:
        app.config.update(test_config)

    db_path = app.config["DATABASE_PATH"]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def connect_db() -> sqlite3.Connection:
        conn = sqlite3.connect(db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def db_connection():
        conn = connect_db()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    with db_connection() as conn:
        conn.execute(
        "CREATE TABLE IF NOT EXISTS operations "
        "(id TEXT PRIMARY KEY, name TEXT NOT NULL, "
        "status TEXT NOT NULL, created_at TEXT NOT NULL)"
        )

    @app.before_request
    def start_request():
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        g.started_at = time.monotonic()

    @app.after_request
    def log_request(response):
        global _request_count, _error_count
        duration_ms = round((time.monotonic() - getattr(g, "started_at", time.monotonic())) * 1000, 2)
        with _metrics_lock:
            _request_count += 1
            if response.status_code >= 500:
                _error_count += 1
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "request_id": getattr(g, "request_id", "unknown"),
                }
            )
        )
        response.headers["X-Request-ID"] = getattr(g, "request_id", "unknown")
        return response

    @app.get("/health")
    def health():
        return jsonify(status="ok", version=APP_VERSION)

    @app.get("/ready")
    def ready():
        try:
            with db_connection() as conn:
                conn.execute("SELECT 1").fetchone()
            return jsonify(status="ready", dependency="sqlite"), 200
        except sqlite3.Error:
            logger.exception("Readiness database check failed")
            return jsonify(status="not_ready"), 503

    @app.get("/metrics")
    def metrics():
        with _metrics_lock:
            requests = _request_count
            errors = _error_count
        body = (
            "# HELP apex_http_requests_total Total HTTP requests handled.\n"
            "# TYPE apex_http_requests_total counter\n"
            f"apex_http_requests_total {requests}\n"
            "# HELP apex_http_errors_total HTTP 5xx responses.\n"
            "# TYPE apex_http_errors_total counter\n"
            f"apex_http_errors_total {errors}\n"
            "# HELP apex_process_uptime_seconds Process uptime in seconds.\n"
            "# TYPE apex_process_uptime_seconds gauge\n"
            f"apex_process_uptime_seconds {time.monotonic() - _start_time:.2f}\n"
        )
        return Response(body, mimetype="text/plain; version=0.0.4; charset=utf-8")

    @app.get("/api/v1/operations")
    def list_operations():
        with db_connection() as conn:
            rows = conn.execute(
                "SELECT id, name, status, created_at FROM operations ORDER BY created_at DESC"
            ).fetchall()
        return jsonify(items=[dict(row) for row in rows])

    @app.post("/api/v1/operations")
    def create_operation():
        data = request.get_json(silent=True) or {}
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            return jsonify(error="'name' must be a non-empty string"), 400
        if len(name.strip()) > 120:
            return jsonify(error="'name' must be at most 120 characters"), 400
        operation = {
            "id": str(uuid.uuid4()),
            "name": name.strip(),
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO operations (id, name, status, created_at) VALUES (?, ?, ?, ?)",
                (operation["id"], operation["name"], operation["status"], operation["created_at"]),
            )
        return jsonify(operation), 201

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(error="not_found", request_id=getattr(g, "request_id", "unknown")), 404

    return app


app = create_app()

if __name__ == "__main__":
    # Local-only development server; production container uses Gunicorn.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
