# Author: 郝津德
"""下单、订单状态、列表及详情路由。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import current_user
from app.database import get_db
from app.models import User
from app.schemas import OrderIn, OrderStatusIn
from app.services import orders


router = APIRouter(prefix="/api/orders", tags=["订单"])


@router.post("", status_code=201)
def create(payload: OrderIn, user: Annotated[User, Depends(current_user)],
           db: Annotated[Session, Depends(get_db)]) -> dict:
    """接收商品 ID 并在事务中创建订单。"""
    return orders.create_order(db, payload.goods_id, user)


@router.get("")
def list_orders(user: Annotated[User, Depends(current_user)], db: Annotated[Session, Depends(get_db)],
                role: str = "buyer", status: str | None = None,
                page: int = Query(1, ge=1), size: int = Query(12, ge=1, le=100)) -> dict:
    """接收角色、状态和页码，返回本人订单。"""
    return orders.list_orders(db, user, role, status, page, size)


@router.put("/{id}/status")
def change_status(id: int, payload: OrderStatusIn, user: Annotated[User, Depends(current_user)],
                  db: Annotated[Session, Depends(get_db)]) -> dict:
    """接收订单 ID 和目标状态，返回流转结果。"""
    return orders.change_order_status(db, id, user, payload.to_status)


@router.get("/{id}")
def detail(id: int, user: Annotated[User, Depends(current_user)],
           db: Annotated[Session, Depends(get_db)]) -> dict:
    """接收订单 ID，返回本人订单详情。"""
    return orders.order_data(db, orders.get_order(db, id, user.id), user.id)

