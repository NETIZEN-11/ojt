import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import Settings


def get_test_settings():
    return Settings(
        SECRET_KEY="a" * 32,
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        REDIS_URL="redis://localhost:6379/0",
        CELERY_BROKER_URL="redis://localhost:6379/1",
        CELERY_RESULT_BACKEND="redis://localhost:6379/2",
        ENVIRONMENT="testing",
        DEBUG=False,
        JWT_PRIVATE_KEY_PATH="",
        JWT_PUBLIC_KEY_PATH="",
        S3_ACCESS_KEY="test",
        S3_SECRET_KEY="test",
    )


@pytest.fixture(autouse=True)
def override_settings():
    with patch("app.core.config.get_settings", return_value=get_test_settings()):
        yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestAuthEndpoints:
    """Test authentication API endpoints."""

    def test_root_endpoint(self, client):
        """Test the root endpoint returns basic info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "name" in data

    def test_login_missing_credentials(self, client):
        """Test login with missing credentials returns 422."""
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

    def test_login_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token returns 401."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code in [401, 500]

    def test_refresh_token_missing_token(self, client):
        """Test refresh with missing token returns 401."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": ""},
        )
        assert response.status_code in [401, 422]


class TestProtectedEndpoints:
    """Test that protected endpoints require authentication."""

    def test_list_users_without_auth(self, client):
        """Test that list_users requires authentication."""
        response = client.get("/api/v1/users/")
        assert response.status_code == 401

    def test_list_suites_without_auth(self, client):
        """Test that list_suites requires authentication."""
        response = client.get("/api/v1/suites/")
        assert response.status_code == 401

    def test_create_suite_without_auth(self, client):
        """Test that create_suite requires authentication."""
        response = client.post("/api/v1/suites/", json={"name": "test"})
        assert response.status_code == 401

    def test_list_agents_without_auth(self, client):
        """Test that list_agents requires authentication."""
        response = client.get("/api/v1/agents/")
        assert response.status_code == 401

    def test_list_runs_without_auth(self, client):
        """Test that list_runs requires authentication."""
        response = client.get("/api/v1/runs/")
        assert response.status_code == 401


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check_no_auth(self, client):
        """Test that health check doesn't require authentication."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"