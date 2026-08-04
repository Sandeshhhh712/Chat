from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Mapping
import jwt
from fastapi import Depends, HTTPException, status
from pwdlib import PasswordHash
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.sql.functions import user

from .models import User
from .setup import SessionDependency

SECRET_KEY = "5b83430a468a304c17da69cd5835d250dd169a05847e0f86b630bd567091aa8c"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_hash = PasswordHash.recommended()


def get_password_hash(password):
    return pwd_hash.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_hash.verify(plain_password, hashed_password)


oauth2scheme = OAuth2PasswordBearer(tokenUrl="token")

# Login Auth


def get_user(session: SessionDependency, username: str) -> User | None:
    user = select(User).where(User.username == username)
    return session.scalar(user)


def authenticate_user(
    session: SessionDependency, username: str, password: str
) -> User | None:
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Check credentials before trying again",
    )
    user = get_user(session, username)
    if user is None:
        raise credential_exception
    if not verify_password(password, user.password):
        raise credential_exception
    return user


def create_access_token(data: Mapping[str, Any], expire_delta: timedelta | None = None):
    payload = data.get("sub")
    if "sub" not in data:
        raise ValueError("Invalid Payload")

    expire = datetime.now(timezone.utc) + (
        expire_delta if expire_delta is not None else timedelta(minutes=15)
    )

    payload = dict(data)
    payload["exp"] = int(expire.timestamp())

    return jwt.encode(payload, SECRET_KEY, ALGORITHM)


def get_current_user(
    token: Annotated[str, Depends(oauth2scheme)], session: SessionDependency
) -> User | None:
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Check credentials before trying again",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, ALGORITHM)
        username = payload.get("sub")
        if username is None:
            raise credential_exception
    except jwt.InvalidTokenError:
        raise credential_exception
    user = get_user(session, username)
    if not user:
        raise credential_exception
    return user
