"""Application logging with structured keyword argument support."""

import logging
import sys


class StructuredLogger(logging.Logger):
    """Logger subclass that accepts keyword arguments and formats them
    into the log message, mimicking structlog-style structured logging."""

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1, **kwargs):
        if kwargs:
            kv = " ".join(f"{k}={v}" for k, v in kwargs.items())
            msg = f"{msg} | {kv}"
        super()._log(level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel)


logging.setLoggerClass(StructuredLogger)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"))

logger: StructuredLogger = logging.getLogger("rag_app")  # type: ignore[assignment]
logger.setLevel(logging.INFO)
logger.addHandler(handler)
logger.propagate = False
