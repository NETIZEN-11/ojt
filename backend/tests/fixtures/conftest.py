import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.core.security import create_access_token, create_refresh_token, TokenData


@pytest.fixture
def access_token():
    return create_access_token(
        data={
            "sub": str(uuid4()),
            "username": "test_user",
            "email": "test@example.com",
            "roles": ["admin"],
            "scopes": ["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"],
        }
    )


@pytest.fixture
def refresh_token():
    return create_refresh_token(
        data={
            "sub": str(uuid4()),
            "username": "test_user",
            "email": "test@example.com",
            "roles": ["admin"],
            "scopes": ["admin"],
        }
    )


@pytest.fixture
def token_data():
    return TokenData(
        sub=str(uuid4()),
        username="test_user",
        email="test@example.com",
        roles=["admin"],
        scopes=["admin", "safety_engineer"],
        exp=int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
    )


@pytest.fixture
def admin_token_header(access_token):
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def viewer_token_header():
    from app.core.security import create_access_token
    token = create_access_token(
        data={
            "sub": str(uuid4()),
            "username": "viewer_user",
            "email": "viewer@example.com",
            "roles": ["viewer"],
            "scopes": ["viewer"],
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def safety_engineer_token_header():
    from app.core.security import create_access_token
    token = create_access_token(
        data={
            "sub": str(uuid4()),
            "username": "safety_user",
            "email": "safety@example.com",
            "roles": ["safety_engineer"],
            "scopes": ["safety_engineer", "ml_engineer", "qa_engineer", "viewer"],
        }
    )
    return {"Authorization": f"Bearer {token}"}