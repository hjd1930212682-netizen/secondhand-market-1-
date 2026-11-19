# Author: 安远
"""仅在独立 MySQL 测试库可连接时运行五买家并发下单验证。"""

import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models import Category


def test_five_buyers_only_one_order() -> None:
    """五个并发请求竞争同一商品，断言恰有一单成功。"""
    # 配置经 pydantic 从 .env 读取，不会写回 os.environ，因此优先查配置对象
    url = os.getenv("TEST_DATABASE_URL") or get_settings().test_database_url or ""
    if not url or not url.startswith("mysql+pymysql://") or not url.split("?")[0].endswith("/secondhand_market_test"):
        pytest.skip("需要独立的 secondhand_market_test MySQL 库")
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect():
            pass
    except Exception:
        pytest.skip("MySQL 测试库未连接")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    def test_db():
        """每个并发请求使用独立 MySQL 会话。"""
        with Session(engine, autoflush=False, expire_on_commit=False) as db:
            yield db

    app.dependency_overrides[get_db] = test_db
    try:
        with Session(engine) as db:
            db.add(Category(name="数码电子"))
            db.commit()
        with TestClient(app) as client:
            def account(index: int) -> dict:
                """创建一个测试账号，返回 Bearer 请求头。"""
                name = f"buyer{index}"
                client.post("/api/auth/register", json={
                    "username": name, "password": "secret123", "nickname": name})
                token = client.post("/api/auth/login", json={
                    "username": name, "password": "secret123"}).json()["access_token"]
                return {"Authorization": "Bearer " + token}

            seller = account(0)
            buyers = [account(i) for i in range(1, 6)]
            goods_id = client.post("/api/goods", headers=seller, json={
                "category_id": 1, "title": "并发测试商品", "description": "",
                "price": "20.00", "images": ""}).json()["id"]

            def place_order(headers: dict) -> tuple[int, str]:
                """并发调用下单接口，返回状态码与错误文本。"""
                with TestClient(app) as worker:
                    response = worker.post("/api/orders", headers=headers, json={"goods_id": goods_id})
                    return response.status_code, response.json().get("detail", "")

            with ThreadPoolExecutor(max_workers=5) as pool:
                results = list(pool.map(place_order, buyers))
            assert sum(status == 201 for status, _ in results) == 1
            assert sum(status == 409 and message == "商品已被抢购" for status, message in results) == 4
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
