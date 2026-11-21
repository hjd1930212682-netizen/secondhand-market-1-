# Author: 王昱皓
"""注册登录、资料修改、密码管理和用户商品查询。"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFound
from app.core.security import create_token, hash_password, verify_password
from app.models import Goods, User
from app.schemas import LoginIn, PasswordIn, ProfileIn, RegisterIn
from app.services.presenters import goods_data, page_result, user_data


def register(db: Session, payload: RegisterIn) -> dict:
    """创建用户；接收会话和注册资料，返回公开用户信息。"""
    if db.scalar(select(User.id).where(User.username == payload.username)):
        raise BusinessError("用户名已被注册", 409)
    user = User(username=payload.username, nickname=payload.nickname.strip(),
                password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise BusinessError("用户名已被注册", 409) from exc
    db.refresh(user)
    return user_data(user)


def login(db: Session, payload: LoginIn) -> dict:
    """验证账号密码；接收会话和凭据，返回 JWT 与用户资料。"""
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise BusinessError("用户名或密码错误", 401)
    return {"access_token": create_token(user.id), "token_type": "bearer", "user": user_data(user)}


def get_public_user(db: Session, user_id: int) -> dict:
    """读取用户主页；接收会话和 ID，返回公开资料。"""
    user = db.get(User, user_id)
    if user is None:
        raise NotFound("用户不存在")
    return user_data(user, public=True)


def update_profile(db: Session, user: User, payload: ProfileIn) -> dict:
    """更新昵称、电话和头像；返回更新后的本人资料。"""
    user.nickname = payload.nickname.strip()
    user.phone = payload.phone
    user.avatar = payload.avatar
    db.commit()
    db.refresh(user)
    return user_data(user)


def update_password(db: Session, user: User, payload: PasswordIn) -> dict:
    """核验旧密码后替换哈希；返回成功提示。"""
    if not verify_password(payload.old_password, user.password_hash):
        raise BusinessError("原密码错误")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "密码修改成功"}


def my_goods(db: Session, user: User, page: int, size: int) -> dict:
    """按页查询本人商品；返回统一列表结构。"""
    from sqlalchemy import func
    total = db.scalar(select(func.count()).select_from(Goods).where(Goods.seller_id == user.id)) or 0
    rows = db.scalars(select(Goods).where(Goods.seller_id == user.id)
                      .order_by(Goods.created_at.desc(), Goods.id.desc())
                      .offset((page - 1) * size).limit(size)).all()
    return page_result([goods_data(row) for row in rows], total, page, size)

