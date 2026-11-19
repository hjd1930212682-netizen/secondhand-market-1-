# Author: 郝津德
"""定义 SQLAlchemy 基类、MySQL 引擎和请求级会话。"""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """所有七张业务表共同继承的声明式基类。"""


def build_engine(url: str) -> Engine:
    """按连接串创建引擎；url 为 SQLAlchemy 连接串，返回 Engine。

    MySQL 需要连接池保活与回收；SQLite 用本地文件验证时则需要放开线程检查，
    否则 FastAPI 的线程池会报 "SQLite objects created in a thread..."。
    """
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600, pool_size=10, max_overflow=20)


@lru_cache
def get_engine() -> Engine:
    """根据 DATABASE_URL 创建连接池；无参数，返回数据库引擎。"""
    return build_engine(get_settings().database_url)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """创建会话工厂；无参数，返回关闭自动提交的工厂。"""
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """为一个请求提供会话；无参数，逐次产出 Session 并在结束时关闭。"""
    with get_session_factory()() as session:
        yield session

