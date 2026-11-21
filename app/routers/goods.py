# Author: 杨云凇
"""商品增改查、状态、软删除及分类路由。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import current_user
from app.database import get_db
from app.models import User
from app.schemas import GoodsIn, GoodsStatusIn
from app.services import goods


router = APIRouter(prefix="/api", tags=["商品与分类"])


@router.get("/categories")
def categories(db: Annotated[Session, Depends(get_db)]) -> dict:
    """返回分类列表。"""
    return goods.categories(db)


@router.post("/goods", status_code=201)
def create(payload: GoodsIn, user: Annotated[User, Depends(current_user)],
           db: Annotated[Session, Depends(get_db)]) -> dict:
    """校验发布输入并返回新商品。"""
    return goods.create_goods(db, user, payload)


@router.get("/goods")
def list_goods(db: Annotated[Session, Depends(get_db)], keyword: str = "",
               category_id: int | None = None, sort: str = "newest",
               page: int = Query(1, ge=1), size: int = Query(12, ge=1, le=100)) -> dict:
    """接收搜索、分类、排序和分页条件并返回商品列表。"""
    return goods.search(db, keyword, category_id, sort, page, size)


@router.put("/goods/{id}")
def update(id: int, payload: GoodsIn, user: Annotated[User, Depends(current_user)],
           db: Annotated[Session, Depends(get_db)]) -> dict:
    """接收商品 ID 和更新字段，返回本人商品。"""
    return goods.update_goods(db, id, user, payload)


@router.put("/goods/{id}/status")
def status(id: int, payload: GoodsStatusIn, user: Annotated[User, Depends(current_user)],
           db: Annotated[Session, Depends(get_db)]) -> dict:
    """接收商品 ID 和上下架状态，返回更新结果。"""
    return goods.change_status(db, id, user, payload.status)


@router.delete("/goods/{id}")
def delete(id: int, user: Annotated[User, Depends(current_user)],
           db: Annotated[Session, Depends(get_db)]) -> dict:
    """接收商品 ID 并软删除本人商品。"""
    return goods.delete_goods(db, id, user)


@router.get("/goods/{id}")
def detail(id: int, db: Annotated[Session, Depends(get_db)]) -> dict:
    """接收商品 ID，返回详情并计一次浏览。"""
    return goods.detail(db, id)

