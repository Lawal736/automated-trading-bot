from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from jose import jwt, JWTError
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import user as user_model
from app.services import user_service
from app.trading.trading_service import TradingService
from app.services.exchange_service import ExchangeService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token"
)

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

class TokenData(BaseModel):
    id: Optional[int] = None

def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> user_model.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        # The 'sub' claim in the token is the user's ID.
        user_id = int(payload.get("sub"))
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(id=user_id)
    except (JWTError, ValueError, TypeError):
        # Catch JWT errors, and ValueError/TypeError if 'sub' is not a valid int
        raise credentials_exception
    
    user = user_service.get(db, id=token_data.id)

    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(
    current_user: user_model.User = Depends(get_current_user),
) -> user_model.User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_trading_service() -> TradingService:
    return TradingService()


def get_exchange_service(session: Session = Depends(get_db)) -> ExchangeService:
    return ExchangeService(session=session)

# Re-export the authentication functions from security.py
__all__ = ["get_db", "get_current_user", "get_current_active_user", "get_trading_service", "get_exchange_service"] 