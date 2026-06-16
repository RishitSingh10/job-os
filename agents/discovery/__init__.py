"""Discovery Agent — find jobs, deduplicate, index.

Public surface::

    from agents.discovery import DiscoveryAgent, DiscoveryResult
    from agents.discovery.adapters import JobPosting, ManualAdapter, ExaAdapter
"""

from agents.discovery.agent import DiscoveryAgent, DiscoveryResult

__all__ = ["DiscoveryAgent", "DiscoveryResult"]
