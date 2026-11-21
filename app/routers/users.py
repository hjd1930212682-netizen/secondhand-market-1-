# Author: 王昱皓
"""本人资料、密码、用户主页和已发布商品路由。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import current_user
from app.database import get_db
from app.models import User
from app.schemas import PasswordIn, ProfileIn
from app.services import users


router = APIRouter(prefix="/api/users", tags=["用户"])


@router.put("/me")
def update_profile(payload: ProfileIn, user: Annotated[User, Depends(current_user)],
                   db: Annotated[Session, Depends(get_db)]) -> dict:
    """校验本人资料输入并返回更新后的资料。"""
    return users.update_profile(db, user, payload)


@router.put("/me/password")
def update_password(payload: PasswordIn, user: Annotated[User, Depends(current_user)],
                    db: Annotated[Session, Depends(get_db)]) -> dict:
    """校验密码输入并调用改密服务。"""
    return users.update_password(db, user, payload)


@router.get("/me/goods")
def my_goods(user: Annotated[User, Depends(current_user)], db: Annotated[Session, Depends(get_db)],
             page: int = Query(1, ge=1), size: int = Query(12, ge=1, le=100)) -> dict:
    """校验页码并查询本人商品。"""
    return users.my_goods(db, user, page, size)


@router.get("/{id}")
def public_profile(id: int, db: Annotated[Session, Depends(get_db)]) -> dict:
    """接收用户 ID，返回公开主页资料。"""
    return users.get_public_user(db, id)

