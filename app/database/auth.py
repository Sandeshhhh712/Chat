from datetime import datetime, timedelta, timezone
from functools import partial
from typing import Annotated, Any, Mapping
import jwt
from fastapi import WebSocket
from fastapi import Depends, HTTPException, status
from jwt.algorithms import Algorithm
from pwdlib import PasswordHash
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
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


async def get_user(session: SessionDependency, username: str) -> User | None:
    user = select(User).where(User.username == username)
    return await session.scalar(user)


async def authenticate_user(
    session: SessionDependency, username: str, password: str
) -> User | None:
    user = await get_user(session, username)
    if user is None:
        return None
    if not verify_password(password, user.password):
        return None
    return user


async def create_access_token(
    data: Mapping[str, Any], expire_delta: timedelta | None = None
):
    if "sub" not in data:
        raise ValueError("Invalid Payload")

    expire = datetime.now(timezone.utc) + (
        expire_delta if expire_delta is not None else timedelta(minutes=15)
    )

    payload = dict(data)
    payload["exp"] = int(expire.timestamp())

    return jwt.encode(payload, SECRET_KEY, ALGORITHM)


async def get_current_user(
    token: Annotated[str, Depends(oauth2scheme)], session: SessionDependency
) -> User | None:
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Check credentials before trying again",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credential_exception
    except jwt.InvalidTokenError:
        raise credential_exception
    user = await get_user(session, username)
    if user is None:
        raise credential_exception
    return user


async def validate_user_ws(token: str, session: SessionDependency) -> User | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        print("JWT bigryo")
        return None
    username = payload.get("sub")
    if username is None:
        print("Not logged in")
        return None
    return await get_user(session, username=username)
