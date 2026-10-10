import json
import logging
import sys

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.logging import (
    JSONFormatter,
    RequestIdFilter,
    TextFormatter,
    get_logger,
    get_request_id,
    request_id_ctx_var,
    set_request_id,
    setup_logging,
)


def test_get_set_request_id() -> None:
    assert get_request_id() == "-"
    token = request_id_ctx_var.set("test-req-001")
    try:
        assert get_request_id() == "test-req-001"
        set_request_id("test-req-002")
        assert get_request_id() == "test-req-002"
    finally:
        request_id_ctx_var.reset(token)
    assert get_request_id() == "-"


def test_request_id_filter() -> None:
    filter_ = RequestIdFilter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    token = request_id_ctx_var.set("abc-xyz-123")
    try:
        assert filter_.filter(record) is True
        assert getattr(record, "request_id", None) == "abc-xyz-123"
    finally:
        request_id_ctx_var.reset(token)


def test_text_formatter() -> None:
    formatter = TextFormatter(use_colors=False)
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=15,
        msg="Sample log message",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-456"
    output = formatter.format(record)
    assert "INFO" in output
    assert "app.test" in output
    assert "[req-456]" in output
    assert "Sample log message" in output


def test_json_formatter() -> None:
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="app.service",
        level=logging.ERROR,
        pathname="service.py",
        lineno=25,
        msg="Database error occurred",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-error-789"
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["level"] == "ERROR"
    assert parsed["logger"] == "app.service"
    assert parsed["request_id"] == "req-error-789"
    assert parsed["message"] == "Database error occurred"
    assert "timestamp" in parsed


def test_json_formatter_with_exception() -> None:
    formatter = JSONFormatter()
    try:
        raise ValueError("Simulated crash")
    except ValueError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="app.crash",
        level=logging.CRITICAL,
        pathname="crash.py",
        lineno=35,
        msg="Fatal error",
        args=(),
        exc_info=exc_info,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["level"] == "CRITICAL"
    assert "exception" in parsed
    assert "ValueError: Simulated crash" in parsed["exception"]


def test_setup_logging_and_get_logger() -> None:
    setup_logging()
    root_logger = logging.getLogger()
    expected_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    assert root_logger.level == expected_level
    assert len(root_logger.handlers) >= 1

    custom_logger = get_logger("my_custom_module")
    assert custom_logger.name == "my_custom_module"


def test_request_logging_middleware_assigns_id(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/utils/health-check/")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 0


def test_request_logging_middleware_preserves_custom_id(client: TestClient) -> None:
    custom_id = "trace-custom-9999"
    response = client.get(
        f"{settings.API_V1_STR}/utils/health-check/",
        headers={"X-Request-ID": custom_id},
    )
    assert response.status_code == 200
    assert response.headers.get("x-request-id") == custom_id
