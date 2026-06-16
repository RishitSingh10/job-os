"""Job deduplication primitives.

Phase 3 ships the deterministic fingerprint used as a fast first-pass dedup key
(stored on ``Job.dedup_hash``). Phase 5 layers fuzzy title similarity and
embedding-based matching on top of this.
"""

from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher

_WS = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^a-z0-9 ]")

# A new posting is a probable duplicate of an existing same-company job when its
# normalised title is at least this similar.
TITLE_SIMILARITY_THRESHOLD = 0.87
# Two postings are semantic duplicates when their embedding cosine distance is at
# or below this (0 = identical direction).
EMBEDDING_DISTANCE_THRESHOLD = 0.08


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


def title_similarity(a: str, b: str) -> float:
    """Normalised similarity ratio in [0, 1] between two titles."""
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def same_company(a: str, b: str) -> bool:
    return normalize(a) == normalize(b)


def is_title_duplicate(a_title: str, b_title: str) -> bool:
    """Whether two titles are similar enough to be considered the same role."""
    return title_similarity(a_title, b_title) >= TITLE_SIMILARITY_THRESHOLD
