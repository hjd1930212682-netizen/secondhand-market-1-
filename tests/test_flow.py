# Author: 安远
"""全链路冒烟：注册 → 发布 → 收藏 → 下单 → 状态流转 → 评价 → 消息。"""


def test_full_trade_flow(client, seed_context):
    """验证一笔交易从发布到互评的完整链路，每步断言状态变化。"""
    seller = seed_context["seller"]
    buyer = seed_context["buyer"]
    goods_id = seed_context["goods_id"]

    # 1. 买家能看到在售商品
    listing = client.get("/api/goods", params={"keyword": "机械键盘"})
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    # 2. 浏览详情，浏览量 +1
    detail = client.get(f"/api/goods/{goods_id}")
    assert detail.status_code == 200
    assert detail.json()["view_count"] == 1
    assert detail.json()["seller_name"] == "卖家小杨"

    # 3. 收藏
    assert client.post("/api/favorites", headers=buyer, json={"goods_id": goods_id}).status_code == 201
    favorites = client.get("/api/favorites", headers=buyer).json()
    assert favorites["total"] == 1

    # 4. 下单：订单初始为待确认，商品立即变已售
    order = client.post("/api/orders", headers=buyer, json={"goods_id": goods_id})
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]
    assert order.json()["status"] == "PENDING"
    assert client.get(f"/api/goods/{goods_id}").json()["status"] == "已售"

    # 5. 卖家确认出售 -> 待付款
    paid = client.put(
        f"/api/orders/{order_id}/status", headers=seller, json={"to_status": "PAID_PENDING"}
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "PAID_PENDING"

    # 6. 买家确认收货 -> 已完成
    done = client.put(
        f"/api/orders/{order_id}/status", headers=buyer, json={"to_status": "COMPLETED"}
    )
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "COMPLETED"
    assert done.json()["finished_at"] is not None

    # 7. 买家评价
    review = client.post(
        f"/api/orders/{order_id}/review", headers=buyer, json={"rating": 5, "content": "东西很好"}
    )
    assert review.status_code == 201, review.text
    assert review.json()["rating"] == 5

    # 8. 卖家评分统计为 5.0
    rating = client.get(f"/api/users/{seed_context['seller_id']}/rating").json()
    assert rating["average"] == 5.0
    assert rating["count"] == 1

    # 9. 商品评价列表可查
    goods_reviews = client.get(f"/api/goods/{goods_id}/reviews").json()
    assert goods_reviews["total"] == 1

    # 10. 站内消息
    sent = client.post(
        "/api/messages",
        headers=buyer,
        json={"receiver_id": seed_context["seller_id"], "content": "什么时候发货？"},
    )
    assert sent.status_code == 201
    assert client.get("/api/messages/unread-count", headers=seller).json()["count"] == 1

    # 11. 标记已读后未读数归零
    client.put("/api/messages/read", headers=seller, json={"peer_id": seed_context["buyer_id"]})
    assert client.get("/api/messages/unread-count", headers=seller).json()["count"] == 0


def test_available_actions_follow_state_machine(client, seed_context):
    """订单详情返回的按钮必须与当前状态、当前角色严格匹配。"""
    buyer = seed_context["buyer"]
    seller = seed_context["seller"]

    order = client.post(
        "/api/orders", headers=buyer, json={"goods_id": seed_context["goods_id"]}
    ).json()
    order_id = order["id"]

    # 以规格中的六条转移为准：PENDING 阶段卖家可确认或拒绝，买家可撤销。
    buyer_view = client.get(f"/api/orders/{order_id}", headers=buyer).json()
    seller_view = client.get(f"/api/orders/{order_id}", headers=seller).json()
    assert {a["to_status"] for a in buyer_view["available_actions"]} == {"CANCELLED"}
    assert [a["label"] for a in buyer_view["available_actions"]] == ["撤销订单"]
    assert {a["to_status"] for a in seller_view["available_actions"]} == {"PAID_PENDING", "CANCELLED"}
    assert {a["label"] for a in seller_view["available_actions"]} == {"确认出售", "拒绝"}
