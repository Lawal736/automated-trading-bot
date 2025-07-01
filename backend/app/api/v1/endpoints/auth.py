from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api import deps
from app.core.security import create_access_token
from app.models import user as user_model
from app.schemas import auth as auth_schema
from app.services import user_service
from app.schemas import user as user_schema
from app.core import config
from app.services.email_service import email_service

router = APIRouter()


@router.post("/register", response_model=user_schema.User)
def register_new_user(
    user_in: auth_schema.UserCreate, db: Session = Depends(deps.get_db)
):
    """
    Create new user.
    """
    user = user_service.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    user = user_service.create(db=db, obj_in=user_in)
    return user


@router.post("/login", response_model=auth_schema.Token)
def login_for_access_token(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = user_service.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user_service.is_active(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    access_token_expires = timedelta(minutes=config.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=auth_schema.Token)
def refresh_token(
    current_user: user_model.User = Depends(deps.get_current_active_user)
) -> Any:
    """Refresh access token"""
    
    access_token_expires = timedelta(minutes=config.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=current_user.id, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
    }


@router.get("/me", response_model=user_schema.User)
def get_current_user_info(
    current_user: user_model.User = Depends(deps.get_current_active_user)
) -> Any:
    """Get current user information"""
    return current_user


@router.post("/logout")
def logout() -> Any:
    """Logout user (client should discard token)"""
    return {"message": "Successfully logged out"}


@router.post("/change-password")
def change_password(
    password_change: auth_schema.PasswordChange,
    db: Session = Depends(deps.get_db),
    current_user: user_model.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Change user password
    """
    # Verify current password
    if not user_service.verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Check if new password is different from current
    if user_service.verify_password(password_change.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    # Update password
    user_service.update_password(db, user=current_user, new_password=password_change.new_password)
    
    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
def forgot_password(
    request: auth_schema.ForgotPasswordRequest,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Send password reset email
    """
    # Find user by email
    user = user_service.get_by_email(db, email=request.email)
    
    # Always return success to prevent email enumeration attacks
    # But only send email if user exists
    if user and user_service.is_active(user):
        # Generate reset token
        reset_token = user_service.generate_password_reset_token(db, user=user)
        
        # Send email
        email_sent = email_service.send_password_reset_email(
            to_email=user.email,
            reset_token=reset_token,
            user_name=user.full_name or user.username
        )
        
        if not email_sent:
            # Log error but don't expose it to user
            pass
    
    return {"message": "If an account with that email exists, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password(
    request: auth_schema.ResetPasswordRequest,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Reset password using token
    """
    # Verify token and reset password
    user = user_service.reset_password_with_token(
        db, 
        token=request.token, 
        new_password=request.new_password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    return {"message": "Password reset successfully"} 