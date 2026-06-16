"""ATS Agent — resume analysis, keyword matching, weighted scoring.

Public surface::

    from agents.ats import ATSAgent, ATSScoreService
    from agents.ats.scoring import ScoreBreakdown, WEIGHTS
"""

from agents.ats.agent import ATSAgent, ATSScoreService

__all__ = ["ATSAgent", "ATSScoreService"]
