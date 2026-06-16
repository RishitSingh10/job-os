"""Backend application package (FastAPI modular monolith).

The HTTP layer for Job OS. Wires together the :mod:`core` infrastructure and the
:mod:`agents` into a single ASGI application via :func:`backend.main.create_app`.
"""

__version__ = "0.1.0"
