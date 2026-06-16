"""Top-level API router aggregation.

Every feature router is included here and the result is mounted under ``/api`` by
the app factory. Adding a feature = create its router module and ``include_router``
it below.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.api import applications, jobs, resumes, system

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
