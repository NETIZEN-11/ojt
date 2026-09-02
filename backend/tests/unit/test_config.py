from app.core.config import Settings


def test_settings_load():
    """Test that settings can be instantiated with required fields."""
    settings = Settings(
        SECRET_KEY="a" * 32,
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        REDIS_URL="redis://localhost:6379/0",
        CELERY_BROKER_URL="redis://localhost:6379/1",
        CELERY_RESULT_BACKEND="redis://localhost:6379/2",
    )
    assert settings.APP_NAME == "Agent Red-Teaming Framework"
    assert settings.SECRET_KEY == "a" * 32
    assert settings.ENVIRONMENT == "development"
    assert settings.DEBUG is True


def test_settings_cors_parsing():
    """Test CORS origins parsing."""
    settings = Settings(
        SECRET_KEY="a" * 32,
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        REDIS_URL="redis://localhost:6379/0",
        CELERY_BROKER_URL="redis://localhost:6379/1",
        CELERY_RESULT_BACKEND="redis://localhost:6379/2",
        CORS_ORIGINS="http://localhost:3000, http://localhost:8000",
    )
    assert len(settings.cors_origins_list) == 2
    assert "http://localhost:3000" in settings.cors_origins_list
    assert "http://localhost:8000" in settings.cors_origins_list


def test_settings_allowed_hosts_parsing():
    """Test target agent allowed hosts parsing."""
    settings = Settings(
        SECRET_KEY="a" * 32,
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        REDIS_URL="redis://localhost:6379/0",
        CELERY_BROKER_URL="redis://localhost:6379/1",
        CELERY_RESULT_BACKEND="redis://localhost:6379/2",
        TARGET_AGENT_ALLOWED_HOSTS="api.example.com, internal.example.com",
    )
    assert len(settings.allowed_hosts_list) == 2
    assert "api.example.com" in settings.allowed_hosts_list
    assert "internal.example.com" in settings.allowed_hosts_list


def test_settings_is_production():
    """Test environment detection."""
    settings = Settings(
        SECRET_KEY="a" * 32,
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        REDIS_URL="redis://localhost:6379/0",
        CELERY_BROKER_URL="redis://localhost:6379/1",
        CELERY_RESULT_BACKEND="redis://localhost:6379/2",
        ENVIRONMENT="production",
    )
    assert settings.is_production is True
    assert settings.is_development is False
