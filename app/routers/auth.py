# Author: 王昱皓
"""注册、登录与当前用户路由。"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import current_user
from app.database import get_db
from app.models import User
from app.schemas import LoginIn, RegisterIn
from app.services import users
from app.services.presenters import user_data


router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", status_code=201)
def register(payload: RegisterIn, db: Annotated[Session, Depends(get_db)]) -> dict:
    """接收注册字段并调用用户服务，返回新用户。"""
    return users.register(db, payload)


@router.post("/login")
def login(payload: LoginIn, db: Annotated[Session, Depends(get_db)]) -> dict:
    """接收账号密码并调用登录服务，返回令牌。"""
    return users.login(db, payload)


@router.get("/me")
def me(user: Annotated[User, Depends(current_user)]) -> dict:
    """接收已认证用户，返回本人资料。"""
    return user_data(user)

