# Author: 安远
"""覆盖注册、商品、订单、评价、收藏和消息的真实 HTTP 交互。"""

import pytest
from fastapi.testclient import TestClient


def register_and_login(client: TestClient, username: str) -> dict:
    """创建并登录测试用户；返回 Bearer 请求头。"""
    assert client.post("/api/auth/register", json={"username": username, "password": "secret123",
                                                    "nickname": username}).status_code == 201
    token = client.post("/api/auth/login", json={"username": username,
                                                  "password": "secret123"}).json()["access_token"]
    return {"Authorization": "Bearer " + token}


def create_goods(client: TestClient, seller: dict) -> int:
    """用卖家请求头发布一件商品，返回商品 ID。"""
    response = client.post("/api/goods", headers=seller,
                           json={"category_id": 1, "title": "测试教材", "description": "九成新",
                                 "price": "25.00", "images": ""})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_static_pages_and_openapi(client: TestClient) -> None:
    """首页、静态页面和公开 API 描述均可访问。"""
    assert client.get("/pages/index.html").status_code == 200
    assert client.get("/docs").status_code == 200
    api_paths = [p for p in client.get("/openapi.json").json()["paths"] if p.startswith("/api/")]
    # 固定规格列出 23 个不同路径；不增加健康检查接口。
    assert len(api_paths) == 24


def test_register_login_and_profile(client: TestClient) -> None:
    """注册后能登录、读取本人资料并改密。"""
    auth = register_and_login(client, "seller")
    assert client.get("/api/auth/me", headers=auth).json()["username"] == "seller"
    assert client.put("/api/users/me", headers=auth,
                      json={"nickname": "新昵称", "phone": "123", "avatar": None}).json()["nickname"] == "新昵称"
    assert client.put("/api/users/me/password", headers=auth,
                      json={"old_password": "secret123", "new_password": "newsecret"}).status_code == 200
    assert client.post("/api/auth/login", json={"username": "seller", "password": "newsecret"}).status_code == 200


@pytest.mark.parametrize("payload", [
    {"username": "", "password": "secret123", "nickname": "A"},
    {"username": "ab", "password": "secret123", "nickname": "A"},
    {"username": "valid", "password": "x", "nickname": "A"},
    {"username": "valid", "password": "secret123", "nickname": ""},
])
def test_invalid_registration(client: TestClient, payload: dict) -> None:
    """空值、短用户名和弱密码返回中文 400。"""
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"]


def test_duplicate_user_and_wrong_password(client: TestClient) -> None:
    """重复账号与错误密码有明确错误码。"""
    register_and_login(client, "seller")
    assert client.post("/api/auth/register", json={"username": "seller", "password": "secret123",
                                                    "nickname": "卖家"}).status_code == 409
    assert client.post("/api/auth/login", json={"username": "seller",
                                                  "password": "bad"}).status_code == 401


@pytest.mark.parametrize("price", ["0", "-1", "100000000.00"])
def test_invalid_prices(client: TestClient, price: str) -> None:
    """零价、负价和超 DECIMAL 范围的商品被拒绝。"""
    auth = register_and_login(client, "seller")
    assert client.post("/api/goods", headers=auth,
                       json={"category_id": 1, "title": "书", "description": "", "price": price,
                             "images": ""}).status_code == 400


def test_goods_search_and_soft_delete(client: TestClient) -> None:
    """关键词搜索命中后，软删除使商品离开公开列表。"""
    auth = register_and_login(client, "seller")
    goods_id = create_goods(client, auth)
    result = client.get("/api/goods?keyword=教材&page=1&size=12").json()
    assert result["total"] == 1 and result["items"][0]["id"] == goods_id
    assert client.delete(f"/api/goods/{goods_id}", headers=auth).status_code == 200
    assert client.get("/api/goods").json()["total"] == 0
    assert client.get(f"/api/goods/{goods_id}").status_code == 404


def test_order_state_and_review(client: TestClient) -> None:
    """两账号完成发布、下单、卖家确认、买家收货和一次评价。"""
    seller = register_and_login(client, "seller")
    buyer = register_and_login(client, "buyer")
    goods_id = create_goods(client, seller)
    order = client.post("/api/orders", headers=buyer, json={"goods_id": goods_id})
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]
    assert client.post("/api/orders", headers=buyer, json={"goods_id": goods_id}).status_code == 409
    assert client.put(f"/api/orders/{order_id}/status", headers=buyer,
                      json={"to_status": "COMPLETED"}).status_code == 409
    assert client.put(f"/api/orders/{order_id}/status", headers=seller,
                      json={"to_status": "PAID_PENDING"}).status_code == 200
    assert client.put(f"/api/orders/{order_id}/status", headers=buyer,
                      json={"to_status": "COMPLETED"}).status_code == 200
    assert client.post(f"/api/orders/{order_id}/review", headers=buyer,
                       json={"rating": 5, "content": "交易顺利"}).status_code == 201
    assert client.post(f"/api/orders/{order_id}/review", headers=buyer,
                       json={"rating": 5, "content": "重复"}).status_code == 409
    assert client.get(f"/api/goods/{goods_id}/reviews").json()["total"] == 1


def test_unauthorized_and_favorites(client: TestClient) -> None:
    """未登录与越权拦截，重复收藏被拒绝。"""
    seller = register_and_login(client, "seller")
    buyer = register_and_login(client, "buyer")
    goods_id = create_goods(client, seller)
    assert client.post("/api/orders", json={"goods_id": goods_id}).status_code == 401
    assert client.put(f"/api/goods/{goods_id}/status", headers=buyer,
                      json={"status": "已下架"}).status_code == 403
    assert client.post("/api/favorites", headers=buyer,
                       json={"goods_id": goods_id}).status_code == 201
    assert client.post("/api/favorites", headers=buyer,
                       json={"goods_id": goods_id}).status_code == 409
    assert client.get("/api/favorites", headers=buyer).json()["total"] == 1


def test_messages(client: TestClient) -> None:
    """买家发消息，卖家可读并标记已读。"""
    seller = register_and_login(client, "seller")
    buyer = register_and_login(client, "buyer")
    seller_id = client.get("/api/auth/me", headers=seller).json()["id"]
    buyer_id = client.get("/api/auth/me", headers=buyer).json()["id"]
    response = client.post("/api/messages", headers=buyer,
                           json={"receiver_id": seller_id, "content": "可以校内面交吗？"})
    assert response.status_code == 201
    assert client.get("/api/messages/unread-count", headers=seller).json()["count"] == 1
    assert client.get(f"/api/messages?peer_id={buyer_id}", headers=seller).json()["total"] == 1
    assert client.put("/api/messages/read", headers=seller,
                      json={"peer_id": buyer_id}).json()["updated"] == 1
    assert client.get("/api/messages/unread-count", headers=seller).json()["count"] == 0
