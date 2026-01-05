"""Network helpers with safety checks."""

from __future__ import annotations

import urllib.request
from urllib.parse import urlparse


def safe_urlopen(req: urllib.request.Request, timeout: int):
    parsed = urlparse(req.full_url)
    if parsed.scheme != "https":
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")
    return urllib.request.urlopen(req, timeout=timeout)  # noqa: S310
