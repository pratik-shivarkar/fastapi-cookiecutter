"""
Copyright (C) Pratik Shivarkar - All Rights Reserved

This source code is protected under international copyright law.  All rights
reserved and protected by the copyright holders.
This file is confidential and only available to authorized individuals with the
permission of the copyright holders.  If you encounter this file and do not have
permission, please contact the copyright holders and delete this file.
"""


import os
from sqlalchemy.orm import Session
from pydantic.main import BaseModel
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import APIRouter, Depends, HTTPException, status, Request

from app.db import get_db
from app.config import logger
from models.user import User, UserModel, Login, LoginHistoryModel, LoginModel

from app.util.mail import Mail, send_mail
from app.util.common import CommonResponse
from app.util.security import UserID, Email, Username, get_user, Token, authenticate_user, \
    generate_access_token, get_current_active_user, RequirePermission, RequiredPolicy, get_user_by_otp, generate_otp, \
    delete_otp, generate_refresh_token, get_user_by_refresh_token


router = APIRouter()

AUTH_MODE = os.getenv('AUTH_MODE')


# --Requests--

class OTPRequest(BaseModel):
    authorization_code: str


class PasswordChangeRequest(OTPRequest):
    password: str
    confirm_password: str
    new_password: str
    confirm_new_password: str


# --Routes--


@router.get("/", response_model=UserModel, summary="Fetch Active User")
async def auth(current_user: User = Depends(get_current_active_user)):
    """
    Fetch currently active user
    """
    return UserModel.from_orm(current_user)


@router.get("/privileged", summary="Privilege Check")
def privileged(current_user=Depends(RequirePermission([RequiredPolicy(action='*', resource='*')]))):
    """
    Check if currently logged in user has admin permissions
    """
    message = f"admin access check passed for user {current_user.username}."
    return {'message': message}


if not AUTH_MODE or AUTH_MODE == 'native':
    @router.get("/reset-password", response_model=CommonResponse, summary="Request Password Reset")
    async def request_password_reset(email: str, db: Session = Depends(get_db)):
        """
        Request password reset code, received by user on their primary email
        """
        user_id = UserID(id=Email(email=email))
        otp = generate_otp(user_id=user_id, action='password_change', db=db)
        body_text = f"""You have requested password change for {{cookiecutter.project_name}}.\n
                     Request Code: {otp.authorization_code}\n
                     Revoke Code: {otp.revoke_code}"""
        body_html = f"""
        <html>
            <body>
                <p>You have requested password change for {{cookiecutter.project_name}}.</p>
                <p>Request Code: {otp.authorization_code}<br/>
                <br/>Revoke Code: {otp.revoke_code}</p>
            </body>
        </html>"""
        mail = Mail(
            recipient_email=otp.user.email,
            subject="Squire password reset request.",
            body_text=body_text,
            body_html=body_html
        )
        try:
            send_mail(mail)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="cannot send otp to email"
            )
        return CommonResponse(message='password change token sent to primary email successfully.')


    @router.post("/reset-password", response_model=CommonResponse, summary="Reset Password")
    async def reset_password(otp_password_change: PasswordChangeRequest, db: Session = Depends(get_db)):
        """
        Change password using old password and authorization code
        """
        user = get_user_by_otp(authorization_code=otp_password_change.authorization_code, action='password_change',
                               db=db)
        if not user.verify_password(otp_password_change.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="incorrect password"
            )
        user.set_password(otp_password_change.new_password)
        db.commit()
        return CommonResponse(message='password changed successfully.')


    @router.get("/revoke-authorization", response_model=CommonResponse, summary="Revoke OTP")
    async def revoke_authorization(revoke_code: str, db: Session = Depends(get_db)):
        """
        Revoke single action OTP code
        """
        delete_otp(revoke_code, db)
        return CommonResponse(message="authorization code revoked.")


    @router.post("/token/", response_model=Token, summary="Login / Get JWT Access Token")
    async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
        """
        Login using Username & Password to get JWT access token
        """
        user = get_user(user_data=UserID(id=Username(username=form_data.username)), db=db)
        login_attempt = Login(ip_address=request.client.host,
                              user_agent=request.headers.get('User-Agent'),
                              user_id=user.id)

        if not authenticate_user(user, form_data.password):
            login_attempt.failed = True
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        db.add(login_attempt)
        db.commit()
        access_token = generate_access_token(data={"sub": user.username})
        refresh_token = generate_refresh_token(data={"sub": user.username})
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


    @router.get("/token/refresh", response_model=Token, summary="Refresh Auth Token")
    async def auth(current_user: User = Depends(get_user_by_refresh_token)):
        """
        Refresh access token using refresh token as Bearer
        """
        access_token = generate_access_token(data={"sub": current_user.username})
        refresh_token = generate_refresh_token(data={"sub": current_user.username})
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


    @router.get("/history", response_model=LoginHistoryModel, summary="Get previous login attempts history")
    async def login_history(current_user: User = Depends(get_current_active_user)):
        """
        Get login history for the authenticated user
        """
        login_attempts = current_user.login_history
        response = LoginHistoryModel([LoginModel.from_orm(login_attempt) for login_attempt in login_attempts])
        return response
