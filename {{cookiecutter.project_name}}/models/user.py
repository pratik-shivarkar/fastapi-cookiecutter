"""
Copyright (C) Pratik Shivarkar - All Rights Reserved

This source code is protected under international copyright law.  All rights
reserved and protected by the copyright holders.
This file is confidential and only available to authorized individuals with the
permission of the copyright holders.  If you encounter this file and do not have
permission, please contact the copyright holders and delete this file.
"""


from starlette import status
from pydantic import BaseModel
from sqlalchemy.sql import func
from fastapi import HTTPException
from typing import Union, Optional, List
from passlib.context import CryptContext
from datetime import datetime, timedelta, date
from sqlalchemy.dialects.postgresql import JSON, INET
from sqlalchemy.orm import declarative_base, relationship, Session
from sqlalchemy.exc import DataError, OperationalError, IntegrityError
from sqlalchemy import (Column, Integer, String, ForeignKey, Boolean, DateTime, Text,
                        Date, select, update)


from app.config import logger

pwd_context = CryptContext(
    # Replace this list with the hash(es) you wish to support.
    # this example sets pbkdf2_sha256 as the default,
    # with additional support for reading legacy bcrypt hashes.
    schemes=["pbkdf2_sha512", "pbkdf2_sha256", "bcrypt"],

    # Automatically mark all but first hasher in list as deprecated.
    # (this will be the default in Passlib 2.0)
    deprecated="auto",
    )

Base = declarative_base()


class Policy(Base):
    __tablename__ = 'policy'
    name = Column(String(32), unique=True)
    permission_id = Column(Integer, ForeignKey('permission.id'), primary_key=True)
    role_id = Column(Integer, ForeignKey('role.id'), primary_key=True)
    permission = relationship('Permission', back_populates='policies')
    role = relationship('Role', back_populates='policies')


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    first_name = Column(String(32), index=True)
    last_name = Column(String(32), index=True)
    username = Column(String(64), index=True, unique=True)
    phone_number = Column(String(16), index=True, unique=True)
    email = Column(String(120), index=True, unique=True)
    secondary_email = Column(String(120), nullable=True)
    company_name = Column(String(128), nullable=True)
    password_hash = Column(String(130))
    country = Column(String(3), nullable=True)
    role_id = Column('role_id', Integer, ForeignKey('role.id'))
    role = relationship('Role', back_populates='users')
    disabled = Column(Boolean, default=False)
    joined = Column(DateTime, server_default=func.now())
    dob = Column(Date, nullable=True)
    address = Column(JSON, nullable=True)
    login_history = relationship('Login', back_populates='user')

    def set_password(self, password):
        self.password_hash = pwd_context.hash(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    def __repr__(self):
        return f"User (id={self.id!r}, name={self.first_name} {self.last_name})"


class Login(Base):
    __tablename__ = 'login'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, server_default=func.now())
    ip_address = Column(INET)
    failed = Column(Boolean, default=False)
    user_agent = Column(Text)
    user_id = Column('user_id', Integer, ForeignKey('user.id'))
    user = relationship('User', back_populates='login_history')


class OTP(Base):
    __tablename__ = 'otp'

    authorization_code = Column(String(8), unique=True, index=True, primary_key=True)
    revoke_code = Column(String(8), unique=True, index=True, primary_key=True)
    action = Column(String(32))
    valid_till = Column(DateTime, default=datetime.utcnow() + timedelta(hours=24))
    user_id = Column('user_id', Integer, ForeignKey('user.id'))
    user = relationship('User')


class Role(Base):
    __tablename__ = 'role'

    id = Column(Integer, primary_key=True)
    title = Column(String(32))
    users = relationship('User', back_populates='role')
    policies = relationship('Policy', back_populates='role')

    def __repr__(self):
        return f"Role (id={self.id!r}, name={self.title!r})"


class Permission(Base):
    __tablename__ = 'permission'

    id = Column(Integer, primary_key=True)
    action = Column(String(32))
    resource_id = Column('resource_id', Integer, ForeignKey('resource.id'))
    resource = relationship('Resource', back_populates='permissions')
    policies = relationship('Policy', back_populates='permission')

    def __repr__(self):
        return f"Permission (id={self.id!r}, action={self.action!r}, resource={self.resource.name!r})"


class Resource(Base):
    __tablename__ = 'resource'

    id = Column(Integer, primary_key=True)
    name = Column(String(32))
    permissions = relationship('Permission', back_populates='resource')

    def __repr__(self):
        return f"Resource (id={self.id!r}, name={self.name!r})"


# -- Schemas --

class UserModel(BaseModel):
    username: Optional[str]
    email: Optional[str]
    company_name: Union[str, None]
    country: Union[str, None]
    first_name: Optional[str]
    last_name: Optional[str]
    phone_number: Optional[str]
    secondary_email: Union[str, None]
    disabled: bool
    joined: Optional[datetime]
    dob: Optional[date]
    address: Optional[str]

    class Config:
        orm_mode = True


class PolicyModel(BaseModel):
    name: Optional[str]
    permission_id: Optional[int]
    role_id: Optional[int]

    class Config:
        orm_mode = True


class RoleModel(BaseModel):
    id: Optional[int]
    title: Optional[str]

    class Config:
        orm_mode = True


class PermissionModel(BaseModel):
    id: Optional[int]
    action: Optional[str]
    resource_id: Optional[int]

    class Config:
        orm_mode = True


class ResourceModel(BaseModel):
    id: Optional[int]
    name: Optional[str]

    class Config:
        orm_mode = True


class LoginModel(BaseModel):
    user_agent: str
    ip_address: str
    timestamp: datetime

    class Config:
        orm_mode = True


class LoginHistoryModel(BaseModel):
    history: List[LoginModel]


# Update Schemas


class UserModelUpdate(BaseModel):
    company_name: Optional[str]
    country: Optional[str]
    first_name: str
    last_name: str
    phone_number: str
    dob: Optional[date]
    address: Optional[str]


class RoleModelUpdate(BaseModel):
    title: Optional[str]


class PermissionModelUpdate(BaseModel):
    action: Optional[str]
    resource_id: Optional[int]


class PolicyModelUpdate(BaseModel):
    name: Optional[str]
    permission_id: Optional[int]
    role_id: Optional[int]


# -- CRUD Functions
# User, Role, Permission, Policy

class UserCRUD:

    @staticmethod
    def create_user(db: Session, user_data: UserModel) -> User:
        try:
            user = User(**user_data.dict())
            db.add(user)
            db.commit()
            db.refresh(user)
        except (DataError, OperationalError, IntegrityError) as e:
            logger.error(e)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid data")
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="unknown error")
        else:
            return user

    @staticmethod
    def create_role(db: Session, role_data: RoleModel) -> Role:
        try:
            role = Role(**role_data.dict())
            db.add(role)
            db.commit()
            db.refresh(role)
        except (DataError, OperationalError, IntegrityError) as e:
            logger.error(e)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid data")
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="unknown error")
        else:
            return role

    @staticmethod
    def create_permission(db: Session, permission_data: PermissionModel) -> Permission:
        try:
            permission = Permission(**permission_data.dict())
            db.add(permission)
            db.commit()
            db.refresh(permission)
        except (DataError, OperationalError, IntegrityError) as e:
            logger.error(e)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid data")
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="unknown error")
        else:
            return permission

    @staticmethod
    def create_policy(db: Session, policy_data: PolicyModel) -> Policy:
        try:
            policy = Policy(**policy_data.dict())
            db.add(policy)
            db.commit()
            db.refresh(policy)
        except (DataError, OperationalError, IntegrityError) as e:
            logger.error(e)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid data")
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="unknown error")
        else:
            return policy

    @staticmethod
    def get_users(db: Session) -> List[UserModel]:
        statement = select(User)
        users = db.execute(statement).fetchall()
        return [UserModel.from_orm(user[0]) for user in users]

    @staticmethod
    def get_user(username: str, db: Session) -> List[UserModel]:
        statement = select(User).filter_by(username=username)
        user = db.execute(statement).scalar()
        return [UserModel.from_orm(user)]

    @staticmethod
    def get_roles(db: Session) -> List[RoleModel]:
        statement = select(Role)
        roles = db.execute(statement).fetchall()
        return [RoleModel.from_orm(role[0]) for role in roles]

    @staticmethod
    def get_role(role_id: int, db: Session) -> List[RoleModel]:
        statement = select(Role).filter_by(id=role_id)
        role = db.execute(statement).scalar()
        return [RoleModel.from_orm(role)]

    @staticmethod
    def get_permissions(db: Session) -> List[PermissionModel]:
        statement = select(Permission)
        permissions = db.execute(statement).fetchall()
        return [PermissionModel.from_orm(permission[0] for permission in permissions)]

    @staticmethod
    def get_permission(permission_id: int, db: Session) -> List[PermissionModel]:
        statement = select(Permission).filter_by(id=permission_id)
        permission = db.execute(statement).scalar()
        return [PermissionModel.from_orm(permission)]

    @staticmethod
    def get_policies(db: Session) -> List[PolicyModel]:
        statement = select(Policy)
        policies = db.execute(statement).fetchall()
        return [PolicyModel.from_orm(policy[0] for policy in policies)]

    @staticmethod
    def get_policy(name: str, db: Session) -> List[PolicyModel]:
        statement = select(Policy).filter_by(name=name)
        policy = db.execute(statement).scalar()
        return [PolicyModel.from_orm(policy)]

    @staticmethod
    def update_user(username: str, user_data: UserModelUpdate, db: Session):
        statement = update(User).where(User.username == username).values(**user_data.dict())
        try:
            db.execute(statement)
            db.commit()
            user = db.execute(select(User).where(User.username == username)).scalar()
        except Exception as e:
            logger.debug(e)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="unknown error.")
        else:
            return user

    @staticmethod
    def update_role(role_id: int, role_data: RoleModelUpdate, db: Session):
        statement = update(Role).where(Role.id == role_id).values(**role_data.dict())
        try:
            db.execute(statement)
            db.commit()
            role = db.execute(select(Role).where(Role.id == role_id)).scalar()
        except Exception as e:
            logger.debug(e)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="unknown error.")
        else:
            return role

    @staticmethod
    def update_permission(permission_id: int, permission_data: PermissionModelUpdate, db: Session):
        statement = update(Permission).where(Permission.id == permission_id).values(**permission_data.dict())
        try:
            db.execute(statement)
            db.commit()
            permission = db.execute(select(Permission).where(Permission.id == permission_id)).scalar()
        except Exception as e:
            logger.debug(e)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="unknown error.")
        else:
            return permission

    @staticmethod
    def update_policy(name: str, policy_data: PolicyModelUpdate, db: Session):
        statement = update(Policy).where(Policy.name == name).values(**policy_data.dict())
        try:
            db.execute(statement)
            db.commit()
            policy = db.execute(select(Policy).where(Policy.name == name)).scalar()
        except Exception as e:
            logger.debug(e)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="unknown error.")
        else:
            return policy

    @staticmethod
    def delete_user(user: User, db: Session) -> bool:
        try:
            db.delete(user)
            db.commit()
        except Exception as e:
            logger.debug(e)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
        else:
            return True

    @staticmethod
    def delete_role(role: Role, db: Session) -> bool:
        try:
            db.delete(role)
            db.commit()
        except Exception as e:
            logger.debug(e)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
        else:
            return True

    @staticmethod
    def delete_permission(permission: Permission, db: Session) -> bool:
        try:
            db.delete(permission)
            db.commit()
        except Exception as e:
            logger.debug(e)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
        else:
            return True

    @staticmethod
    def delete_policy(policy: Policy, db: Session) -> bool:
        try:
            db.delete(policy)
            db.commit()
        except Exception as e:
            logger.debug(e)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
        else:
            return True
