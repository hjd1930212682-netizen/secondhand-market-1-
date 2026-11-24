# Author: 郝津德
"""消息发送、会话、已读和未读数接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import current_user
from app.database import get_db
from app.models import User
from app.schemas import MessageIn, ReadMessagesIn
from app.services import social


router = APIRouter(prefix="/api/messages", tags=["消息"])


@router.post("", status_code=201)
def send(payload: MessageIn, user: Annotated[User, Depends(current_user)],
         db: Annotated[Session, Depends(get_db)]) -> dict:
    """接收消息字段并发送站内信。"""
    return social.send_message(db, user, payload)


@router.get("")
def listing(user: Annotated[User, Depends(current_user)], db: Annotated[Session, Depends(get_db)],
            peer_id: int | None = None, page: int = Query(1, ge=1),
            size: int = Query(50, ge=1, le=100)) -> dict:
    """接收联系人和分页条件，返回本人消息。"""
    return social.list_messages(db, user, peer_id, page, size)


@router.put("/read")
def read(payload: ReadMessagesIn, user: Annotated[User, Depends(current_user)],
         db: Annotated[Session, Depends(get_db)]) -> dict:
    """接收联系人 ID，把对方发来的消息标为已读。"""
    return social.mark_read(db, user, payload.peer_id)


@router.get("/unread-count")
def unread_count(user: Annotated[User, Depends(current_user)],
                 db: Annotated[Session, Depends(get_db)]) -> dict:
    """返回当前用户的未读消息数量。"""
    return social.unread_count(db, user)
