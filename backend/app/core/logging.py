import json
import logging
import os
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from app.core.config import settings

request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    """Get the current request ID from context variable."""
    return request_id_ctx_var.get("-")


def set_request_id(request_id: str) -> None:
    """Set the request ID in context variable."""
    request_id_ctx_var.set(request_id)


class RequestIdFilter(logging.Filter):
    """Filter that injects the current request_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


class TextFormatter(logging.Formatter):
    """Human-readable log formatter with ANSI colors for development."""

    COLORS: dict[int, str] = {
        logging.DEBUG: "\033[36m",  # Cyan
        logging.INFO: "\033[32m",  # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",  # Red
        logging.CRITICAL: "\033[1;31m",  # Bold Red
    }
    RESET: str = "\033[0m"

    def __init__(self, use_colors: bool = True) -> None:
        super().__init__()
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        req_id = getattr(record, "request_id", "-")
        req_part = f"[{req_id}] " if req_id != "-" else ""
        time_str = self.formatTime(record, "%Y-%m-%d %H:%M:%S")

        levelname = record.levelname
        if self.use_colors:
            color = self.COLORS.get(record.levelno, "")
            reset = self.RESET if color else ""
            levelname = f"{color}{levelname:<8}{reset}"
        else:
            levelname = f"{levelname:<8}"

        message = record.getMessage()
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        return f"{time_str} | {levelname} | {record.name} | {req_part}{message}"


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production environments."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "module": record.module,
            "line": record.lineno,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging() -> None:
    """Configure project-wide logging based on settings."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    use_colors = (
        settings.LOG_FORMAT == "text"
        and sys.stdout.isatty()
        and os.getenv("NO_COLOR") is None
    )

    formatter: logging.Formatter
    if settings.LOG_FORMAT == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter(use_colors=use_colors)

    request_id_filter = RequestIdFilter()

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(request_id_filter)
    root_logger.addHandler(console_handler)

    # Optional file handler
    if settings.LOG_FILE_PATH:
        file_path = Path(settings.LOG_FILE_PATH)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            JSONFormatter()
            if settings.LOG_FORMAT == "json"
            else TextFormatter(use_colors=False)
        )
        file_handler.addFilter(request_id_filter)
        root_logger.addHandler(file_handler)

    # Configure external loggers to propagate through root logger
    for logger_name in ("uvicorn", "uvicorn.error", "fastapi"):
        ext_logger = logging.getLogger(logger_name)
        ext_logger.handlers.clear()
        ext_logger.propagate = True

    # Suppress redundant uvicorn access logs (handled by RequestLoggingMiddleware)
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers.clear()
    uvicorn_access.setLevel(logging.WARNING)

    # SQLAlchemy engine logging
    sql_logger = logging.getLogger("sqlalchemy.engine")
    if settings.LOG_SQL_QUERIES:
        sql_logger.setLevel(logging.INFO)
    else:
        sql_logger.setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger instance configured for the application."""
    return logging.getLogger(name or "app")
