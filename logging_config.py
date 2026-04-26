import logging
import os
import sys


_RESET = "\033[0m"
_LEVEL_COLORS = {
    logging.DEBUG: "\033[90m",
    logging.INFO: "\033[94m",
    logging.WARNING: "\033[93m",
    logging.ERROR: "\033[91m",
    logging.CRITICAL: "\033[95m",
}
_TAG_COLORS = {
    "MQTT SUB": "\033[96m",
    "MQTT UNSUB": "\033[96m",
    "MQTT PUB": "\033[92m",
    "MQTT ACK": "\033[95m",
    "MQTT PUBLISHED": "\033[95m",
    "MQTT RECV": "\033[93m",
    "MQTT CONNECT": "\033[94m",
    "MQTT DISCONNECT": "\033[91m",
    "LLM": "\033[92m",
    "STT": "\033[96m",
    "APP": "\033[94m",
}


def _should_use_color() -> bool:
    if os.getenv("NO_COLOR"):
        return False
    if os.getenv("FORCE_COLOR"):
        return True
    return hasattr(sys.stderr, "isatty") and sys.stderr.isatty()


class ColorFormatter(logging.Formatter):
    def __init__(self, use_color: bool = True):
        super().__init__("%(asctime)s %(levelname)-8s %(name)s %(message)s", "%H:%M:%S")
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        original_levelname = record.levelname
        tag = getattr(record, "log_tag", None)

        if self.use_color:
            level_color = _LEVEL_COLORS.get(record.levelno)
            if level_color:
                record.levelname = f"{level_color}{record.levelname}{_RESET}"
            if tag:
                tag_color = _TAG_COLORS.get(tag)
                if tag_color:
                    record.msg = f"[{tag_color}{tag}{_RESET}] {record.msg}"
                else:
                    record.msg = f"[{tag}] {record.msg}"
            elif tag:
                record.msg = f"[{tag}] {record.msg}"
        elif tag:
            record.msg = f"[{tag}] {record.msg}"

        try:
            return super().format(record)
        finally:
            record.levelname = original_levelname


def setup_logging(level: int = logging.DEBUG) -> None:
    root = logging.getLogger()
    root.setLevel(level)

    formatter = ColorFormatter(use_color=_should_use_color())
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(formatter)

    root.handlers.clear()
    root.addHandler(handler)


def log_extra(tag: str) -> dict[str, str]:
    return {"log_tag": tag}