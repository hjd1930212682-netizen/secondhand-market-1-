# Author: 郝津德
"""FastAPI 登录依赖，从 Bearer Token 获取当前用户。"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError
from app.core.security import read_token
from app.database import get_db
from app.models import User


BEARER = HTTPBearer(auto_error=False)


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(BEARER)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """从凭据和会话加载用户，返回 User；缺失或无效时返回 401。"""
    if credentials is None:
        raise BusinessError("请先登录", 401)
    user = db.get(User, read_token(credentials.credentials))
    if user is None:
        raise BusinessError("登录已失效，请重新登录", 401)
    return user

