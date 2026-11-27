# Author: 安远
"""订单状态机、防重复成交、越权与社交功能异常用例。"""


def _place_order(client, seed_context):
    """下单并返回订单 ID，供多个用例复用。"""
    resp = client.post(
        "/api/orders", headers=seed_context["buyer"], json={"goods_id": seed_context["goods_id"]}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_order_requires_login(client, seed_context):
    """未登录不能下单。"""
    assert client.post(
        "/api/orders", json={"goods_id": seed_context["goods_id"]}
    ).status_code == 401


def test_cannot_buy_own_goods(client, seed_context):
    """卖家不能购买自己发布的商品。"""
    resp = client.post(
        "/api/orders", headers=seed_context["seller"], json={"goods_id": seed_context["goods_id"]}
    )
    assert resp.status_code == 400


def test_duplicate_purchase_rejected(client, seed_context):
    """同一件商品不能被买两次：第二单必须 409，防止重复成交。"""
    _place_order(client, seed_context)
    second = client.post(
        "/api/orders", headers=seed_context["buyer"], json={"goods_id": seed_context["goods_id"]}
    )
    assert second.status_code == 409
    assert "抢购" in second.json()["detail"] or "售" in second.json()["detail"]


def test_illegal_transition_rejected(client, seed_context):
    """PENDING 直接跳 COMPLETED 属于非法流转，必须 409。"""
    order_id = _place_order(client, seed_context)
    resp = client.put(
        f"/api/orders/{order_id}/status",
        headers=seed_context["buyer"],
        json={"to_status": "COMPLETED"},
    )
    assert resp.status_code == 409


def test_role_without_permission_forbidden(client, seed_context):
    """买家不能替卖家确认出售，属于越权 403。"""
    order_id = _place_order(client, seed_context)
    resp = client.put(
        f"/api/orders/{order_id}/status",
        headers=seed_context["buyer"],
        json={"to_status": "PAID_PENDING"},
    )
    assert resp.status_code == 403


def test_unknown_status_rejected(client, seed_context):
    """完全不存在目标状态时返回 409。"""
    order_id = _place_order(client, seed_context)
    resp = client.put(
        f"/api/orders/{order_id}/status",
        headers=seed_context["seller"],
        json={"to_status": "WHATEVER"},
    )
    assert resp.status_code == 409


def test_third_party_cannot_view_order(client, seed_context, make_user):
    """与订单无关的第三方查看订单详情返回 403。"""
    order_id = _place_order(client, seed_context)
    outsider_headers, _ = make_user("outsider")
    resp = client.get(f"/api/orders/{order_id}", headers=outsider_headers)
    assert resp.status_code == 403


def test_cancel_after_confirm_restores_goods(client, seed_context):
    """确认后买家取消，商品应重新回到在售。"""
    order_id = _place_order(client, seed_context)
    client.put(
        f"/api/orders/{order_id}/status",
        headers=seed_context["seller"],
        json={"to_status": "PAID_PENDING"},
    )
    cancelled = client.put(
        f"/api/orders/{order_id}/status",
        headers=seed_context["buyer"],
        json={"to_status": "CANCELLED"},
    )
    assert cancelled.status_code == 200
    assert client.get(f"/api/goods/{seed_context['goods_id']}").json()["status"] == "在售"


def test_buyer_cancel_pending_restores_goods(client, seed_context):
    """待确认阶段买家撤销，商品应回到在售且订单结束。"""
    order_id = _place_order(client, seed_context)
    cancelled = client.put(
        f"/api/orders/{order_id}/status",
        headers=seed_context["buyer"],
        json={"to_status": "CANCELLED"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    assert cancelled.json()["finished_at"] is not None
    assert client.get(f"/api/goods/{seed_context['goods_id']}").json()["status"] == "在售"


def test_completed_then_refund_keeps_goods_sold(client, seed_context):
    """已完成订单申请退款：商品不重新上架（交易已实际发生）。"""
    order_id = _place_order(client, seed_context)
    client.put(
        f"/api/orders/{order_id}/status",
        headers=seed_context["seller"],
        json={"to_status": "PAID_PENDING"},
    )
    client.put(
        f"/api/orders/{order_id}/status",
        headers=seed_context["buyer"],
        json={"to_status": "COMPLETED"},
    )
    refunded = client.put(
        f"/api/orders/{order_id}/status",
        headers=seed_context["buyer"],
        json={"to_status": "CANCELLED"},
    )
    assert refunded.status_code == 200
    assert client.get(f"/api/goods/{seed_context['goods_id']}").json()["status"] == "已售"


def test_review_requires_completed_order(client, seed_context):
    """未完成的订单不能评价。"""
    order_id = _place_order(client, seed_context)
    resp = client.post(
        f"/api/orders/{order_id}/review",
        headers=seed_context["buyer"],
        json={"rating": 5, "content": "还没收到"},
    )
    assert resp.status_code == 400


def test_review_only_by_buyer(client, seed_context):
    """卖家不能评价自己卖出的订单。"""
    order_id = _place_order(client, seed_context)
    client.put(
        f"/api/orders/{order_id}/status",
        headers=seed_context["seller"],
        json={"to_status": "PAID_PENDING"},
    )
    client.put(
        f"/api/orders/{order_id}/status",
        headers=seed_context["buyer"],
        json={"to_status": "COMPLETED"},
    )
    resp = client.post(
        f"/api/orders/{order_id}/review",
        headers=seed_context["seller"],
        json={"rating": 5, "content": "我是卖家"},
    )
    assert resp.status_code == 403


def test_duplicate_review_rejected(client, seed_context):
    """同一订单只能评价一次，第二次 409。"""
    order_id = _place_order(client, seed_context)
    client.put(
        f"/api/orders/{order_id}/status",
        headers=seed_context["seller"],
        json={"to_status": "PAID_PENDING"},
    )
    client.put(
        f"/api/orders/{order_id}/status",
        headers=seed_context["buyer"],
        json={"to_status": "COMPLETED"},
    )
    body = {"rating": 4, "content": "不错"}
    assert client.post(
        f"/api/orders/{order_id}/review", headers=seed_context["buyer"], json=body
    ).status_code == 201
    assert client.post(
        f"/api/orders/{order_id}/review", headers=seed_context["buyer"], json=body
    ).status_code == 409


def test_rating_out_of_range(client, seed_context):
    """评分 6 分越界：边界值，必须被参数校验拦下。"""
    order_id = _place_order(client, seed_context)
    resp = client.post(
        f"/api/orders/{order_id}/review",
        headers=seed_context["buyer"],
        json={"rating": 6, "content": "超纲"},
    )
    assert resp.status_code == 400


def test_favorite_duplicate_rejected(client, seed_context):
    """重复收藏同一商品返回 409，而不是产生两条记录。"""
    body = {"goods_id": seed_context["goods_id"]}
    assert client.post("/api/favorites", headers=seed_context["buyer"], json=body).status_code == 201
    assert client.post("/api/favorites", headers=seed_context["buyer"], json=body).status_code == 409


def test_remove_favorite_not_exists(client, seed_context):
    """取消一个没收藏过的商品返回 404。"""
    assert client.delete(
        f"/api/favorites/{seed_context['goods_id']}", headers=seed_context["buyer"]
    ).status_code == 404


def test_message_to_self_rejected(client, seed_context):
    """不能给自己发消息。"""
    resp = client.post(
        "/api/messages",
        headers=seed_context["buyer"],
        json={"receiver_id": seed_context["buyer_id"], "content": "自言自语"},
    )
    assert resp.status_code == 400


def test_message_blank_content_rejected(client, seed_context):
    """空白消息内容属于边界值。"""
    resp = client.post(
        "/api/messages",
        headers=seed_context["buyer"],
        json={"receiver_id": seed_context["seller_id"], "content": "   "},
    )
    assert resp.status_code in (400, 422)


def test_order_list_role_validation(client, seed_context):
    """role 只接受 buyer / seller。"""
    assert client.get("/api/orders", headers=seed_context["buyer"], params={"role": "admin"}).status_code == 400


def test_order_list_status_filter(client, seed_context):
    """按状态筛选订单，别的状态不应出现。"""
    _place_order(client, seed_context)
    pending = client.get(
        "/api/orders", headers=seed_context["buyer"], params={"status": "PENDING"}
    ).json()
    completed = client.get(
        "/api/orders", headers=seed_context["buyer"], params={"status": "COMPLETED"}
    ).json()
    assert pending["total"] == 1
    assert completed["total"] == 0
