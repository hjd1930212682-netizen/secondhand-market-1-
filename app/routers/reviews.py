# Author: 安远
"""交易评价及用户评分接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import current_user
from app.database import get_db
from app.models import User
from app.schemas import ReviewIn
from app.services import social


router = APIRouter(prefix="/api", tags=["评价"])


@router.post("/orders/{id}/review", status_code=201)
def review(id: int, payload: ReviewIn, user: Annotated[User, Depends(current_user)],
           db: Annotated[Session, Depends(get_db)]) -> dict:
    """接收订单 ID 与评价字段，返回已创建评价。"""
    return social.create_review(db, id, user, payload)


@router.get("/goods/{id}/reviews")
def goods_reviews(id: int, db: Annotated[Session, Depends(get_db)],
                  page: int = Query(1, ge=1), size: int = Query(12, ge=1, le=100)) -> dict:
    """接收商品 ID 和分页条件，返回评价列表。"""
    return social.goods_reviews(db, id, page, size)


@router.get("/users/{id}/rating")
def user_rating(id: int, db: Annotated[Session, Depends(get_db)]) -> dict:
    """接收用户 ID，返回平均星级和评价数。"""
    return social.user_rating(db, id)

