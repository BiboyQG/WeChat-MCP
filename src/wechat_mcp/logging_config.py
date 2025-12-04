import logging
import os
from pathlib import Path


def setup_logging() -> logging.Logger:
    """
    Configure logging to both terminal and a log file under logs/.

    The log directory can be customized via WECHAT_MCP_LOG_DIR, otherwise
    a "logs" directory relative to the current working directory is used.
    """
    log_dir_env = os.getenv("WECHAT_MCP_LOG_DIR", "logs")
    log_dir = Path(log_dir_env).expanduser().resolve()
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "wechat_mcp.log"

    logger = logging.getLogger("wechat_mcp")
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.debug("Logging initialized, log file at %s", log_file)
    return logger


logger = setup_logging()
