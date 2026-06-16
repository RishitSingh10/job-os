"""Job source adapters — normalise postings from each source into JobPosting."""

from agents.discovery.adapters.base import JobPosting, JobSourceAdapter
from agents.discovery.adapters.exa import ExaAdapter
from agents.discovery.adapters.manual import ManualAdapter

__all__ = ["ExaAdapter", "JobPosting", "JobSourceAdapter", "ManualAdapter"]
