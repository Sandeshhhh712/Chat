from contextlib import asynccontextmanager
from contextvars import Token
from datetime import timedelta
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.util import unbound_method_to_callable
from app.dependencies.index import html
from .database.setup import get_db, create_db, dispose, SessionDependency
from .database.models import User
from .database.schemas import UserCreate, UserRead, Token
from fastapi import status
from .database.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    create_access_token,
    get_password_hash,
)
from fastapi.security import OAuth2PasswordRequestForm
from .database.auth import oauth2scheme


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server is starting...")
    await create_db()
    yield
    print("Server is closing...")
    await dispose()


app = FastAPI(lifespan=lifespan)


@app.post("/token")
async def login_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDependency,
) -> Token:
    username = form_data.username
    password = form_data.password
    user = await authenticate_user(session, username=username, password=password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Check credentials before trying again",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(
        data={"sub": user.username}, expire_delta=access_token_expires
    )
    return Token(access_token=access_token, type="bearer")


@app.post("/register", response_model=UserRead, status_code=201)
async def register_user(user: UserCreate, session: SessionDependency):
    query = select(User).where(User.username == user.username)
    result = await session.execute(query)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists"
        )

    hashed_password = get_password_hash(user.password)

    new_user = User(username=user.username, password=hashed_password)

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_broadcast_message(self, message: str):
        dead = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.active_connections.remove(connection)


manager = ConnectionManager()


@app.get("/")
async def homepage():
    return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await manager.send_broadcast_message(f"{websocket.client} has connected")

    sender_name = "Someone"
    try:
        while True:

            try:
                data = await websocket.receive_json()
            except ValueError:
                continue
            if not isinstance(data, dict):
                continue

            sender_name = data.get("name")
            message_text = data.get("message")
            broadcast = f"{sender_name} sent :{message_text}"
            await manager.send_broadcast_message(broadcast)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        await manager.send_broadcast_message(f"{sender_name} has disconnected")
