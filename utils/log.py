"""
Logging utilities for NBA Processor.
"""

import sys
from typing import Optional

# Global settings
_verbose = False
_use_emoji = True
_log_file: Optional[str] = None


def set_verbosity(verbose: bool) -> None:
    """Set verbosity level."""
    global _verbose
    _verbose = verbose


def set_use_emoji(use_emoji: bool) -> None:
    """Set emoji usage."""
    global _use_emoji
    _use_emoji = use_emoji


def set_log_file(path: str) -> None:
    """Set log file path."""
    global _log_file
    _log_file = path


def _log(message: str, prefix: str = "", file=sys.stdout) -> None:
    """Internal logging function."""
    output = f"{prefix}{message}" if prefix else message
    print(output, file=file)

    if _log_file:
        with open(_log_file, 'a', encoding='utf-8') as f:
            f.write(output + '\n')


def info(message: str) -> None:
    """Log info message."""
    _log(message)


def debug(message: str) -> None:
    """Log debug message (only if verbose)."""
    if _verbose:
        _log(message)


def warn(message: str) -> None:
    """Log warning message."""
    prefix = "Warning: " if not _use_emoji else "Warning: "
    _log(message, prefix, file=sys.stderr)


def error(message: str) -> None:
    """Log error message."""
    prefix = "Error: " if not _use_emoji else "Error: "
    _log(message, prefix, file=sys.stderr)


def success(message: str) -> None:
    """Log success message."""
    _log(message)


def exception(message: str, exc: Exception) -> None:
    """Log exception with traceback."""
    import traceback
    error(f"{message}: {exc}")
    if _verbose:
        traceback.print_exc()
