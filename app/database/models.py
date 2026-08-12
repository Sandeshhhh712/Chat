from sqlalchemy import ForeignKey, func, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from .setup import Base
from typing import List


class User(Base):
    __tablename__ = "user_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True)
    password: Mapped[str] = mapped_column(String(255))

    message: Mapped[List["Message"]] = relationship(
        back_populates="user", cascade="all,delete-orphan"
    )
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chatroom_table.id"), index=True, nullable=True
    )
    chatroom: Mapped["Chatroom"] = relationship(back_populates="user")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Chatroom(Base):
    __tablename__ = "chatroom_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))

    user: Mapped[List["User"]] = relationship(
        back_populates="chatroom", cascade="all,delete-orphan"
    )
    chat_message: Mapped[List["Message"]] = relationship(
        back_populates="chatroom", cascade="all,delete-orphan"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Message(Base):
    __tablename__ = "message_table"

    id: Mapped[int] = mapped_column(primary_key=True)

    chat_id: Mapped[int] = mapped_column(ForeignKey("chatroom_table.id"), index=True)
    chatroom: Mapped["Chatroom"] = relationship(back_populates="chat_message")
    user_id: Mapped[int] = mapped_column(ForeignKey("user_table.id"), index=True)
    user: Mapped["User"] = relationship(back_populates="message")
    content: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
