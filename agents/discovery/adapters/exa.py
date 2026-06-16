"""Exa adapter — semantic web search for job postings via the Exa API.

Exa returns ranked web results for a natural-language query (e.g.
"remote AI engineer roles at GenAI startups"). Each result is mapped best-effort
to a :class:`JobPosting`; the company is inferred from the result's host when the
API doesn't provide a structured author.
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

import httpx
from core.config import Settings, get_settings
from core.database.enums import JobSource
from core.exceptions import ValidationError

from agents.discovery.adapters.base import JobPosting

EXA_SEARCH_URL = "https://api.exa.ai/search"


def _company_from_url(url: str, fallback: str | None) -> str:
    if fallback:
        return fallback
    host = urlparse(url).hostname or ""
    host = host.removeprefix("www.")
    return host.split(".")[0].capitalize() if host else "Unknown"


def _parse_published(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class ExaAdapter:
    """Fetch postings from Exa semantic search."""

    source: JobSource = JobSource.exa

    def __init__(
        self, settings: Settings | None = None, *, client: httpx.AsyncClient | None = None
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client  # injectable for tests

    async def fetch(self, query: str, *, limit: int = 25) -> list[JobPosting]:
        api_key = self._settings.exa_api_key
        if not api_key:
            raise ValidationError("Exa search requires JOBOS_EXA_API_KEY to be set.")

        payload = {
            "query": query,
            "numResults": limit,
            "type": "auto",
            "contents": {"text": {"maxCharacters": 2000}},
        }
        headers = {"x-api-key": api_key}

        if self._client is not None:
            resp = await self._client.post(EXA_SEARCH_URL, json=payload, headers=headers)
        else:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(EXA_SEARCH_URL, json=payload, headers=headers)
        resp.raise_for_status()
        results = resp.json().get("results", [])

        return [self._to_posting(r) for r in results if r.get("url") and r.get("title")]

    def _to_posting(self, result: dict) -> JobPosting:
        url = result["url"]
        return JobPosting(
            title=result["title"],
            company=_company_from_url(url, result.get("author")),
            url=url,
            description=(result.get("text") or "").strip(),
            source=JobSource.exa,
            external_id=result.get("id"),
            posted_at=_parse_published(result.get("publishedDate")),
        )
