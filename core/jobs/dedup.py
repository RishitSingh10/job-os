"""Job deduplication primitives.

Phase 3 ships the deterministic fingerprint used as a fast first-pass dedup key
(stored on ``Job.dedup_hash``). Phase 5 layers fuzzy title similarity and
embedding-based matching on top of this.
"""

from __future__ import annotations

import hashlib
import re

_WS = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^a-z0-9 ]")


def normalize(text: str) -> str:
    """Lowercase, strip punctuation, and collapse whitespace."""
    lowered = text.strip().lower()
    lowered = _NON_ALNUM.sub(" ", lowered)
    return _WS.sub(" ", lowered).strip()


def make_dedup_hash(*, title: str, company: str, url: str = "") -> str:
    """A stable fingerprint for a posting.

    Built from normalised company + title (the URL is included only when present,
    since the same posting can surface under different tracking URLs).
    """
    parts = [normalize(company), normalize(title)]
    if url:
        parts.append(url.split("?", 1)[0].rstrip("/").lower())
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:32]
