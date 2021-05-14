import os
from starlette import status
from sqlalchemy import select
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from app.db import get_db
from app.config import logger
from app.util.common import CommonResponse
from app.util.security import RequirePermission, RequiredPolicy
from models.user import (User, UserModel, RoleModel, PermissionModel,
                         PolicyModel, Role, Permission, Policy, UserCRUD, UserModelUpdate, RoleModelUpdate,
                         PermissionModelUpdate, PolicyModelUpdate)

router = APIRouter()

if os.getenv('PRODUCTION') == '0':
    DEV_FLAG = True
else:
    DEV_FLAG = False


@router.get("/user", include_in_schema=DEV_FLAG, response_model=List[UserModel])
def get_user(username: Optional[str] = None,
             db: Session = Depends(get_db),
             _: User = Depends(RequirePermission([RequiredPolicy(action='*', resource='*')]))):
    """Get a list of users or a specific user."""
    if username:
        users = UserCRUD.get_user(username=username, db=db)
    else:
        users = UserCRUD.get_users(db=db)
    return users


@router.post("/user", include_in_schema=DEV_FLAG, response_model=UserModel)
def add_user(user_data: UserModel,
             db: Session = Depends(get_db),
             _=Depends(RequirePermission([RequiredPolicy(action='*', resource='*')]))):
    """Add user to the system."""
    user = UserCRUD.create_user(db, user_data)
    return UserModel.from_orm(user)


@router.put("/user", include_in_schema=DEV_FLAG, response_model=UserModel)
def update_user(username: str,
                user_data: UserModelUpdate,
                db: Session = Depends(get_db),
                _=Depends(RequirePermission([RequiredPolicy(action='*', resource='*')]))):
    """Update user data."""
    user = UserCRUD.update_user(username, user_data, db)
    return user


@router.delete("/user", include_in_schema=DEV_FLAG, response_model=CommonResponse)
def delete_user(user_id: int,
                db: Session = Depends(get_db),
                _=Depends(RequirePermission([RequiredPolicy(action='*', resource='*')]))):
    """Delete user from the system."""
    statement = select(User).filter_by(id=user_id)
    user = db.execute(statement).scalar()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    if UserCRUD.delete_user(user, db):
        return CommonResponse(message="user deleted successfully.")


@router.get("/role", include_in_schema=DEV_FLAG, response_model=List[RoleModel])
def get_role(role_id: Optional[int] = None,
             db: Session = Depends(get_db),
             _=Depends(RequirePermission([RequiredPolicy(action='*', resource='*')]))):
    """Get a list of roles or a specific role."""
    if role_id:
        roles = UserCRUD.get_role(role_id=role_id, db=db)
    else:
        roles = UserCRUD.get_roles(db=db)
    return roles


@router.post("/role", include_in_schema=DEV_FLAG, response_model=RoleModel)
def add_role(role_data: RoleModel,
             db: Session = Depends(get_db),
             _=Depends(RequirePermission([RequiredPolicy(action='*', resource='*')]))):
    """Add a role to the system."""
    role = UserCRUD.create_role(db, role_data)
    return RoleModel.from_orm(role)


@router.put("/role", include_in_schema=DEV_FLAG, response_model=RoleModel)
def update_role(role_id: int,
                role_data: RoleModelUpdate,
                db: Session = Depends(get_db),
                _=Depends(RequirePermission([RequiredPolicy(action='*', resource='*')]))):
    """Update role data."""
    role = UserCRUD.update_role(role_id, role_data, db)
    return role


@router.delete("/role", include_in_schema=DEV_FLAG, response_model=CommonResponse)
def delete_role(role_id: int,
                db: Session = Depends(get_db),
                _=Depends(RequirePermission([RequiredPolicy(action='*', resource='*')]))):
    """Delete role from the system."""
    statement = select(Role).filter_by(id=role_id)
    role = db.execute(statement).scalar()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    if UserCRUD.delete_role(role, db):
        return CommonResponse(message="role deleted successfully.")


@router.get("/permission", include_in_schema=DEV_FLAG, response_model=List[PermissionModel])
def get_permission(permission_id: Optional[int] = None,
                   db: Session = Depends(get_db),
                   _=Depends(RequirePermission([RequiredPolicy(action='*', resource='*')]))):
    """Get a list of permissions or a specific permission."""
    if permission_id:
        permissions = UserCRUD.get_permission(permission_id=permission_id, db=db)
    else:
        permissions = UserCRUD.get_permissions(db=db)
    return permissions


@router.post("/permission", include_in_schema=DEV_FLAG, response_model=PermissionModel)
def add_permission(permission_data: PermissionModel,
                   db: Session = Depends(get_db),
                   _=Depends(RequirePermission([RequiredPolicy(action='*', resource='*')]))):
    """Add permission to the system."""
    permission = UserCRUD.create_permission(db, permission_data)
    return PermissionModel.from_orm(permission)


@router.put("/permission", include_in_schema=DEV_FLAG, response_model=PermissionModel)
def update_permission(permission_id: int,
                      permission_data: PermissionModelUpdate,
                      db: Session = Depends(get_db),
                      _=Depends(RequirePermission([RequiredPolicy(action='*', resource='*')]))):
    """Update permission data."""
    permission = UserCRUD.update_permission(permission_id, permission_data, db)
    return permission


@router.delete("/permission", include_in_schema=DEV_FLAG, response_model=CommonResponse)
def delete_permission(permission_id: int,
                      db: Session = Depends(get_db),
                      _=Depends(RequirePermission([RequiredPolicy(action='*', resource='*')]))):
    """Delete permission from the system."""
    statement = select(Permission).filter_by(id=permission_id)
    permission = db.execute(statement).scalar()
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    if UserCRUD.delete_role(permission, db):
        return CommonResponse(message="role deleted successfully.")


@router.get("/policy", include_in_schema=DEV_FLAG, response_model=List[PolicyModel])
def get_policy(name: Optional[str] = None,
               db: Session = Depends(get_db),
               _=Depends(RequirePermission([RequiredPolicy(action='*', resource='*')]))):
    """Get a list of policies or a specific policy."""
    if name:
        policies = UserCRUD.get_policy(name=name, db=db)
    else:
        policies = UserCRUD.get_policies(db=db)
    return policies


@router.post("/policy", include_in_schema=DEV_FLAG, response_model=PolicyModel)
def add_policy(policy_data: PolicyModel,
               db: Session = Depends(get_db),
               _=Depends(RequirePermission([RequiredPolicy(action='*', resource='*')]))):
    """Add policy to the system."""
    policy = UserCRUD.create_policy(db, policy_data)
    return PolicyModel.from_orm(policy)


@router.put("/policy", include_in_schema=DEV_FLAG, response_model=PolicyModel)
def update_policy(name: str,
                  policy_data: PolicyModelUpdate,
                  db: Session = Depends(get_db),
                  _=Depends(RequirePermission([RequiredPolicy(action='*', resource='*')]))):
    """Update policy data."""
    policy = UserCRUD.update_policy(name, policy_data, db)
    return policy


@router.delete("/policy", include_in_schema=DEV_FLAG, response_model=CommonResponse)
def delete_policy(name: str,
                  db: Session = Depends(get_db),
                  _=Depends(RequirePermission([RequiredPolicy(action='*', resource='*')]))):
    """Delete policy."""
    statement = select(Policy).filter_by(name=name)
    policy = db.execute(statement).scalar()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    if UserCRUD.delete_role(policy, db):
        return CommonResponse(message="role deleted successfully.")
