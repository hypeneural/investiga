"""Classified Retry Policies using Tenacity.

This module provides specific retry strategies based on the *type* of operational failure.
"""

from tenacity import (
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
)
import httpx


class SourceBlockedError(Exception):
    """Raised when a SourceAdapter hits a Captcha or deep block."""
    pass


class RateLimitError(Exception):
    """Raised when a 429 Too Many Requests is hit."""
    pass


# ── Policies ────────────────────────────────────────────────────────
# 1. Transient Network / Timeout (Fast, short exponential backoff)
retry_network = dict(
    retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)

# 2. Rate Limiting (Long fixed wait)
retry_rate_limit = dict(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(3),
    wait=wait_fixed(60),  # Wait 1 minute before retrying
)

# 3. Blocked / Captcha (Fail Fast -> send to DLQ / Human Intervention)
# We don't retry automatically on captchas because it wastes resources.
# It should fail and the worker should park the job.
retry_blocked = dict(
    retry=retry_if_exception_type(SourceBlockedError),
    stop=stop_after_attempt(1),
)
