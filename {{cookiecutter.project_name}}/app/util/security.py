"""
Copyright (C) Pratik Shivarkar - All Rights Reserved

This source code is protected under international copyright law.  All rights
reserved and protected by the copyright holders.
This file is confidential and only available to authorized individuals with the
permission of the copyright holders.  If you encounter this file and do not have
permission, please contact the copyright holders and delete this file.
"""


import os
import random
import string
from pydantic import BaseModel
from jose import JWTError, jwt
from typing import Optional, Union, List
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status, Header

from app.db import get_db
from app.config import logger
from models.user import User, OTP

AUTH_MODE = os.getenv('AUTH_MODE')
SECRET_KEY = os.getenv('SECRET_KEY')
REFRESH_KEY = os.getenv('REFRESH_KEY')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class Username(BaseModel):
    username: str


class Email(BaseModel):
    email: str


class UserID(BaseModel):
    id: Union[Username, Email]


class UserInfo(UserID):
    password: str


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_user(user_data: UserID, db: Session) -> User:
    if type(user_data.id).__name__ == 'Username':
        statement = select(User).filter_by(username=user_data.id.username)
    else:
        statement = select(User).filter_by(email=user_data.id.email)
    user = db.execute(statement).scalar()
    if not user:
        raise HTTPException(status_code=404, detail="cannot find user")
    return user


def authenticate_user(user: User, password: str) -> bool:
    return user.verify_password(password)


def generate_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def generate_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, REFRESH_KEY, algorithm=ALGORITHM)
    return encoded_jwt


if AUTH_MODE == 'api-gateway':
    class GetCurrentUser:
        def __init__(self, refresh=False):
            self.refresh = refresh

        def __call__(self, x_consumer_id: str = Header(...), db: Session = Depends(get_db)):
            credentials_exception = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="do not have authenticated user",
            )
            username = x_consumer_id
            if username is None:
                raise credentials_exception

            user_id = UserID(id=Username(username=username))
            user = get_user(user_id, db)
            if user is None:
                raise credentials_exception
            if user.disabled:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not activated")
            return user
else:
    class GetCurrentUser:
        def __init__(self, refresh=False):
            self.refresh = refresh

        def __call__(self, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
            credentials_exception = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            try:
                # TODO: Implement one time refresh tokens with Redis, use JWT to validate expiry of the token
                if not self.refresh:
                    ENCRYPTION_KEY = SECRET_KEY
                else:
                    ENCRYPTION_KEY = REFRESH_KEY
                payload = jwt.decode(token, ENCRYPTION_KEY, algorithms=[ALGORITHM])
                username: str = payload.get("sub")
                if username is None:
                    raise credentials_exception
                TokenData(username=username)
            except JWTError:
                raise credentials_exception
            user_id = UserID(id=Username(username=username))
            user = get_user(user_id, db)
            if user is None:
                raise credentials_exception
            if user.disabled:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not activated")
            return user


def get_current_active_user(current_user: User = Depends(GetCurrentUser())):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="inactive user")
    return current_user


def get_user_by_refresh_token(current_user: User = Depends(GetCurrentUser(refresh=True))):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="inactive user")
    return current_user


class RequiredPolicy(BaseModel):
    action: str
    resource: str


class RequirePermission:
    def __init__(self, permissions: List[RequiredPolicy]):
        self.permissions = permissions

    def __call__(self, user: User = Depends(get_current_active_user)):
        for permission in self.permissions:
            allowed_actions_for_resource = [policy.permission.action
                                            for policy in user.role.policies
                                            if policy.permission.resource.name == permission.resource]
            if permission.action not in allowed_actions_for_resource:
                logger.debug(
                    f"user with role {user.role} not allowed to perform {permission.action} on {permission.resource}"
                )
                raise HTTPException(status_code=403, detail="operation not permitted")
        return user


def generate_otp(user_id: UserID, action: str, db: Session) -> OTP:
    if type(user_id.id).__name__ == 'Username':
        statement = select(User).filter_by(username=user_id.id.username)
    else:
        statement = select(User).filter_by(email=user_id.id.email)
    user = db.execute(statement).scalar()
    retry_count = 0
    while True:
        try:
            password_characters = string.ascii_letters + string.digits
            auth_code = ''.join(random.choice(password_characters) for _ in range(8))
            revoke_code = ''.join(random.choice(password_characters) for _ in range(8))
            valid_till = datetime.utcnow() + timedelta(hours=24)
            otp = OTP(
                authorization_code=auth_code,
                revoke_code=revoke_code,
                action=action,
                valid_till=valid_till,
                user_id=user.id
            )
            db.add(otp)
            db.commit()
            db.refresh(otp)
        except IntegrityError:
            retry_count += 1
            if retry_count >= 5:
                break
        else:
            return otp
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="operation could not complete. try again.")


def delete_otp(revoke_code: str, db: Session):
    try:
        statement = select(OTP).filter_by(revoke_code=revoke_code)
        otp = db.execute(statement).scalar()
        db.delete(otp)
        db.commit()
    except IntegrityError as e:
        logger.debug(e)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="code not found.")
    except Exception as e:
        logger.debug(e, e.__class__.__name__)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="code not found.")


def get_user_by_otp(authorization_code: str, action: str, db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="could not validate credentials",
    )

    statement = select(OTP).filter_by(authorization_code=authorization_code)
    otp = db.execute(statement).scalar()
    if otp is None:
        raise credentials_exception
    if otp.action != action:
        raise credentials_exception
    user = otp.user
    db.delete(otp)
    db.commit()
    return user
