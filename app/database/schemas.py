from pydantic import BaseModel
from datetime import datetime


class UserCreate(BaseModel):
    name: str
    password: str


class UserRead(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime


class Token(BaseModel):
    token: str
    type: str


class Tokendata(BaseModel):
    sub: str
