"""Tailoring Agent — truthful resume optimisation, versioning, diffs.

Public surface::

    from agents.tailoring import TailoringAgent, TailoringOutcome, TailoredResumeService
"""

from agents.tailoring.agent import TailoredResumeService, TailoringAgent, TailoringOutcome

__all__ = ["TailoredResumeService", "TailoringAgent", "TailoringOutcome"]
