"""Test main application endpoints."""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


def test_root_endpoint(client: TestClient):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "AI Education Backend API"
    assert data["version"] == "0.1.0"


def test_health_endpoint(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ai-education-backend"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_api_health_endpoint(async_client: AsyncClient):
    """Test API health check endpoint."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["api_version"] == "v1"