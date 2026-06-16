"""Specialised local AI agents for Job OS.

Each agent owns one bounded responsibility and is orchestrated by the API/services
layer — there are no microservices, only in-process modules:

* :mod:`agents.discovery`    — find jobs, deduplicate, index.
* :mod:`agents.ats`          — resume analysis, keyword matching, scoring.
* :mod:`agents.tailoring`    — truthful resume optimisation + diffs.
* :mod:`agents.cover_letter` — concise / startup / enterprise cover letters.
* :mod:`agents.browser`      — Playwright automation with explicit approval gates.
* :mod:`agents.tracking`     — application lifecycle updates.
* :mod:`agents.analytics`    — metric aggregation and insights.
"""
