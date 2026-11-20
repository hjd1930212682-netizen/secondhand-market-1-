# Author: 郝津德
"""bcrypt 密码验证与 JWT 签发。"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.core.exceptions import BusinessError


PASSWORDS = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """接收明文密码，返回 bcrypt 哈希。"""
    return PASSWORDS.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """比较明文和哈希，返回是否匹配。"""
    return PASSWORDS.verify(password, password_hash)


def create_token(user_id: int) -> str:
    """接收用户 ID，返回含过期时间的 JWT。"""
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": str(user_id), "exp": expires}, settings.jwt_secret, algorithm=ALGORITHM)


def read_token(token: str) -> int:
    """解码 JWT 并返回用户 ID；无效或过期时抛 401 异常。"""
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise BusinessError("登录已失效，请重新登录", 401) from exc

