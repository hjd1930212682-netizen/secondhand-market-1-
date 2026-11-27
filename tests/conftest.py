# Author: 安远
"""FastAPI TestClient 测试会话；普通接口用内存库，MySQL 并发另测。"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-only-secret-never-use-in-production")

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Category  # noqa: E402


@compiles(TINYINT, "sqlite")
def compile_tinyint(element: TINYINT, compiler, **kwargs) -> str:
    """将 MySQL TINYINT 译成 SQLite INTEGER；仅供不涉及锁的接口测试。"""
    return "INTEGER"


@pytest.fixture
def client() -> TestClient:
    """每个用例得到隔离数据库和测试客户端。"""
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record) -> None:
        """为 SQLite 测试连接打开外键约束；无返回值。"""
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Category(name="数码电子"), Category(name="书籍资料")])
        db.commit()

    def test_db():
        """为每个测试请求产出独立会话。"""
        with Session(engine, autoflush=False, expire_on_commit=False) as db:
            yield db

    app.dependency_overrides[get_db] = test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def make_user(client: TestClient):
    """返回一个「注册 + 登录」的工厂，产出 (请求头, 用户信息)。"""

    def _make(username: str, password: str = "pass1234", nickname: str | None = None):
        """注册指定账号并登录；返回可直接用于请求的 Bearer 头与用户对象。"""
        registered = client.post(
            "/api/auth/register",
            json={"username": username, "password": password, "nickname": nickname or username},
        )
        assert registered.status_code == 201, registered.text
        token = client.post(
            "/api/auth/login", json={"username": username, "password": password}
        ).json()["access_token"]
        return {"Authorization": "Bearer " + token}, registered.json()

    return _make


@pytest.fixture
def seed_context(client: TestClient) -> dict:
    """创建卖家、买家和在售商品，返回全链路测试上下文。"""

    def account(username: str, nickname: str) -> tuple[dict, int]:
        """注册并登录一个账号，返回请求头和用户 ID。"""
        response = client.post("/api/auth/register", json={
            "username": username, "nickname": nickname, "password": "secret123"})
        user_id = response.json()["id"]
        token = client.post("/api/auth/login", json={
            "username": username, "password": "secret123"}).json()["access_token"]
        return {"Authorization": "Bearer " + token}, user_id

    seller, seller_id = account("seller", "卖家小杨")
    buyer, buyer_id = account("buyer", "买家小王")
    # client 夹具已预置分类（1=数码电子、2=书籍资料）
    category_id = 1
    goods = client.post("/api/goods", headers=seller, json={
        "category_id": category_id, "title": "机械键盘", "description": "九成新 青轴",
        "price": "128.00", "images": ""}).json()
    return {"seller": seller, "buyer": buyer, "seller_id": seller_id,
            "buyer_id": buyer_id, "category_id": category_id, "goods_id": goods["id"]}

