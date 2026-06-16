"""Tests for the system/health API and app factory."""

from __future__ import annotations

from httpx import AsyncClient


async def test_health_returns_ok(client: AsyncClient) -> None:
    resp = await client.get("/api/health")
    assert resp.status_code == 200

    body = resp.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"
    assert body["version"]
    assert body["app_name"]


async def test_ready_reports_dependencies(client: AsyncClient) -> None:
    # Ollama almost certainly isn't running in CI; the endpoint must still respond
    # 200 with a structured, well-formed readiness payload (never raise).
    resp = await client.get("/api/ready")
    assert resp.status_code == 200

    body = resp.json()
    assert "ready" in body
    assert isinstance(body["dependencies"], list)
    names = {d["name"] for d in body["dependencies"]}
    assert "ollama" in names


async def test_openapi_schema_is_served(client: AsyncClient) -> None:
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    assert resp.json()["info"]["title"]
