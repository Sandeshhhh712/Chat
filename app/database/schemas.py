from typing import List

from pydantic import BaseModel
from datetime import datetime


class UserCreate(BaseModel):
    username: str
    password: str


class UserRead(BaseModel):
    id: int
    username: str
    created_at: datetime
    updated_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str


class ChatroomCreate(BaseModel):
    name: str


class ChatroomRead(BaseModel):
    id: int
    name: str
    created_at: datetime
