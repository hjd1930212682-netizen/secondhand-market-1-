# Author: 郝津德
"""用户收藏的添加、移除和列表接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import current_user
from app.database import get_db
from app.models import User
from app.schemas import FavoriteIn
from app.services import social


router = APIRouter(prefix="/api/favorites", tags=["收藏"])


@router.post("", status_code=201)
def add(payload: FavoriteIn, user: Annotated[User, Depends(current_user)],
        db: Annotated[Session, Depends(get_db)]) -> dict:
    """接收商品 ID，创建本人收藏。"""
    return social.add_favorite(db, user, payload.goods_id)


@router.delete("/{goods_id}")
def remove(goods_id: int, user: Annotated[User, Depends(current_user)],
           db: Annotated[Session, Depends(get_db)]) -> dict:
    """接收商品 ID，移除本人收藏。"""
    return social.remove_favorite(db, user, goods_id)


@router.get("")
def listing(user: Annotated[User, Depends(current_user)], db: Annotated[Session, Depends(get_db)],
            page: int = Query(1, ge=1), size: int = Query(12, ge=1, le=100)) -> dict:
    """接收分页条件，返回本人收藏列表。"""
    return social.list_favorites(db, user, page, size)

