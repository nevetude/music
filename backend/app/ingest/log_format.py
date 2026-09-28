"""Цветной консольный логгер в стиле uvicorn/FastAPI:
`12:00:01 INFO     сообщение`, с отступами для вложенных шагов пайплайна
и подсветкой отдельных символов (✓ → ✗) внутри сообщения.

Использование:
    from .log_format import setup_logging
    setup_logging()  # один раз, в точке входа (cli.py)

    logger = logging.getLogger(__name__)
    logger.info("text")                    # plain line
    logger.info("text", extra={"indent": 1})  # indented as a "  ↳ " branch
"""

import logging
import sys

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

LEVEL_COLORS = {
    logging.DEBUG: "\033[36m",  # cyan
    logging.INFO: "\033[32m",  # green
    logging.WARNING: "\033[33m",  # yellow
    logging.ERROR: "\033[31m",  # red
    logging.CRITICAL: "\033[97;41m",  # белый на красном
}

SYMBOL_COLORS = {
    "✓": "\033[32m",  # green
    "→": "\033[36m",  # cyan
    "✗": "\033[31m",  # red
}

LEVEL_WIDTH = 8  # "CRITICAL" — самое длинное имя уровня


def _supports_color() -> bool:
    return sys.stderr.isatty()


class ColorFormatter(logging.Formatter):
    def __init__(self, use_color: bool | None = None) -> None:
        super().__init__()
        self.use_color = _supports_color() if use_color is None else use_color

    def _colorize_symbols(self, message: str) -> str:
        for symbol, color in SYMBOL_COLORS.items():
            if symbol in message:
                message = message.replace(symbol, f"{color}{symbol}{RESET}")
        return message

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()

        # Заголовки секций (log_header) — печатаются отдельным блоком, без
        # уровня/времени/отступа, жирным и цветом уровня.
        if getattr(record, "header", False):
            if self.use_color:
                color = LEVEL_COLORS.get(record.levelno, "")
                return f"{BOLD}{color}{message}{RESET}"
            return message

        indent = getattr(record, "indent", 0)
        branch = "  " * indent + ("↳ " if indent else "")

        if self.use_color:
            message = self._colorize_symbols(message)
            time_str = f"{DIM}{self.formatTime(record, '%H:%M:%S')}{RESET}"
            color = LEVEL_COLORS.get(record.levelno, "")
            level_str = f"{color}{BOLD}{record.levelname:<{LEVEL_WIDTH}}{RESET}"
        else:
            time_str = self.formatTime(record, "%H:%M:%S")
            level_str = f"{record.levelname:<{LEVEL_WIDTH}}"

        line = f"{time_str} {level_str} {branch}{message}"
        if record.exc_info:
            line = f"{line}\n{self.formatException(record.exc_info)}"
        return line


# Режимы вывода (make parse ... LOG=<режим>):
#   entities — только Artist → Album → Songs (логгер ingest.entities)
#   api      — только HTTP-запросы к Genius (логгер ingest.api)
#   all      — оба потока вместе
# WARNING и выше (ошибки загрузки) показываются в любом режиме.
LOG_MODES: dict[str, set[str] | None] = {
    "entities": {"ingest.entities"},
    "api": {"ingest.api"},
    "all": None,
}
DEFAULT_LOG_MODE = "entities"


class ModeFilter(logging.Filter):
    def __init__(self, mode: str) -> None:
        super().__init__()
        self.allowed = LOG_MODES[mode]

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno >= logging.WARNING or self.allowed is None:
            return True
        return record.name in self.allowed


def setup_logging(mode: str = DEFAULT_LOG_MODE, level: int = logging.INFO) -> None:
    """Настраивает root-логгер один раз, в точке входа CLI."""
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter())
    handler.addFilter(ModeFilter(mode))

    # httpx сам пишет INFO-строку на каждый запрос — у нас для этого свой ingest.api
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
