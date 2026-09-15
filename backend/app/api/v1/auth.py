from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, get_user_repo
from app.core.exceptions import AuthenticationError
from app.core.logging import get_logger
from app.core.security import (
    TokenData,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_password_hash,
    get_scopes_for_roles,
    verify_password,
)
from app.models.user import User
from app.repositories.users import UserRepository

router = APIRouter()
logger = get_logger(__name__)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str | None = None


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repo),
):
    user = await user_repo.get_by_email_or_username(request.username)
    if not user or not verify_password(request.password, user.hashed_password):
        logger.warning("login_failed", username=request.username)
        raise AuthenticationError("Invalid credentials")

    if not user.is_active:
        raise AuthenticationError("Account is disabled")

    roles = [role.name for role in user.roles]
    scopes = get_scopes_for_roles(roles)

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "roles": roles,
            "scopes": scopes,
        }
    )
    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "roles": roles,
            "scopes": scopes,
        }
    )

    user.last_login = datetime.now(UTC)
    await db.commit()

    logger.info("login_success", user_id=str(user.id))
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=30 * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repo),
):
    try:
        token_data = decode_refresh_token(request.refresh_token)
    except Exception:
        raise AuthenticationError("Invalid refresh token")

    # SECURITY: Verify user still exists and is active
    user = await user_repo.get(UUID(token_data.sub))
    if not user:
        raise AuthenticationError("User not found")
    if not user.is_active:
        raise AuthenticationError("User account is disabled")

    # Get fresh roles from database
    roles = [role.name for role in user.roles]
    scopes = get_scopes_for_roles(roles)

    access_token = create_access_token(
        data={
            "sub": token_data.sub,
            "username": user.username,
            "email": user.email,
            "roles": roles,
            "scopes": scopes,
        }
    )
    new_refresh_token = create_refresh_token(
        data={
            "sub": token_data.sub,
            "username": user.username,
            "email": user.email,
            "roles": roles,
            "scopes": scopes,
        }
    )

    logger.info("token_refreshed", user_id=token_data.sub)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=30 * 60,
    )


@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repo),
):
    from app.core.config import get_settings

    settings = get_settings()
    
    # SECURITY: In production, strictly control registration
    if settings.is_production:
        # Check if open registration is explicitly allowed via feature flag
        # Note: FEATURE_EXPERIMENTAL_UI should NOT control security features
        if not getattr(settings, "ALLOW_OPEN_REGISTRATION", False):
            # Allow registration only if no users exist (bootstrap scenario)
            all_users = await user_repo.list(skip=0, limit=1)
            if len(all_users) > 0:
                raise HTTPException(
                    status_code=403,
                    detail="Registration is disabled in production. Contact your administrator for an invitation.",
                )

    # Password strength validation - comprehensive checks
    if len(request.password) < 12:
        raise HTTPException(status_code=400, detail="Password must be at least 12 characters")
    if request.password.lower() == request.password or request.password.upper() == request.password:
        raise HTTPException(status_code=400, detail="Password must contain mixed case")
    if not any(c.isdigit() for c in request.password):
        raise HTTPException(status_code=400, detail="Password must contain at least one digit")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in request.password):
        raise HTTPException(status_code=400, detail="Password must contain at least one special character")
    
    # Check for username/email in password
    if request.username.lower() in request.password.lower():
        raise HTTPException(status_code=400, detail="Password must not contain username")
    if request.email.split("@")[0].lower() in request.password.lower():
        raise HTTPException(status_code=400, detail="Password must not contain email")
    
    # Check for common weak passwords
    COMMON_WEAK_PASSWORDS = {
        "password123", "password12", "qwerty123", "admin123", "welcome123",
        "changeme123", "letmein123", "monkey123", "dragon123", "master123"
    }
    if request.password.lower() in COMMON_WEAK_PASSWORDS:
        raise HTTPException(status_code=400, detail="Password is too common - choose a stronger password")

    if await user_repo.get_by_email(request.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    if await user_repo.get_by_username(request.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    hashed_password = get_password_hash(request.password)
    user = User(
        email=request.email,
        username=request.username,
        hashed_password=hashed_password,
        full_name=request.full_name,
    )
    user = await user_repo.create(user)

    await db.commit()

    roles = [role.name for role in user.roles]
    scopes = get_scopes_for_roles(roles)

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "roles": roles,
            "scopes": scopes,
        }
    )
    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "roles": roles,
            "scopes": scopes,
        }
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=30 * 60,
    )


@router.get("/me")
async def get_current_user_info(current_user: TokenData = Depends(get_current_active_user)):
    return {
        "id": current_user.sub,
        "username": current_user.username,
        "email": current_user.email,
        "roles": current_user.roles,
        "scopes": current_user.scopes,
    }
