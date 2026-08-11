from sqlalchemy import select
from app.database.models import Chatroom
from app.database.setup import SessionDependency


async def get_chatroom(session: SessionDependency, chatroom: str) -> Chatroom | None:
    room = select(Chatroom).where(Chatroom.name == chatroom)
    return await session.scalar(room)
