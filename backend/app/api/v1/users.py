from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr

from app.api.deps import TokenData, get_permission_repo, get_role_repo, get_user_repo, require_role
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.models.user import Role
from app.repositories.users import PermissionRepository, RoleRepository, UserRepository

router = APIRouter()
logger = get_logger(__name__)


class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    full_name: str | None = None
    is_active: bool
    is_superuser: bool
    roles: list[str]
    created_at: datetime | str

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    is_active: bool | None = None


class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_system: bool

    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    name: str
    description: str | None = None


class PermissionResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    resource: str
    action: str

    class Config:
        from_attributes = True


@router.get("/", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    user_repo: UserRepository = Depends(get_user_repo),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    users = await user_repo.list(skip=skip, limit=limit)
    return [
        UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            roles=[role.name for role in user.roles],
            created_at=user.created_at.isoformat(),
        )
        for user in users
    ]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    user_repo: UserRepository = Depends(get_user_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer"])),
):
    user = await user_repo.get_with_roles(user_id)
    if not user:
        raise NotFoundError("User", str(user_id))
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        roles=[role.name for role in user.roles],
        created_at=user.created_at.isoformat(),
    )


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    update: UserUpdate,
    user_repo: UserRepository = Depends(get_user_repo),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    user = await user_repo.get(user_id)
    if not user:
        raise NotFoundError("User", str(user_id))

    update_data = update.model_dump(exclude_unset=True)
    if "email" in update_data:
        existing = await user_repo.get_by_email(update_data["email"])
        if existing and existing.id != user_id:
            raise ConflictError("Email already in use")

    for key, value in update_data.items():
        setattr(user, key, value)

    await user_repo.session.flush()
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        roles=[role.name for role in user.roles],
        created_at=user.created_at.isoformat(),
    )


@router.post("/{user_id}/roles/{role_id}")
async def assign_role(
    user_id: UUID,
    role_id: UUID,
    user_repo: UserRepository = Depends(get_user_repo),
    role_repo: RoleRepository = Depends(get_role_repo),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    user = await user_repo.get_with_roles(user_id)
    if not user:
        raise NotFoundError("User", str(user_id))

    role = await role_repo.get(role_id)
    if not role:
        raise NotFoundError("Role", str(role_id))

    if role not in user.roles:
        user.roles.append(role)
        await user_repo.session.flush()

    return {"message": "Role assigned"}


@router.delete("/{user_id}/roles/{role_id}")
async def remove_role(
    user_id: UUID,
    role_id: UUID,
    user_repo: UserRepository = Depends(get_user_repo),
    role_repo: RoleRepository = Depends(get_role_repo),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    user = await user_repo.get_with_roles(user_id)
    if not user:
        raise NotFoundError("User", str(user_id))

    role = await role_repo.get(role_id)
    if not role:
        raise NotFoundError("Role", str(role_id))

    if role in user.roles:
        user.roles.remove(role)
        await user_repo.session.flush()

    return {"message": "Role removed"}


@router.get("/roles/", response_model=list[RoleResponse])
async def list_roles(
    role_repo: RoleRepository = Depends(get_role_repo),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    roles = await role_repo.list()
    return [RoleResponse.model_validate(role) for role in roles]


@router.post("/roles/", response_model=RoleResponse)
async def create_role(
    role: RoleCreate,
    role_repo: RoleRepository = Depends(get_role_repo),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    if await role_repo.get_by_name(role.name):
        raise ConflictError("Role already exists")

    new_role = Role(name=role.name, description=role.description)
    new_role = await role_repo.create(new_role)
    return RoleResponse.model_validate(new_role)


@router.get("/permissions/", response_model=list[PermissionResponse])
async def list_permissions(
    permission_repo: PermissionRepository = Depends(get_permission_repo),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    permissions = await permission_repo.list()
    return [PermissionResponse.model_validate(p) for p in permissions]
