from contextlib import asynccontextmanager
from datetime import timedelta
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from app.dependencies.index import html
from .database.setup import create_db, dispose, SessionDependency
from .database.models import User
from .database.schemas import UserCreate, UserRead, Token
from fastapi import status
from .database.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    create_access_token,
    get_current_user,
    validate_user_ws,
    get_password_hash,
)
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm
import asyncio


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
    return Token(access_token=access_token, token_type="bearer")


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
        self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_broadcast_message(self, message: str):
        dead = []

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.active_connections.remove(connection)

    async def send_message_to_user(self, message: str, user: str):
        pass


# Login garne and pass that token so that it can be used for my custom websocket security logic

manager = ConnectionManager()


@app.get("/")
async def homepage():
    return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session: SessionDependency):
    await websocket.accept()

    try:
        auth_data = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
    except (asyncio.TimeoutError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    except WebSocketDisconnect:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    token = auth_data.get("token")
    current_user = await validate_user_ws(token, session)
    if current_user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    await manager.send_broadcast_message(f"{websocket.client} has connected")

    sender_name = current_user.username
    try:
        while True:
            try:
                data = await websocket.receive_json()
            except ValueError:
                continue
            if not isinstance(data, dict):
                continue
            message_text = data.get("message")
            broadcast = f"{sender_name} sent :{message_text}"
            await manager.send_broadcast_message(broadcast)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        await manager.send_broadcast_message(f"{sender_name} has disconnected")
