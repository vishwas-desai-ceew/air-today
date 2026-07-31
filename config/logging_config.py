import logging
import logging.handlers
from pathlib import Path

PARENT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = PARENT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "aq_winter.log"

_configured = False


def get_logger(name: str) -> logging.Logger:
    """Returns a module-scoped logger under the shared 'aq_winter' namespace.

    Handlers (rotating file + console) are attached once to the root
    'aq_winter' logger the first time this is called; every subsequent
    call just returns a child logger, so cron scripts and the Streamlit
    app all end up in the same log file instead of scattered print()s.
    """
    global _configured
    root = logging.getLogger("aq_winter")
    if not _configured:
        root.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

        _configured = True

    return logging.getLogger(f"aq_winter.{name}")
