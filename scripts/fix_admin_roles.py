#!/usr/bin/env python3
"""Fix admin user roles."""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.user import User, Role, Permission


async def fix_roles():
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Create permissions
        permissions = {}
        permission_list = [
            ("users:read", "users", "read"),
            ("users:write", "users", "write"),
            ("agents:read", "agents", "read"),
            ("agents:write", "agents", "write"),
            ("suites:read", "suites", "read"),
            ("suites:write", "suites", "write"),
            ("runs:read", "runs", "read"),
            ("runs:write", "runs", "write"),
            ("results:read", "results", "read"),
            ("baselines:read", "baselines", "read"),
            ("baselines:write", "baselines", "write"),
            ("regressions:read", "regressions", "read"),
            ("reviews:read", "reviews", "read"),
            ("reports:read", "reports", "read"),
            ("settings:read", "settings", "read"),
            ("settings:write", "settings", "write"),
        ]
        
        for perm_name, resource, action in permission_list:
            # Check if exists
            result = await session.execute(
                select(Permission).where(Permission.name == perm_name)
            )
            perm = result.scalar_one_or_none()
            if not perm:
                perm = Permission(name=perm_name, resource=resource, action=action)
                session.add(perm)
                await session.flush()
            permissions[perm_name] = perm
        
        print(f"✓ Created/verified {len(permissions)} permissions")
        
        # Create admin role
        result = await session.execute(select(Role).where(Role.name == "admin"))
        admin_role = result.scalar_one_or_none()
        
        if not admin_role:
            admin_role = Role(
                name="admin",
                description="Full administrative access",
                is_system=True,
                permissions=list(permissions.values())
            )
            session.add(admin_role)
            await session.flush()
            print("✓ Created admin role")
        else:
            # Update permissions
            admin_role.permissions = list(permissions.values())
            print("✓ Updated admin role permissions")
        
        # Get admin user and assign role
        result = await session.execute(
            select(User).where(User.username == "admin").options(selectinload(User.roles))
        )
        admin_user = result.scalar_one_or_none()
        
        if admin_user:
            if admin_role not in admin_user.roles:
                admin_user.roles.append(admin_role)
                print(f"✓ Assigned admin role to user {admin_user.username}")
            else:
                print(f"✓ User {admin_user.username} already has admin role")
        else:
            print("✗ Admin user not found")
        
        await session.commit()
        print("\n✅ Roles and permissions fixed successfully!")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(fix_roles())
