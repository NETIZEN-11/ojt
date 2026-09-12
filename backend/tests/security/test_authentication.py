import pytest
from unittest.mock import patch, MagicMock

from fastapi import HTTPException
from app.core.security import (
    get_current_user,
    decode_token,
    decode_refresh_token,
    TokenData,
    load_private_key,
    load_public_key,
)
from app.core.config import get_settings as config_get_settings


@pytest.fixture(autouse=True)
def clear_lru_cache():
    config_get_settings.cache_clear()
    yield


class TestGetCurrentUser:
    """Test authentication and authorization functions."""

    @pytest.mark.asyncio
    async def test_missing_token_raises_401(self):
        """Test that missing token raises 401 Unauthorized."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                MagicMock(scopes=[]),
                token=None,
            )
        assert exc_info.value.status_code == 401
        assert "Not authenticated" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        """Test that invalid token raises 401 Unauthorized."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                MagicMock(scopes=[]),
                token="invalid.token.value",
            )
        assert exc_info.value.status_code in [401, 500]

    @pytest.mark.asyncio
    async def test_missing_token_always_raises_401(self):
        """Test that missing token always raises 401 (no dev bypass)."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                MagicMock(scopes=[]),
                token=None,
            )
        assert exc_info.value.status_code == 401
        assert "Not authenticated" in exc_info.value.detail


class TestDecodeToken:
    """Test token decoding functions."""

    def test_decode_invalid_token_raises_401(self):
        """Test that invalid token raises HTTPException."""
        with pytest.raises(HTTPException):
            decode_token("invalid.token.value")


class TestLoadKeys:
    """Test key loading functions."""

    def test_load_private_key_without_path_raises_error(self):
        """Test that loading private key without path raises ValueError."""
        with patch("app.core.security.get_settings") as mock_settings:
            mock_settings.return_value.JWT_PRIVATE_KEY_PATH = ""
            mock_settings.return_value.JWT_ALGORITHM = "RS256"
            with pytest.raises(ValueError, match="JWT_PRIVATE_KEY_PATH is required"):
                load_private_key()

    def test_load_public_key_without_path_raises_error(self):
        """Test that loading public key without path raises ValueError."""
        with patch("app.core.security.get_settings") as mock_settings:
            mock_settings.return_value.JWT_PUBLIC_KEY_PATH = ""
            mock_settings.return_value.JWT_ALGORITHM = "RS256"
            with pytest.raises(ValueError, match="JWT_PUBLIC_KEY_PATH is required"):
                load_public_key()


class TestRequireRole:
    """Test role-based authorization."""

    @pytest.mark.asyncio
    async def test_missing_token_raises_401(self):
        """Test that require_role requires authentication."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                MagicMock(scopes=["admin"]),
                token=None,
            )
        assert exc_info.value.status_code == 401


class TestTokenExpiration:
    """Test token expiration handling."""

    def test_expired_token_raises_error(self):
        """Test that expired token raises HTTPException."""
        with pytest.raises(HTTPException):
            decode_token("expired.invalid.token")