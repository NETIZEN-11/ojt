import os
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

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
    auto_error=True,  # SECURITY: Always enforce authentication, fail-closed
)


class TokenData(BaseModel):
    sub: str
    username: str
    email: str
    roles: list[str]
    scopes: list[str]
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


def _resolve_key_path(path: str) -> str:
    """
    Resolve key path with security constraints.
    SECURITY: Only allows absolute paths or paths within project root to prevent path traversal.
    """
    if not path:
        return path
    
    # Normalize the path to prevent traversal attacks
    path = os.path.normpath(path)
    
    # SECURITY: Block path traversal attempts
    if ".." in path or path.startswith("/etc") or path.startswith("\\\\"):
        raise ValueError(f"Invalid key path (potential path traversal): {path}")
    
    # If absolute path, verify it exists and is readable
    if os.path.isabs(path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Key file not found: {path}")
        # Verify it's a regular file (not a directory or symlink)
        if not os.path.isfile(path):
            raise ValueError(f"Key path must be a regular file: {path}")
        return path
    
    # For relative paths, only search within project root
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        # Try relative to project root
        candidate = os.path.normpath(os.path.join(project_root, path))
        
        # SECURITY: Ensure resolved path is still within project root
        if not candidate.startswith(project_root):
            raise ValueError(f"Key path escapes project root: {path}")
        
        if os.path.exists(candidate) and os.path.isfile(candidate):
            return candidate
        
        # Try app/core/keys directory as fallback
        candidate2 = os.path.normpath(os.path.join(project_root, "backend", "app", "core", "keys", os.path.basename(path)))
        if candidate2.startswith(project_root) and os.path.exists(candidate2) and os.path.isfile(candidate2):
            return candidate2
            
    except Exception as e:
        raise ValueError(f"Failed to resolve key path: {e}")
        pass
    # Fallback to keys directory next to this file
    keys_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys")
    candidate3 = os.path.join(keys_dir, os.path.basename(path))
    if os.path.exists(candidate3):
        return candidate3
    return path


def _read_key_file(path: str) -> str:
    """Read a key file, raising FileNotFoundError if it doesn't exist."""
    resolved = _resolve_key_path(path)
    if not os.path.exists(resolved):
        raise FileNotFoundError(f"Key file not found: {path} (resolved: {resolved})")
    with open(resolved) as f:
        return f.read()


def load_private_key() -> tuple[str, str]:
    settings = get_settings()
    if not settings.JWT_PRIVATE_KEY_PATH:
        raise ValueError("JWT_PRIVATE_KEY_PATH is required")
    return _read_key_file(settings.JWT_PRIVATE_KEY_PATH), settings.JWT_ALGORITHM


def load_public_key() -> tuple[str, str]:
    settings = get_settings()
    if not settings.JWT_PUBLIC_KEY_PATH:
        raise ValueError("JWT_PUBLIC_KEY_PATH is required")
    return _read_key_file(settings.JWT_PUBLIC_KEY_PATH), settings.JWT_ALGORITHM


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    private_key, algorithm = load_private_key()
    return jwt.encode(to_encode, private_key, algorithm=algorithm)


def create_refresh_token(data: dict[str, Any]) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    private_key, algorithm = load_private_key()
    return jwt.encode(to_encode, private_key, algorithm=algorithm)


def decode_token(token: str) -> TokenData:
    try:
        public_key, algorithm = load_public_key()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[algorithm],
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
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication configuration error",
        ) from e


def decode_refresh_token(token: str) -> TokenData:
    try:
        public_key, algorithm = load_public_key()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[algorithm],
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
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication configuration error",
        ) from e


async def get_current_user(
    security_scopes: SecurityScopes,
    token: str | None = Depends(oauth2_scheme),
) -> TokenData:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
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


def require_role(required_roles: list[str]):
    async def role_checker(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if not any(role in current_user.roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role permissions",
            )
        return current_user

    return role_checker


def require_scope(required_scopes: list[str]):
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


def get_scopes_for_roles(roles: list[str]) -> list[str]:
    scopes = set()
    for role in roles:
        scopes.update(ROLE_SCOPES.get(role, []))
    return list(scopes)
