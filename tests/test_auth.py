# Author: 安远
"""注册登录与账号安全的边界、异常用例。"""


def test_register_success(client):
    """正常注册返回 201，且响应不含密码哈希。"""
    resp = client.post(
        "/api/auth/register",
        json={"username": "newbie", "password": "pass1234", "nickname": "新同学"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "newbie"
    assert "password" not in body and "password_hash" not in body


def test_register_duplicate_username(client, make_user):
    """重复用户名必须被拒绝，且返回 409 而不是静默覆盖。"""
    make_user("dupuser")
    resp = client.post(
        "/api/auth/register",
        json={"username": "dupuser", "password": "pass1234", "nickname": "另一个"},
    )
    assert resp.status_code == 409
    assert "已被注册" in resp.json()["detail"]


def test_register_username_too_short(client):
    """用户名少于 3 位：边界值，应被参数校验拦下。"""
    resp = client.post(
        "/api/auth/register", json={"username": "ab", "password": "pass1234", "nickname": "短"}
    )
    assert resp.status_code == 400


def test_register_username_illegal_chars(client):
    """用户名含空格或中文标点：格式不合法。"""
    resp = client.post(
        "/api/auth/register",
        json={"username": "bad name!", "password": "pass1234", "nickname": "非法"},
    )
    assert resp.status_code == 400


def test_register_password_too_short(client):
    """密码 5 位：边界值，应被拒绝。"""
    resp = client.post(
        "/api/auth/register", json={"username": "shortpwd", "password": "12345", "nickname": "短密"}
    )
    assert resp.status_code == 400


def test_register_blank_nickname(client):
    """昵称为空串：边界值。"""
    resp = client.post(
        "/api/auth/register", json={"username": "nonick", "password": "pass1234", "nickname": ""}
    )
    assert resp.status_code == 400


def test_login_wrong_password(client, make_user):
    """密码错误返回 401，且不透露账号是否存在。"""
    make_user("loginuser")
    resp = client.post(
        "/api/auth/login", json={"username": "loginuser", "password": "wrongpass"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "用户名或密码错误"


def test_login_unknown_user(client):
    """不存在的账号同样返回 401。"""
    resp = client.post("/api/auth/login", json={"username": "ghost", "password": "pass1234"})
    assert resp.status_code == 401


def test_me_without_token(client):
    """未登录访问受保护接口必须 401，而不是 200 或 500。"""
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_invalid_token(client):
    """伪造令牌必须 401。"""
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_me_returns_current_user(client, make_user):
    """带合法令牌能取到本人资料。"""
    headers, user = make_user("whoami", nickname="我是谁")
    resp = client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["nickname"] == "我是谁"
    assert resp.json()["phone"] is None


def test_change_password_flow(client, make_user):
    """改密后旧密码失效、新密码可用。"""
    headers, _ = make_user("pwduser", password="oldpass1")
    changed = client.put(
        "/api/users/me/password",
        headers=headers,
        json={"old_password": "oldpass1", "new_password": "newpass1"},
    )
    assert changed.status_code == 200

    assert client.post(
        "/api/auth/login", json={"username": "pwduser", "password": "oldpass1"}
    ).status_code == 401
    assert client.post(
        "/api/auth/login", json={"username": "pwduser", "password": "newpass1"}
    ).status_code == 200


def test_change_password_wrong_old(client, make_user):
    """原密码错误时不能改密。"""
    headers, _ = make_user("pwduser2", password="oldpass1")
    resp = client.put(
        "/api/users/me/password",
        headers=headers,
        json={"old_password": "badpass1", "new_password": "newpass1"},
    )
    assert resp.status_code == 400


def test_update_profile(client, make_user):
    """修改昵称与手机号后立即生效。"""
    headers, _ = make_user("profuser")
    resp = client.put(
        "/api/users/me", headers=headers, json={"nickname": "新昵称", "phone": "13800000000"}
    )
    assert resp.status_code == 200
    assert resp.json()["nickname"] == "新昵称"
    assert resp.json()["phone"] == "13800000000"


def test_public_profile_hides_phone(client, make_user):
    """他人主页不能泄露手机号，属于隐私字段。"""
    headers, user = make_user("privacyuser")
    client.put("/api/users/me", headers=headers, json={"nickname": "隐私", "phone": "13900000000"})
    public = client.get(f"/api/users/{user['id']}").json()
    assert "phone" not in public


def test_public_profile_not_found(client):
    """查询不存在的用户返回 404。"""
    assert client.get("/api/users/99999").status_code == 404


def test_register_min_boundary_accepted(client):
    """用户名 3 位、密码 6 位、昵称 1 字：全部取最下界，应当注册成功。

    上面几支只验了「下界减一被拒」，如果不补这支，把 min_length 写成 4 或 7
    也不会有用例变红，边界就只测了一半。
    """
    resp = client.post(
        "/api/auth/register",
        json={"username": "abc", "password": "123456", "nickname": "安"},
    )
    assert resp.status_code == 201
    assert resp.json()["username"] == "abc"
    assert client.post(
        "/api/auth/login", json={"username": "abc", "password": "123456"}
    ).status_code == 200


def test_register_username_max_length(client):
    """用户名 50 位是上限（等于列宽），51 位必须被拒。"""
    ok = client.post(
        "/api/auth/register",
        json={"username": "u" * 50, "password": "pass1234", "nickname": "长名"},
    )
    assert ok.status_code == 201
    assert ok.json()["username"] == "u" * 50

    too_long = client.post(
        "/api/auth/register",
        json={"username": "v" * 51, "password": "pass1234", "nickname": "超长"},
    )
    assert too_long.status_code == 400


def test_register_nickname_near_max_length(client):
    """昵称 80 字可用、81 字被拒，且首尾空格被去掉。"""
    ok = client.post(
        "/api/auth/register",
        json={"username": "nick80", "password": "pass1234", "nickname": "  " + "昵" * 80 + "  "},
    )
    assert ok.status_code == 201
    assert ok.json()["nickname"] == "昵" * 80

    too_long = client.post(
        "/api/auth/register",
        json={"username": "nick81", "password": "pass1234", "nickname": "昵" * 81},
    )
    assert too_long.status_code == 400


def test_register_blank_nickname_by_spaces(client):
    """昵称只有空格：长度校验能过，但语义上是空昵称，应按空处理。

    这是纯空白字符串绕过 min_length=1 的典型漏洞，注册与改资料两条入口都要堵。
    """
    resp = client.post(
        "/api/auth/register",
        json={"username": "blanknick", "password": "pass1234", "nickname": "   "},
    )
    assert resp.status_code == 400


def test_login_returns_usable_token(client, make_user):
    """登录返回的 bearer 令牌能直接访问受保护接口，字段与接口文档一致。"""
    make_user("tokenuser")
    body = client.post(
        "/api/auth/login", json={"username": "tokenuser", "password": "pass1234"}
    ).json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["username"] == "tokenuser"
    assert "password_hash" not in body["user"]
    me = client.get("/api/auth/me", headers={"Authorization": "Bearer " + body["access_token"]})
    assert me.status_code == 200


def test_bearer_without_token_rejected(client):
    """只写 `Bearer` 不带令牌属于格式错误，不能落到 500。"""
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer"})
    assert resp.status_code == 401


def test_update_profile_blank_nickname_rejected(client, make_user):
    """改资料时昵称传空格：与注册同一口径，应按空昵称拒绝。"""
    headers, _ = make_user("blankprofile")
    resp = client.put("/api/users/me", headers=headers, json={"nickname": "  "})
    assert resp.status_code == 400


def test_update_profile_phone_too_long(client, make_user):
    """手机号超过 30 字符：属字段边界，应被参数校验拦下。"""
    headers, _ = make_user("phonelong")
    resp = client.put("/api/users/me", headers=headers, json={"nickname": "手机号超长", "phone": "1" * 31})
    assert resp.status_code == 400


def test_update_profile_is_full_replacement(client, make_user):
    """PUT /api/users/me 是全量替换：第二次不带 avatar，头像应被清空。

    与 PUT /api/goods/{id} 保持同一语义，前端「整表提交」才不用区分 PATCH。
    """
    headers, _ = make_user("replaceuser")
    first = client.put("/api/users/me", headers=headers, json={
        "nickname": "有头像", "phone": "13800000001", "avatar": "/static/uploads/a.png"})
    assert first.json()["avatar"] == "/static/uploads/a.png"

    second = client.put("/api/users/me", headers=headers, json={"nickname": "没头像"})
    assert second.status_code == 200
    assert second.json()["avatar"] is None
    assert second.json()["phone"] is None


def test_change_password_new_too_short(client, make_user):
    """新密码 5 位：边界值，不能因为「原密码对」就放行。"""
    headers, _ = make_user("pwdshort", password="oldpass1")
    resp = client.put(
        "/api/users/me/password",
        headers=headers,
        json={"old_password": "oldpass1", "new_password": "12345"},
    )
    assert resp.status_code == 400


def test_change_password_requires_login(client):
    """未登录不能改密，必须 401 而不是 400（先判身份再判字段）。"""
    resp = client.put(
        "/api/users/me/password",
        json={"old_password": "oldpass1", "new_password": "newpass1"},
    )
    assert resp.status_code == 401
