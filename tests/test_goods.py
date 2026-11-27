# Author: 安远
"""商品发布、搜索、越权与边界值用例。"""


def test_create_goods_requires_login(client):
    """未登录不能发布商品。"""
    resp = client.post(
        "/api/goods",
        json={"category_id": 1, "title": "测试", "description": "", "price": "1.00", "images": ""},
    )
    assert resp.status_code == 401


def test_price_zero_rejected(client, seed_context):
    """价格 0：边界值，业务上不允许白送。"""
    resp = client.post(
        "/api/goods",
        headers=seed_context["seller"],
        json={
            "category_id": seed_context["category_id"],
            "title": "零元商品",
            "description": "",
            "price": "0",
            "images": "",
        },
    )
    assert resp.status_code == 400


def test_price_negative_rejected(client, seed_context):
    """价格为负：异常值。"""
    resp = client.post(
        "/api/goods",
        headers=seed_context["seller"],
        json={
            "category_id": seed_context["category_id"],
            "title": "负价商品",
            "description": "",
            "price": "-10",
            "images": "",
        },
    )
    assert resp.status_code == 400


def test_blank_title_rejected(client, seed_context):
    """标题全是空格：边界值，不能当成有效标题。"""
    resp = client.post(
        "/api/goods",
        headers=seed_context["seller"],
        json={
            "category_id": seed_context["category_id"],
            "title": "   ",
            "description": "",
            "price": "10.00",
            "images": "",
        },
    )
    assert resp.status_code == 400


def test_category_not_exist(client, seed_context):
    """分类 ID 不存在时拒绝发布，避免脏数据。"""
    resp = client.post(
        "/api/goods",
        headers=seed_context["seller"],
        json={
            "category_id": 99999,
            "title": "野分类",
            "description": "",
            "price": "10.00",
            "images": "",
        },
    )
    assert resp.status_code == 400


def test_update_others_goods_forbidden(client, seed_context):
    """越权编辑他人商品返回 403。"""
    resp = client.put(
        f"/api/goods/{seed_context['goods_id']}",
        headers=seed_context["buyer"],
        json={
            "category_id": seed_context["category_id"],
            "title": "被改的标题",
            "description": "",
            "price": "1.00",
            "images": "",
        },
    )
    assert resp.status_code == 403


def test_delete_others_goods_forbidden(client, seed_context):
    """越权删除他人商品返回 403。"""
    assert client.delete(
        f"/api/goods/{seed_context['goods_id']}", headers=seed_context["buyer"]
    ).status_code == 403


def test_soft_delete_keeps_record(client, seed_context):
    """删除是软删除：商品变已下架，列表查不到，详情也查不到。"""
    resp = client.delete(f"/api/goods/{seed_context['goods_id']}", headers=seed_context["seller"])
    assert resp.status_code == 200
    assert resp.json()["status"] == "已下架"

    listing = client.get("/api/goods", params={"keyword": "机械键盘"}).json()
    assert listing["total"] == 0
    assert client.get(f"/api/goods/{seed_context['goods_id']}").status_code == 404


def test_keyword_search_matches_description(client, seed_context):
    """关键词命中描述文本也算匹配。"""
    resp = client.get("/api/goods", params={"keyword": "青轴"}).json()
    assert resp["total"] == 1


def test_keyword_search_no_result(client):
    """搜索无结果时返回空列表而不是报错。"""
    resp = client.get("/api/goods", params={"keyword": "完全不存在的商品"}).json()
    assert resp["items"] == []
    assert resp["total"] == 0


def test_pagination_beyond_last_page(client, seed_context):
    """页码越界：边界值，应返回空列表且 total 仍正确。"""
    resp = client.get("/api/goods", params={"page": 99, "size": 12}).json()
    assert resp["items"] == []
    assert resp["total"] >= 1


def test_invalid_sort_rejected(client):
    """非法排序参数返回 400，而不是默默用默认排序。"""
    assert client.get("/api/goods", params={"sort": "hack"}).status_code == 400


def test_sort_by_price_asc(client, seed_context):
    """价格升序：先发贵的再加个便宜的，验证排序真实生效。"""
    client.post(
        "/api/goods",
        headers=seed_context["seller"],
        json={
            "category_id": seed_context["category_id"],
            "title": "便宜的数据线",
            "description": "",
            "price": "9.90",
            "images": "",
        },
    )
    prices = [float(g["price"]) for g in client.get("/api/goods", params={"sort": "price_asc"}).json()["items"]]
    assert prices == sorted(prices)


def test_view_count_increment(client, seed_context):
    """每次打开详情浏览量 +1。"""
    for expected in (1, 2, 3):
        assert client.get(f"/api/goods/{seed_context['goods_id']}").json()["view_count"] == expected


def test_goods_detail_404(client):
    """不存在的商品返回 404。"""
    assert client.get("/api/goods/99999").status_code == 404


def test_create_goods_returns_full_shape(client, seed_context):
    """发布正常流：出参必须带卖家与分类字段，前端直接用返回值渲染卡片。"""
    resp = client.post(
        "/api/goods",
        headers=seed_context["seller"],
        json={
            "category_id": seed_context["category_id"],
            "title": "二手显示器",
            "description": "27 寸 2K",
            "price": "899.00",
            "images": "/static/uploads/a.png",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "在售"
    assert body["view_count"] == 0
    assert body["seller_name"] == "卖家小杨"
    assert body["category_name"] == "数码电子"
    assert body["price"] in ("899.00", 899.0)
    assert set(body) >= {
        "id", "seller_id", "category_id", "title", "description", "price", "images",
        "status", "view_count", "created_at", "seller_name", "seller_avatar",
        "seller_credit", "category_name",
    }


def test_update_goods_is_full_replacement(client, seed_context):
    """编辑正常流：PUT 全量替换，改完详情读取到新值，且出参与发布同形。"""
    resp = client.put(
        f"/api/goods/{seed_context['goods_id']}",
        headers=seed_context["seller"],
        json={
            "category_id": 2,
            "title": "机械键盘（已换轴）",
            "description": "换过轴体",
            "price": "99.50",
            "images": "",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "机械键盘（已换轴）"
    assert body["category_name"] == "书籍资料"
    assert body["seller_name"] == "卖家小杨"

    detail = client.get(f"/api/goods/{seed_context['goods_id']}").json()
    assert detail["title"] == "机械键盘（已换轴）"
    assert float(detail["price"]) == 99.50


def test_update_goods_requires_category_id(client, seed_context):
    """PUT 是全量替换：漏了 category_id 必须 400，不能沿用旧分类。"""
    resp = client.put(
        f"/api/goods/{seed_context['goods_id']}",
        headers=seed_context["seller"],
        json={"title": "只改标题", "description": "", "price": "10.00", "images": ""},
    )
    assert resp.status_code == 400


def test_update_unknown_goods(client, seed_context):
    """编辑不存在的商品返回 404，不能静默成功。"""
    resp = client.put(
        "/api/goods/99999",
        headers=seed_context["seller"],
        json={
            "category_id": seed_context["category_id"],
            "title": "幽灵商品",
            "description": "",
            "price": "10.00",
            "images": "",
        },
    )
    assert resp.status_code == 404


def test_toggle_status_hides_and_restores(client, seed_context):
    """下架后在售列表与详情都查不到，重新上架又能查到——软删除的可逆性。"""
    goods_id = seed_context["goods_id"]
    off = client.put(f"/api/goods/{goods_id}/status", headers=seed_context["seller"],
                     json={"status": "已下架"})
    assert off.status_code == 200 and off.json()["status"] == "已下架"
    assert client.get(f"/api/goods/{goods_id}").status_code == 404
    assert client.get("/api/goods", params={"keyword": "机械键盘"}).json()["total"] == 0

    on = client.put(f"/api/goods/{goods_id}/status", headers=seed_context["seller"],
                    json={"status": "在售"})
    assert on.status_code == 200 and on.json()["status"] == "在售"
    assert client.get(f"/api/goods/{goods_id}").status_code == 200


def test_invalid_status_rejected(client, seed_context):
    """状态只允许「在售 / 已下架」，写别的值返回 400。"""
    resp = client.put(
        f"/api/goods/{seed_context['goods_id']}/status",
        headers=seed_context["seller"],
        json={"status": "售罄"},
    )
    assert resp.status_code == 400


def test_delete_unknown_goods(client, seed_context):
    """删除不存在的商品返回 404。"""
    assert client.delete("/api/goods/99999", headers=seed_context["seller"]).status_code == 404


def test_price_max_boundary(client, seed_context):
    """价格上限：99999999.99（DECIMAL(10,2) 满位）可发布，再大一位就 400。"""
    ok = client.post(
        "/api/goods",
        headers=seed_context["seller"],
        json={"category_id": seed_context["category_id"], "title": "顶格价",
              "description": "", "price": "99999999.99", "images": ""},
    )
    assert ok.status_code == 201

    too_big = client.post(
        "/api/goods",
        headers=seed_context["seller"],
        json={"category_id": seed_context["category_id"], "title": "超上限",
              "description": "", "price": "100000000.00", "images": ""},
    )
    assert too_big.status_code == 400


def test_price_three_decimals_rejected(client, seed_context):
    """价格三位小数：列只存两位，不能靠四舍五入悄悄改价。"""
    resp = client.post(
        "/api/goods",
        headers=seed_context["seller"],
        json={"category_id": seed_context["category_id"], "title": "三位小数",
              "description": "", "price": "9.999", "images": ""},
    )
    assert resp.status_code == 400


def test_title_boundary_length(client, seed_context):
    """标题 160 字可用、161 字被拒，且首尾空格被去掉后再存。"""
    ok = client.post(
        "/api/goods",
        headers=seed_context["seller"],
        json={"category_id": seed_context["category_id"], "title": "  " + "标" * 160 + "  ",
              "description": "", "price": "1.00", "images": ""},
    )
    assert ok.status_code == 201
    assert ok.json()["title"] == "标" * 160

    too_long = client.post(
        "/api/goods",
        headers=seed_context["seller"],
        json={"category_id": seed_context["category_id"], "title": "标" * 161,
              "description": "", "price": "1.00", "images": ""},
    )
    assert too_long.status_code == 400


def test_pagination_bounds_rejected(client):
    """page/size 越界：page=0、size=0、size=101 全部 400，而不是自动纠正。"""
    assert client.get("/api/goods", params={"page": 0}).status_code == 400
    assert client.get("/api/goods", params={"size": 0}).status_code == 400
    assert client.get("/api/goods", params={"size": 101}).status_code == 400


def test_category_filter(client, seed_context):
    """按分类过滤：命中一件，换到没有商品的分类返回空列表且 total=0。"""
    hit = client.get("/api/goods", params={"category_id": seed_context["category_id"]}).json()
    assert hit["total"] == 1
    assert hit["items"][0]["id"] == seed_context["goods_id"]

    other = client.get("/api/goods", params={"category_id": 2}).json()
    assert other["total"] == 0 and other["items"] == []


def test_category_id_not_integer_rejected(client):
    """category_id 传空串或非数字：必须 400，前端才不会把空筛选当全量。"""
    assert client.get("/api/goods", params={"category_id": ""}).status_code == 400
    assert client.get("/api/goods", params={"category_id": "abc"}).status_code == 400


def test_categories_list(client):
    """分类列表正常流：返回 id/name/parent_id 三字段。"""
    body = client.get("/api/categories").json()
    assert body["total"] == 2
    assert {"id", "name", "parent_id"} == set(body["items"][0])


def test_hot_sort_orders_by_view_count(client, seed_context):
    """热度排序按浏览量降序：给第二件商品刷两次浏览，它应排到第一。"""
    second = client.post(
        "/api/goods",
        headers=seed_context["seller"],
        json={"category_id": seed_context["category_id"], "title": "冷门商品",
              "description": "", "price": "5.00", "images": ""},
    ).json()
    client.get(f"/api/goods/{second['id']}")
    client.get(f"/api/goods/{second['id']}")

    items = client.get("/api/goods", params={"sort": "hot"}).json()["items"]
    assert items[0]["id"] == second["id"]
    assert items[0]["view_count"] >= items[1]["view_count"]


def test_my_goods_pagination_and_off_shelf_visible(client, seed_context):
    """我的商品：分页数字准确，且已下架的商品仍在这里（软删除不丢记录）。"""
    for index in range(2):
        client.post(
            "/api/goods",
            headers=seed_context["seller"],
            json={"category_id": seed_context["category_id"], "title": f"批量商品{index}",
                  "description": "", "price": "3.00", "images": ""},
        )
    client.delete(f"/api/goods/{seed_context['goods_id']}", headers=seed_context["seller"])

    first = client.get("/api/users/me/goods", headers=seed_context["seller"],
                       params={"page": 1, "size": 2}).json()
    assert first["total"] == 3
    assert len(first["items"]) == 2
    second = client.get("/api/users/me/goods", headers=seed_context["seller"],
                        params={"page": 2, "size": 2}).json()
    assert len(second["items"]) == 1

    all_titles = {item["status"] for item in first["items"] + second["items"]}
    assert "已下架" in all_titles


def test_my_goods_requires_login(client):
    """我的商品必须登录，匿名访问 401。"""
    assert client.get("/api/users/me/goods").status_code == 401
