"""Security utilities — input sanitization, secret masking."""

import re
from typing import Any


MAX_TRANSCRIPT_LENGTH = 50_000  # characters
MAX_RULES_LENGTH = 20_000
MAX_CORRECTION_LENGTH = 5_000
MAX_RUN_NAME_LENGTH = 200


def sanitize_text(text: str, max_length: int) -> str:
    """Truncate and strip a user-supplied text field."""
    return text.strip()[:max_length]


def mask_secret(value: str, visible: int = 4) -> str:
    """Mask all but the last `visible` characters of a secret."""
    if len(value) <= visible:
        return "***"
    return "*" * (len(value) - visible) + value[-visible:]


def safe_error_message(error: Exception) -> str:
    """Return an error message safe to show to the frontend.

    Strips potential API key leaks and stack details.
    """
    msg = str(error)
    # Remove anything that looks like an API key (long alphanumeric strings)
    msg = re.sub(r"[A-Za-z0-9_\-]{20,}", "[REDACTED]", msg)
    # Cap length
    return msg[:500]


def validate_run_id(run_id: str) -> bool:
    """Check that a run ID looks like a valid UUID."""
    return bool(re.match(r"^[0-9a-f\-]{36}$", run_id))
