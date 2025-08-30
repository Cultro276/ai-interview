"""
Enterprise Role-Based Access Control (RBAC) System
Granular permissions, role hierarchy, and resource-based access control
"""
from enum import Enum
from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass
from sqlalchemy import String, Text, Boolean, ForeignKey, Table, Column, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base
import json


class Permission(str, Enum):
    """
    Granular permissions for enterprise access control
    """
    # User management
    USER_CREATE = "user.create"
    USER_READ = "user.read"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    USER_LIST = "user.list"
    USER_INVITE = "user.invite"
    USER_DISABLE = "user.disable"
    
    # Job management
    JOB_CREATE = "job.create"
    JOB_READ = "job.read"
    JOB_UPDATE = "job.update"
    JOB_DELETE = "job.delete"
    JOB_LIST = "job.list"
    JOB_PUBLISH = "job.publish"
    JOB_ARCHIVE = "job.archive"
    
    # Candidate management
    CANDIDATE_CREATE = "candidate.create"
    CANDIDATE_READ = "candidate.read"
    CANDIDATE_UPDATE = "candidate.update"
    CANDIDATE_DELETE = "candidate.delete"
    CANDIDATE_LIST = "candidate.list"
    CANDIDATE_INVITE = "candidate.invite"
    CANDIDATE_EXPORT = "candidate.export"
    CANDIDATE_BULK_UPLOAD = "candidate.bulk_upload"
    
    # Interview management
    INTERVIEW_CREATE = "interview.create"
    INTERVIEW_READ = "interview.read"
    INTERVIEW_UPDATE = "interview.update"
    INTERVIEW_DELETE = "interview.delete"
    INTERVIEW_LIST = "interview.list"
    INTERVIEW_CONDUCT = "interview.conduct"
    INTERVIEW_REVIEW = "interview.review"
    INTERVIEW_RESCHEDULE = "interview.reschedule"
    
    # Report access
    REPORT_VIEW = "report.view"
    REPORT_EXPORT = "report.export"
    REPORT_CREATE = "report.create"
    REPORT_ANALYTICS = "report.analytics"
    
    # Admin functions
    ADMIN_SETTINGS = "admin.settings"
    ADMIN_LOGS = "admin.logs"
    ADMIN_METRICS = "admin.metrics"
    ADMIN_BACKUP = "admin.backup"
    ADMIN_RESTORE = "admin.restore"
    
    # Team management
    TEAM_CREATE = "team.create"
    TEAM_MANAGE = "team.manage"
    TEAM_INVITE = "team.invite"
    TEAM_REMOVE = "team.remove"
    
    # Data access (GDPR compliance)
    DATA_EXPORT = "data.export"
    DATA_DELETE = "data.delete"
    DATA_ANONYMIZE = "data.anonymize"
    
    # System permissions
    SYSTEM_MONITOR = "system.monitor"
    SYSTEM_CONFIGURE = "system.configure"
    SYSTEM_MAINTAIN = "system.maintain"


class ResourceType(str, Enum):
    """
    Resource types for resource-based access control
    """
    USER = "user"
    JOB = "job"
    CANDIDATE = "candidate"
    INTERVIEW = "interview"
    REPORT = "report"
    TEAM = "team"
    ORGANIZATION = "organization"
    SYSTEM = "system"


class AccessLevel(str, Enum):
    """
    Access levels for hierarchical permissions
    """
    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    OWNER = "owner"


# Association tables for many-to-many relationships
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True)
)

# user_roles = Table(
#     'user_roles',
#     Base.metadata,
#     Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
#     Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True)
# )


class PermissionModel(Base):
    """
    Database model for permissions
    """
    __tablename__ = "permissions"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


class Role(Base):
    """
    Database model for roles
    """
    __tablename__ = "roles"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=0)  # Role hierarchy level
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Tenant isolation
    organization_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Relationships
    permissions = relationship("PermissionModel", secondary=role_permissions, back_populates="roles")
    # Note: User relationship will be established without back_populates to avoid circular import issues


class ResourcePermission(Base):
    """
    Resource-specific permissions (e.g., user can only access specific jobs)
    """
    __tablename__ = "resource_permissions"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False)
    access_level: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Additional metadata
    granted_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    granted_at: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    expires_at: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


@dataclass
class AccessContext:
    """
    Context for access control decisions
    """
    user_id: int
    organization_id: Optional[int] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Resource context
    resource_type: Optional[ResourceType] = None
    resource_id: Optional[int] = None
    resource_owner_id: Optional[int] = None
    
    # Request context
    action: Optional[str] = None
    endpoint: Optional[str] = None


class RBACManager:
    """
    Enterprise RBAC manager
    Handles role assignment, permission checking, and access control
    """
    
    def __init__(self):
        self._role_cache: Dict[int, Set[Permission]] = {}
        self._permission_cache: Dict[str, Set[Permission]] = {}
        self._initialize_system_roles()
    
    def _initialize_system_roles(self):
        """
        Initialize default system roles
        """
        self.system_roles = {
            "super_admin": {
                "level": 100,
                "permissions": list(Permission),
                "description": "Full system access"
            },
            "organization_admin": {
                "level": 80,
                "permissions": [
                    Permission.USER_CREATE, Permission.USER_READ, Permission.USER_UPDATE,
                    Permission.USER_LIST, Permission.USER_INVITE, Permission.USER_DISABLE,
                    Permission.JOB_CREATE, Permission.JOB_READ, Permission.JOB_UPDATE,
                    Permission.JOB_DELETE, Permission.JOB_LIST, Permission.JOB_PUBLISH,
                    Permission.CANDIDATE_CREATE, Permission.CANDIDATE_READ, Permission.CANDIDATE_UPDATE,
                    Permission.CANDIDATE_LIST, Permission.CANDIDATE_INVITE, Permission.CANDIDATE_EXPORT,
                    Permission.INTERVIEW_CREATE, Permission.INTERVIEW_READ, Permission.INTERVIEW_UPDATE,
                    Permission.INTERVIEW_LIST, Permission.INTERVIEW_REVIEW,
                    Permission.REPORT_VIEW, Permission.REPORT_EXPORT, Permission.REPORT_ANALYTICS,
                    Permission.TEAM_CREATE, Permission.TEAM_MANAGE, Permission.TEAM_INVITE
                ],
                "description": "Organization administration"
            },
            "hr_manager": {
                "level": 60,
                "permissions": [
                    Permission.JOB_CREATE, Permission.JOB_READ, Permission.JOB_UPDATE, Permission.JOB_LIST,
                    Permission.CANDIDATE_CREATE, Permission.CANDIDATE_READ, Permission.CANDIDATE_UPDATE,
                    Permission.CANDIDATE_LIST, Permission.CANDIDATE_INVITE, Permission.CANDIDATE_EXPORT,
                    Permission.INTERVIEW_CREATE, Permission.INTERVIEW_READ, Permission.INTERVIEW_UPDATE,
                    Permission.INTERVIEW_LIST, Permission.INTERVIEW_REVIEW,
                    Permission.REPORT_VIEW, Permission.REPORT_EXPORT
                ],
                "description": "HR management functions"
            },
            "interviewer": {
                "level": 40,
                "permissions": [
                    Permission.JOB_READ, Permission.JOB_LIST,
                    Permission.CANDIDATE_READ, Permission.CANDIDATE_LIST,
                    Permission.INTERVIEW_READ, Permission.INTERVIEW_CONDUCT, Permission.INTERVIEW_REVIEW,
                    Permission.REPORT_VIEW
                ],
                "description": "Interview conducting"
            },
            "recruiter": {
                "level": 30,
                "permissions": [
                    Permission.JOB_READ, Permission.JOB_LIST,
                    Permission.CANDIDATE_CREATE, Permission.CANDIDATE_READ, Permission.CANDIDATE_UPDATE,
                    Permission.CANDIDATE_LIST, Permission.CANDIDATE_INVITE,
                    Permission.INTERVIEW_CREATE, Permission.INTERVIEW_READ, Permission.INTERVIEW_LIST,
                    Permission.REPORT_VIEW
                ],
                "description": "Recruitment functions"
            },
            "viewer": {
                "level": 10,
                "permissions": [
                    Permission.JOB_READ, Permission.JOB_LIST,
                    Permission.CANDIDATE_READ, Permission.CANDIDATE_LIST,
                    Permission.INTERVIEW_READ, Permission.INTERVIEW_LIST,
                    Permission.REPORT_VIEW
                ],
                "description": "Read-only access"
            }
        }
    
    async def check_permission(
        self,
        context: AccessContext,
        permission: Permission,
        resource_id: Optional[int] = None
    ) -> bool:
        """
        Check if user has specific permission
        """
        try:
            # Get user permissions
            user_permissions = await self._get_user_permissions(context.user_id)
            
            # Check direct permission
            if permission in user_permissions:
                # Additional resource-level checks
                if resource_id:
                    return await self._check_resource_permission(
                        context, permission, resource_id
                    )
                return True
            
            # Check role-based permissions with hierarchy
            return await self._check_role_hierarchy_permission(
                context, permission, resource_id
            )
            
        except Exception as e:
            # Log security event
            from src.core.audit import audit_security_event, AuditContext
            await audit_security_event(
                "permission_check_error",
                {"error": str(e), "permission": permission.value, "user_id": context.user_id},
                AuditContext(user_id=context.user_id, ip_address=context.ip_address)
            )
            return False
    
    async def _get_user_permissions(self, user_id: int) -> Set[Permission]:
        """
        Get all permissions for a user (from roles and direct assignments)
        """
        if user_id in self._role_cache:
            return self._role_cache[user_id]
        
        from src.db.session import async_session_factory
        from sqlalchemy import select
        
        permissions = set()
        
        async with async_session_factory() as session:
            # Get permissions from roles
            # Temporarily disabled RBAC system - fallback to simple permissions
            # query = select(PermissionModel).join(role_permissions).join(user_roles).where(
            #     user_roles.c.user_id == user_id
            # )
            return set()  # Return empty permissions for now
            # result = await session.execute(query)
            # role_permissions_result = result.scalars().all()
            # 
            # for perm in role_permissions_result:
            #     try:
            #         permissions.add(Permission(perm.name))
            #     except ValueError:
            #         # Skip invalid permissions
            #         continue
        
        # Cache for performance
        self._role_cache[user_id] = permissions
        return permissions
    
    async def _check_resource_permission(
        self,
        context: AccessContext,
        permission: Permission,
        resource_id: int
    ) -> bool:
        """
        Check resource-specific permissions
        """
        from src.db.session import async_session_factory
        from sqlalchemy import select, and_
        
        async with async_session_factory() as session:
            # Check direct resource permission
            if context.resource_type is None:
                return False
                
            query = select(ResourcePermission).where(
                and_(
                    ResourcePermission.user_id == context.user_id,
                    ResourcePermission.resource_type == context.resource_type.value,
                    ResourcePermission.resource_id == resource_id
                )
            )
            result = await session.execute(query)
            resource_perm = result.scalar_one_or_none()
            
            if resource_perm:
                # Check access level
                required_level = self._get_required_access_level(permission)
                user_level = AccessLevel(resource_perm.access_level)
                return self._access_level_sufficient(user_level, required_level)
            
            # Check ownership
            if context.resource_owner_id == context.user_id:
                return True
            
            return False
    
    async def _check_role_hierarchy_permission(
        self,
        context: AccessContext,
        permission: Permission,
        resource_id: Optional[int]
    ) -> bool:
        """
        Check permissions based on role hierarchy
        """
        from src.db.session import async_session_factory
        from sqlalchemy import select
        
        async with async_session_factory() as session:
            # Get user roles with hierarchy levels
            # Temporarily disabled RBAC system - fallback to simple permissions
            # query = select(Role).join(user_roles).where(
            #     user_roles.c.user_id == context.user_id
            # ).order_by(Role.level.desc())
            #             
            # result = await session.execute(query)
            # user_roles_result = result.scalars().all()
            #
            # # Check highest level roles first
            # for role in user_roles_result:
            return False  # Default deny for now
            #     role_permissions = await self._get_role_permissions(role.id)
            #     if permission in role_permissions:
            #         # Additional checks for sensitive permissions
            #         if self._is_sensitive_permission(permission):
            #             return await self._check_sensitive_permission(context, permission)
            #         return True
            # 
            # return False
    
    def _get_required_access_level(self, permission: Permission) -> AccessLevel:
        """
        Determine required access level for permission
        """
        if permission.value.endswith('.delete') or permission.value.startswith('admin.'):
            return AccessLevel.ADMIN
        elif permission.value.endswith('.update') or permission.value.endswith('.create'):
            return AccessLevel.WRITE
        else:
            return AccessLevel.READ
    
    def _access_level_sufficient(self, user_level: AccessLevel, required_level: AccessLevel) -> bool:
        """
        Check if user access level is sufficient
        """
        level_hierarchy = {
            AccessLevel.NONE: 0,
            AccessLevel.READ: 1,
            AccessLevel.WRITE: 2,
            AccessLevel.ADMIN: 3,
            AccessLevel.OWNER: 4
        }
        
        return level_hierarchy[user_level] >= level_hierarchy[required_level]
    
    def _is_sensitive_permission(self, permission: Permission) -> bool:
        """
        Check if permission requires additional security checks
        """
        sensitive_permissions = [
            Permission.USER_DELETE, Permission.ADMIN_SETTINGS, Permission.ADMIN_BACKUP,
            Permission.DATA_DELETE, Permission.DATA_ANONYMIZE, Permission.SYSTEM_CONFIGURE
        ]
        return permission in sensitive_permissions
    
    async def _check_sensitive_permission(self, context: AccessContext, permission: Permission) -> bool:
        """
        Additional checks for sensitive permissions (MFA, IP restrictions, etc.)
        """
        # Implement additional security checks
        # - Multi-factor authentication
        # - IP whitelist
        # - Time-based restrictions
        # - Approval workflows
        
        # For now, require super admin for most sensitive operations
        user_permissions = await self._get_user_permissions(context.user_id)
        return Permission.SYSTEM_CONFIGURE in user_permissions
    
    async def _get_role_permissions(self, role_id: int) -> Set[Permission]:
        """
        Get permissions for a specific role
        """
        cache_key = f"role_{role_id}"
        if cache_key in self._permission_cache:
            return self._permission_cache[cache_key]
        
        from src.db.session import async_session_factory
        from sqlalchemy import select
        
        permissions = set()
        
        async with async_session_factory() as session:
            query = select(PermissionModel).join(role_permissions).where(
                role_permissions.c.role_id == role_id
            )
            result = await session.execute(query)
            role_permissions_result = result.scalars().all()
            
            for perm in role_permissions_result:
                try:
                    permissions.add(Permission(perm.name))
                except ValueError:
                    continue
        
        self._permission_cache[cache_key] = permissions
        return permissions
    
    async def grant_permission(
        self,
        user_id: int,
        resource_type: ResourceType,
        resource_id: int,
        access_level: AccessLevel,
        granted_by: int
    ):
        """
        Grant resource-specific permission to user
        """
        from src.db.session import async_session_factory
        
        async with async_session_factory() as session:
            resource_perm = ResourcePermission(
                user_id=user_id,
                resource_type=resource_type.value,
                resource_id=resource_id,
                access_level=access_level.value,
                granted_by=granted_by
            )
            
            session.add(resource_perm)
            await session.commit()
            
            # Clear cache
            if user_id in self._role_cache:
                del self._role_cache[user_id]
    
    async def revoke_permission(
        self,
        user_id: int,
        resource_type: ResourceType,
        resource_id: int
    ):
        """
        Revoke resource-specific permission from user
        """
        from src.db.session import async_session_factory
        from sqlalchemy import delete, and_
        
        async with async_session_factory() as session:
            query = delete(ResourcePermission).where(
                and_(
                    ResourcePermission.user_id == user_id,
                    ResourcePermission.resource_type == resource_type.value,
                    ResourcePermission.resource_id == resource_id
                )
            )
            
            await session.execute(query)
            await session.commit()
            
            # Clear cache
            if user_id in self._role_cache:
                del self._role_cache[user_id]


# Global RBAC manager instance
rbac_manager = RBACManager()


# Decorator for endpoint protection
def require_permission(permission: Permission, resource_type: Optional[ResourceType] = None):
    """
    Decorator to protect endpoints with RBAC
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user and context from request
            # This would be integrated with FastAPI dependency injection
            context = AccessContext(user_id=1)  # Get from request
            
            has_permission = await rbac_manager.check_permission(context, permission)
            
            if not has_permission:
                from fastapi import HTTPException
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
