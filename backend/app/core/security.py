import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from pathlib import Path

from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, SecurityScopes

from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    scopes={
        "admin": "Full administrative access",
        "safety_engineer": "Create and manage test suites, baselines",
        "ml_engineer": "Run evaluations, view results",
        "qa_engineer": "Run evaluations, manage test cases",
        "reviewer": "Review and label findings",
        "viewer": "Read-only access to dashboards and reports",
    },
)


class TokenData(BaseModel):
    sub: str
    username: str
    email: str
    roles: List[str]
    scopes: List[str]
    exp: int


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def load_private_key() -> tuple[str, str]:
    if settings.JWT_PRIVATE_KEY_PATH and os.path.exists(settings.JWT_PRIVATE_KEY_PATH):
        with open(settings.JWT_PRIVATE_KEY_PATH, "r") as f:
            return f.read(), settings.JWT_ALGORITHM
    return settings.SECRET_KEY, "HS256"


def load_public_key() -> tuple[str, str]:
    if settings.JWT_PUBLIC_KEY_PATH and os.path.exists(settings.JWT_PUBLIC_KEY_PATH):
        with open(settings.JWT_PUBLIC_KEY_PATH, "r") as f:
            return f.read(), settings.JWT_ALGORITHM
    return settings.SECRET_KEY, "HS256"


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    private_key, algorithm = load_private_key()
    return jwt.encode(to_encode, private_key, algorithm=algorithm)


def create_refresh_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    private_key, algorithm = load_private_key()
    return jwt.encode(to_encode, private_key, algorithm=algorithm)


def decode_token(token: str) -> TokenData:
    try:
        public_key, algorithm = load_public_key()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[algorithm, "HS256", "RS256"],
            options={"verify_aud": False},
        )
        if payload.get("type") != "access":
            raise JWTError("Invalid token type")
        return TokenData(**payload)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def decode_refresh_token(token: str) -> TokenData:
    try:
        public_key, algorithm = load_public_key()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[algorithm, "HS256", "RS256"],
            options={"verify_aud": False},
        )
        if payload.get("type") != "refresh":
            raise JWTError("Invalid token type")
        return TokenData(**payload)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
) -> TokenData:
    token_data = decode_token(token)
    if security_scopes.scopes:
        for scope in security_scopes.scopes:
            if scope not in token_data.scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions",
                    headers={"WWW-Authenticate": f'Bearer scope="{security_scopes.scope_str}"'},
                )
    return token_data


def require_role(required_roles: List[str]):
    async def role_checker(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if not any(role in current_user.roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role permissions",
            )
        return current_user

    return role_checker


def require_scope(required_scopes: List[str]):
    async def scope_checker(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if not any(scope in current_user.scopes for scope in required_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient scope permissions",
            )
        return current_user

    return scope_checker


ROLE_SCOPES = {
    "admin": ["admin", "safety_engineer", "ml_engineer", "qa_engineer", "reviewer", "viewer"],
    "safety_engineer": ["safety_engineer", "ml_engineer", "qa_engineer", "reviewer", "viewer"],
    "ml_engineer": ["ml_engineer", "qa_engineer", "viewer"],
    "qa_engineer": ["qa_engineer", "viewer"],
    "reviewer": ["reviewer", "viewer"],
    "viewer": ["viewer"],
}


def get_scopes_for_roles(roles: List[str]) -> List[str]:
    scopes = set()
    for role in roles:
        scopes.update(ROLE_SCOPES.get(role, []))
    return list(scopes)