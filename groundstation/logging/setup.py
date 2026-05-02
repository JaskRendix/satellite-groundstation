import json
import logging
import logging.handlers
import os


def _json_formatter(record: logging.LogRecord) -> str:
    payload = {
        "level": record.levelname,
        "name": record.name,
        "message": record.getMessage(),
        "time": record.created,
    }
    if record.args:
        payload["args"] = record.args
    return json.dumps(payload)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return _json_formatter(record)


def init_logging(
    name: str,
    level: str = "INFO",
    fmt: str = "text",
    logfile: str | None = None,
) -> logging.Logger:
    """
    Initialize a logger with unified formatting.
    """

    logger = logging.getLogger(name)
    logger.setLevel(level.upper())

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Console handler
    console = logging.StreamHandler()
    if fmt == "json":
        console.setFormatter(JsonLogFormatter())
    else:
        console.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

    logger.addHandler(console)

    # Optional file handler
    if logfile:
        os.makedirs(os.path.dirname(logfile), exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            logfile, maxBytes=5_000_000, backupCount=3
        )
        if fmt == "json":
            file_handler.setFormatter(JsonLogFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
            )
        logger.addHandler(file_handler)

    return logger
