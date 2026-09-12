import pytest
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timedelta
from uuid import uuid4

from app.core.config import Settings


@pytest.fixture
def test_settings():
    """Provide test settings for all tests."""
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
        EVAL_MODE="local",
        DEV_MOCK_JUDGE=True,
        DEV_MOCK_TARGET_AGENT=True,
        DEV_SEED_DATA=True,
        S3_ACCESS_KEY="test_access_key",
        S3_SECRET_KEY="test_secret_key",
    )


@pytest.fixture(autouse=True)
def mock_settings(test_settings):
    """Override settings globally for tests."""
    with patch("app.core.config.get_settings", return_value=test_settings):
        yield


@pytest.fixture
def client():
    """Provide a FastAPI test client."""
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_access_token():
    """Generate a valid access token for testing."""
    from app.core.security import create_access_token

    with patch("app.core.config.get_settings", return_value=test_settings()), \
         patch("builtins.open", mock_open(read_data="fake_key")):
        return create_access_token(
            data={
                "sub": str(uuid4()),
                "username": "test_user",
                "email": "test@example.com",
                "roles": ["admin"],
                "scopes": ["admin", "safety_engineer"],
                "type": "access",
            },
            expires_delta=timedelta(hours=1),
        )


@pytest.fixture
def admin_headers(sample_access_token):
    """Provide authorization headers for admin requests."""
    return {"Authorization": f"Bearer {sample_access_token}"}


@pytest.fixture
def viewer_token():
    """Generate a viewer access token."""
    from app.core.security import create_access_token

    with patch("app.core.config.get_settings", return_value=test_settings()), \
         patch("builtins.open", mock_open(read_data="fake_key")):
        token = create_access_token(
            data={
                "sub": str(uuid4()),
                "username": "viewer_user",
                "email": "viewer@example.com",
                "roles": ["viewer"],
                "scopes": ["viewer"],
                "type": "access",
            },
            expires_delta=timedelta(hours=1),
        )
    return token


@pytest.fixture
def viewer_headers(viewer_token):
    """Provide authorization headers for viewer requests."""
    return {"Authorization": f"Bearer {viewer_token}"}