"""HTTP API routers.

Each feature area gets its own router module and is mounted under ``/api`` by
:func:`backend.api.router.api_router`. Phase 1 ships the system/health router; the
rest (jobs, resumes, applications, analytics, ...) arrive in their phases.
"""
