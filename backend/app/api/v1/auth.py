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
    full_name: str = None


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
async def refresh_token(request: RefreshRequest):
    try:
        token_data = decode_refresh_token(request.refresh_token)
    except Exception:
        raise AuthenticationError("Invalid refresh token")

    access_token = create_access_token(
        data={
            "sub": token_data.sub,
            "username": token_data.username,
            "email": token_data.email,
            "roles": token_data.roles,
            "scopes": token_data.scopes,
        }
    )
    new_refresh_token = create_refresh_token(
        data={
            "sub": token_data.sub,
            "username": token_data.username,
            "email": token_data.email,
            "roles": token_data.roles,
            "scopes": token_data.scopes,
        }
    )

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
