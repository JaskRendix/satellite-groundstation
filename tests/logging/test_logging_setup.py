from groundstation.logging.setup import init_logging


def test_init_logging_text_format(tmp_path):
    logfile = tmp_path / "test.log"

    logger = init_logging(
        name="test_logger", level="INFO", fmt="text", logfile=str(logfile)
    )

    logger.info("hello world")

    assert logfile.exists()
    content = logfile.read_text()
    assert "hello world" in content
    assert "INFO" in content


def test_init_logging_json_format(tmp_path):
    logfile = tmp_path / "test.json"

    logger = init_logging(
        name="json_logger", level="DEBUG", fmt="json", logfile=str(logfile)
    )

    logger.debug("json test")

    content = logfile.read_text()
    assert "json test" in content
    assert content.strip().startswith("{")
    assert '"level": "DEBUG"' in content


def test_logger_does_not_duplicate_handlers(tmp_path):
    logfile = tmp_path / "dup.log"

    logger1 = init_logging("dup_logger", logfile=str(logfile))
    logger2 = init_logging("dup_logger", logfile=str(logfile))

    # Only one handler should exist
    assert len(logger1.handlers) == 2
    assert logger1.handlers is logger2.handlers
