from typing import Any, Dict, Optional, Union, List
import secrets
import hashlib
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.base import ServiceBase


class UserService(ServiceBase[User, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(self.model).filter(self.model.email == email).first()

    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        return db.query(self.model).filter(self.model.username == username).first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        db_obj = self.model(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            full_name=obj_in.full_name,
            username=obj_in.username,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: User,
        obj_in: Union[UserUpdate, Dict[str, Any]]
    ) -> User:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def authenticate(
        self, db: Session, *, email: str, password: str
    ) -> Optional[User]:
        # Try to authenticate by email first
        user = self.get_by_email(db, email=email)
        if not user:
            # If not found by email, try by username
            user = self.get_by_username(db, username=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_active(self, user: User) -> bool:
        return user.is_active
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against its hash"""
        return verify_password(plain_password, hashed_password)
    
    def update_password(self, db: Session, *, user: User, new_password: str) -> User:
        """Update user password"""
        hashed_password = get_password_hash(new_password)
        user.hashed_password = hashed_password
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def generate_password_reset_token(self, db: Session, *, user: User) -> str:
        """Generate a secure password reset token"""
        # Generate a random token
        token = secrets.token_urlsafe(32)
        
        # Hash the token for storage (security best practice)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Set expiration time (1 hour from now)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Store the hashed token and expiration in user record
        user.reset_token_hash = token_hash
        user.reset_token_expires_at = expires_at
        db.add(user)
        db.commit()
        
        # Return the plain token (to be sent via email)
        return token

    def verify_password_reset_token(self, db: Session, *, token: str) -> Optional[User]:
        """Verify password reset token and return user if valid"""
        # Hash the provided token
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Find user with matching token hash
        user = db.query(self.model).filter(
            self.model.reset_token_hash == token_hash,
            self.model.reset_token_expires_at > datetime.utcnow()
        ).first()
        
        return user

    def reset_password_with_token(self, db: Session, *, token: str, new_password: str) -> Optional[User]:
        """Reset password using token"""
        user = self.verify_password_reset_token(db, token=token)
        if not user:
            return None
        
        # Update password
        self.update_password(db, user=user, new_password=new_password)
        
        # Clear reset token
        user.reset_token_hash = None
        user.reset_token_expires_at = None
        db.add(user)
        db.commit()
        
        return user


user_service = UserService(User) 