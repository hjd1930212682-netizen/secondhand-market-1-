# Author: 安远
"""生成实验报告与设计文档所需的七张图。

设计约束：图在正文里固定插成 16 cm 宽，约等于 453 磅。
因此画布坐标直接以「磅」为单位（宽 453），字号也按磅写，
这样 8 磅的字插进文档就是 8 磅，不会被缩放成 3 磅而看不清。
画布按 S 倍分辨率绘制后直接输出，保证「一」这类细横线不被冲淡。

fig1_er            数据库 ER 图
fig2_architecture  系统分层架构与下单调用链
fig3_modules       功能模块划分与责任人
fig4_order_state   订单状态机
fig5_flow          核心业务流程图
fig6_usecase       用例图
fig7_gitlog        Git 提交历史（数据取自 git log）

用法：python scripts/make_figures.py
输出：docs/figures/*.png
"""

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "figures"

S = 3  # 渲染倍率：453 磅宽 → 1359 像素，16 cm 下约 216 dpi

FONT_REG = "C:/Windows/Fonts/msyh.ttc"
FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"
FONT_MONO = "C:/Windows/Fonts/consola.ttf"

INK = "#1b2431"
MUTED = "#5b6b7f"
NAVY = "#233b5e"
LINE = "#c3d0e0"

USER_C, GOODS_C, TRADE_C, SOCIAL_C = "#2f6fb3", "#2f9e8f", "#c77d2a", "#8a5fa8"

_font_cache: dict = {}


def font(size: float, bold: bool = False):
    """按字号（磅）取字体；size 为逻辑磅值，内部乘渲染倍率。"""
    key = (round(size, 1), bold)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(FONT_BOLD if bold else FONT_REG, int(round(size * S)))
    return _font_cache[key]


def mono(size: float):
    key = ("mono", round(size, 1))
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(FONT_MONO, int(round(size * S)))
    return _font_cache[key]


class Canvas:
    """以磅为单位的画布：坐标与字号都按磅给，输出时乘 S。"""

    def __init__(self, w, h, bg: str = "#ffffff"):
        w, h = int(round(w)), int(round(h))
        self.W, self.H = w, h
        self.img = Image.new("RGB", (w * S, h * S), bg)
        self.d = ImageDraw.Draw(self.img)

    def rect(self, box, fill="#ffffff", outline=LINE, width=1.0, radius=4):
        x1, y1, x2, y2 = box
        if radius:
            self.d.rounded_rectangle([x1 * S, y1 * S, x2 * S, y2 * S], radius=radius * S,
                                     fill=fill, outline=outline, width=max(1, int(width * S)))
        else:
            self.d.rectangle([x1 * S, y1 * S, x2 * S, y2 * S], fill=fill,
                             outline=outline, width=max(1, int(width * S)))

    def line(self, pts, fill=LINE, width=1.0):
        self.d.line([(x * S, y * S) for x, y in pts], fill=fill, width=max(1, int(width * S)))

    def arrow(self, pts, fill=NAVY, width=1.0, head=4.0):
        """折线箭头，箭头画在最后一个点。"""
        self.line(pts, fill=fill, width=width)
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        dx, dy = x2 - x1, y2 - y1
        n = max((dx * dx + dy * dy) ** 0.5, 1e-6)
        ux, uy = dx / n, dy / n
        px, py = -uy, ux
        tip = (x2 * S, y2 * S)
        left = ((x2 - ux * head + px * head * 0.45) * S, (y2 - uy * head + py * head * 0.45) * S)
        right = ((x2 - ux * head - px * head * 0.45) * S, (y2 - uy * head - py * head * 0.45) * S)
        self.d.polygon([tip, left, right], fill=fill)

    def text(self, xy, s, size=8, bold=False, fill=INK, anchor="la", fnt=None):
        self.d.text((xy[0] * S, xy[1] * S), s, font=fnt or font(size, bold), fill=fill, anchor=anchor)

    def tw(self, s, size=8, bold=False, fnt=None) -> float:
        """文字宽度（磅）。"""
        return (fnt or font(size, bold)).getlength(s) / S

    def fit(self, s, w, size=7.2, bold=False, min_size=5.0) -> tuple[str, float]:
        """在宽度 w 内放不下时逐步缩小字号，仍放不下则截断加省略号。"""
        size_use = size
        while size_use > min_size and self.tw(s, size_use, bold) > w:
            size_use -= 0.2
        while s and self.tw(s, size_use, bold) > w:
            s = s[:-1]
        return s, size_use

    def fit_text(self, x, y, w, s, size=7.2, bold=False, fill=INK, anchor="lm"):
        s2, sz = self.fit(s, w, size, bold)
        self.text((x, y), s2, size=sz, bold=bold, fill=fill, anchor=anchor)

    def save(self, name: str) -> Path:
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / name
        self.img.save(path)
        return path


# ---------------------------------------------------------------- 图 1 ER
def entity(c: Canvas, x: int, y: int, w: int, title: str, color: str,
           fields: list[tuple[str, str, str]]) -> dict:
    """画一张表：彩色表头 + 字段行。fields 为 (字段名, 类型或指向, PK/FK/UK)。"""
    head_h, row_h = 13, 10.2
    h = head_h + row_h * len(fields) + 3
    c.rect((x, y, x + w, y + h), fill="#ffffff", outline="#c9d6e6", width=0.8, radius=3)
    c.d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + head_h) * S], radius=3 * S, fill=color)
    c.d.rectangle([x * S, (y + head_h - 3) * S, (x + w) * S, (y + head_h) * S], fill=color)
    c.fit_text(x + 4, y + head_h / 2 + 0.5, w - 26, title, size=7.2, bold=True, fill="#ffffff")
    for i, (name, note, badge) in enumerate(fields):
        ry = y + head_h + i * row_h + row_h / 2
        c.text((x + 4, ry), name, size=6.6, fill=INK, anchor="lm")
        nx = x + 4 + c.tw(name, 6.6) + 2.5
        if note:
            c.fit_text(nx, ry, w - (nx - x) - 12, note, size=6.0, fill=MUTED)
        if badge:
            c.text((x + w - 4, ry), badge, size=5.6, bold=True, fill=color, anchor="rm")
        if i < len(fields) - 1:
            c.line([(x + 3, y + head_h + (i + 1) * row_h),
                    (x + w - 3, y + head_h + (i + 1) * row_h)], fill="#eef2f8", width=0.5)
    return {"x1": x, "y1": y, "x2": x + w, "y2": y + h}


def rel(c: Canvas, pts, label: str, at: tuple[float, float] | None = None) -> None:
    """画关系线，并在指定位置压一个白底标签。"""
    c.arrow(pts, fill="#a9bacd", width=1.0, head=4.0)
    lx, ly = at or ((pts[0][0] + pts[-1][0]) / 2, (pts[0][1] + pts[-1][1]) / 2)
    w = c.tw(label, 6.0) + 4
    c.rect((lx - w / 2, ly - 4.4, lx + w / 2, ly + 4.4), fill="#ffffff", outline="#ffffff",
           width=0, radius=0)
    c.text((lx, ly), label, size=6.0, fill="#4d6a8c", anchor="mm")


def build_er() -> Path:
    """第一张图：七张表的 ER 图。字段后的 → 表示外键。"""
    c = Canvas(453, 472)

    entity(c, 6, 8, 134, "users 用户", USER_C, [
        ("id", "int", "PK"), ("username", "varchar(50)", "UK"),
        ("password_hash", "varchar(255)", ""), ("nickname", "varchar(80)", ""),
        ("avatar", "varchar(255)", ""), ("phone", "varchar(30)", ""),
        ("credit_score", "int", ""), ("created_at", "datetime", ""),
    ])
    entity(c, 6, 118, 134, "favorites 收藏", SOCIAL_C, [
        ("id", "int", "PK"), ("user_id", "→users", "FK"),
        ("goods_id", "→goods", "FK"), ("created_at", "datetime", ""),
    ])
    entity(c, 6, 190, 134, "categories 分类", GOODS_C, [
        ("id", "int", "PK"), ("name", "varchar(80)", ""),
        ("parent_id", "→categories", "FK"),
    ])

    entity(c, 250, 8, 134, "goods 商品", GOODS_C, [
        ("id", "int", "PK"), ("seller_id", "→users", "FK"),
        ("category_id", "→categories", "FK"), ("title", "varchar(160)", ""),
        ("price", "decimal", ""), ("images", "text", ""),
        ("status", "在售/已售/下架", ""), ("view_count", "int", ""),
        ("created_at", "datetime", ""),
    ])
    entity(c, 250, 138, 134, "orders 订单", TRADE_C, [
        ("id", "int", "PK"), ("order_no", "varchar(40)", "UK"),
        ("goods_id", "→goods", "FK"), ("buyer_id", "→users", "FK"),
        ("seller_id", "→users", "FK"), ("price", "decimal", ""),
        ("status", "四态", ""), ("created_at", "datetime", ""),
        ("finished_at", "datetime", ""),
    ])
    entity(c, 250, 264, 134, "reviews 评价", SOCIAL_C, [
        ("id", "int", "PK"), ("order_id", "→orders", "FK"),
        ("reviewer_id", "→users", "FK"), ("target_id", "→users", "FK"),
        ("rating", "tinyint 1~5", ""), ("content", "text", ""),
        ("created_at", "datetime", ""),
    ])
    entity(c, 250, 374, 134, "messages 站内消息", SOCIAL_C, [
        ("id", "int", "PK"), ("sender_id", "→users", "FK"),
        ("receiver_id", "→users", "FK"), ("goods_id", "→goods", "FK"),
        ("content", "text", ""), ("is_read", "tinyint(1)", ""),
    ])

    # 关系线：由「1」端指向「N」端，标签写明业务动作与基数
    # 每条关系进入 goods / orders 左侧的落点各不相同，避免两支箭头叠在一点
    rel(c, [(140, 24), (250, 24)], "发布 1:N", (195, 18))
    rel(c, [(140, 88), (196, 88), (196, 172), (250, 172)], "买家下单 / 卖家接单 1:N", (196, 152))
    rel(c, [(73, 106), (73, 118)], "收藏", (85, 112))
    rel(c, [(140, 112), (170, 112), (170, 70), (250, 70)], "被收藏 1:N", (206, 64))
    rel(c, [(140, 206), (225, 206), (225, 100), (250, 100)], "归类 1:N", (180, 200))
    rel(c, [(317, 126), (317, 138)], "成交", (331, 132))
    rel(c, [(317, 250), (317, 264)], "一单一评 1:1", (352, 257))
    rel(c, [(140, 104), (236, 104), (236, 298), (250, 298)], "评价 1:N", (236, 344))

    c.text((6, 455), "说明：字段后的 → 表示外键指向的表；PK 主键、FK 外键、UK 唯一键；"
                     "14 条外键全部在 MySQL 中建成真实约束。",
           size=6.4, fill=MUTED, anchor="ls")
    c.text((6, 466), "为免连线交叉，messages 指向 users 与 goods 的三条外键只以字段标注表示。",
           size=6.4, fill=MUTED, anchor="ls")
    return c.save("fig1_er.png")


# ------------------------------------------------------------ 图 2 架构
def band(c: Canvas, y: int, h: int, name: str, note: str, color: str) -> None:
    c.rect((6, y, 447, y + h), fill="#f8fafd", outline="#dde5ef", width=0.8, radius=5)
    c.d.rounded_rectangle([6 * S, y * S, 72 * S, (y + h) * S], radius=5 * S, fill=color)
    c.d.rectangle([60 * S, y * S, 72 * S, (y + h) * S], fill=color)
    c.text((13, y + h / 2 - 5), name, size=8.4, bold=True, fill="#ffffff", anchor="lm")
    c.text((13, y + h / 2 + 6), note, size=6.0, fill="#e6eefa", anchor="lm")


def box(c: Canvas, x: int, y: int, w: int, h: int, name: str, note: str = "",
        size: float = 7.0) -> None:
    c.rect((x, y, x + w, y + h), fill="#ffffff", outline="#cfdae8", width=0.8, radius=4)
    if note:
        c.fit_text(x + 4, y + h / 2 - 4.6, w - 8, name, size=size, bold=True)
        c.fit_text(x + 4, y + h / 2 + 5.0, w - 8, note, size=6.0, fill=MUTED)
    else:
        c.fit_text(x + 4, y + h / 2, w - 8, name, size=size)


def build_architecture() -> Path:
    """第二张图：三层架构 + 一次下单请求的调用链。"""
    c = Canvas(453, 424)

    band(c, 6, 62, "表现层", "浏览器 14 页", USER_C)
    box(c, 78, 13, 118, 22, "列表 / 详情 / 发布", "", 6.8)
    box(c, 78, 39, 118, 22, "登录 / 注册 / 个人中心", "", 6.8)
    box(c, 202, 13, 118, 22, "api.js 请求封装", "Bearer 令牌 · 401 跳转")
    box(c, 202, 39, 118, 22, "common.js 公共组件", "导航 · toast · 分页")
    box(c, 326, 13, 115, 22, "style.css 样式", "三档响应式断点")
    box(c, 326, 39, 115, 22, "pages.js 页面逻辑", "按 data-page 分发")

    band(c, 76, 62, "业务层", "FastAPI", GOODS_C)
    box(c, 78, 83, 118, 22, "路由层 routers", "参数校验 · 依赖注入")
    box(c, 202, 83, 118, 22, "服务层 services", "业务规则 · 事务边界")
    box(c, 326, 83, 115, 22, "order_state.py", "六条状态转移")
    box(c, 78, 109, 118, 22, "schemas 模型", "请求 / 响应校验")
    box(c, 202, 109, 118, 22, "core 鉴权与异常", "JWT · 统一错误码")
    box(c, 326, 109, 115, 22, "deps 依赖", "取当前用户")

    band(c, 146, 50, "数据层", "SQLAlchemy", TRADE_C)
    box(c, 78, 154, 180, 34, "ORM 模型：七张表", "14 条外键 · 软删除")
    box(c, 266, 154, 175, 34, "MySQL 8.0（InnoDB）", "utf8mb4 · 行锁 · 唯一索引")

    for y1, y2, label in [(68, 76, "HTTP 同源"), (138, 146, "Session / SQL")]:
        c.arrow([(226, y1), (226, y2)], fill="#9fb2c9", width=0.9, head=3.2)
        c.text((230, (y1 + y2) / 2), label, size=5.8, fill=MUTED, anchor="lm")

    c.text((6, 208), "一次「立即购买」请求的十步调用链", size=7.4, bold=True, fill=NAVY, anchor="lm")
    steps = [
        ("1", "点击立即购买", "pages.js 取 goods_id"),
        ("2", "POST /api/orders", "api.js 加 Bearer 令牌"),
        ("3", "中间件", "记录方法、路径、耗时"),
        ("4", "解析令牌", "deps 校验签名与过期"),
        ("5", "路由转服务", "create_order 接管校验"),
        ("6", "开启事务加锁", "SELECT … FOR UPDATE"),
        ("7", "校验商品状态", "非在售直接返回 409"),
        ("8", "建单并改商品", "同一事务内提交"),
        ("9", "presenter 组装", "附 available_actions"),
        ("10", "浏览器渲染", "按钮由接口决定"),
    ]
    for i, (no, name, note) in enumerate(steps):
        col, row = divmod(i, 5)
        x = 6 + col * 224
        y = 220 + row * 36
        c.d.ellipse([(x + 1) * S, (y + 6) * S, (x + 15) * S, (y + 20) * S], fill=NAVY)
        c.text((x + 8, y + 13), no, size=6.2, bold=True, fill="#ffffff", anchor="mm")
        c.fit_text(x + 19, y + 8, 200, name, size=7.0, bold=True)
        c.fit_text(x + 19, y + 19, 200, note, size=6.0, fill=MUTED)

    c.text((6, 418), "说明：路由层不写业务判断，状态转移只在 order_state.py 一张表里定义；"
                     "前端按钮完全由接口返回的 available_actions 决定。",
           size=6.4, fill=MUTED, anchor="ls")
    return c.save("fig2_architecture.png")


# ---------------------------------------------------------- 图 3 模块图
def build_modules() -> Path:
    """第三张图：功能模块与责任人，叶子模块两列排布。"""
    groups = [
        ("账号与鉴权", "王昱皓", USER_C,
         ["注册与登录", "JWT 会话保持", "个人资料修改", "头像上传", "密码修改"]),
        ("商品模块", "杨云凇", GOODS_C,
         ["发布商品（多图）", "编辑与软删除", "上架 / 下架", "关键词搜索", "分类筛选与排序", "我的商品管理"]),
        ("交易模块", "郝津德", TRADE_C,
         ["下单防超卖", "订单状态机", "订单列表与详情", "取消与退款"]),
        ("互动模块", "郝津德 / 安远", SOCIAL_C,
         ["站内消息会话", "未读数提醒", "商品收藏", "买家评价卖家", "评分统计"]),
        ("平台支撑", "郝津德", "#4d7f9c",
         ["配置与数据库连接", "ORM 与建库脚本", "统一异常与日志", "图片上传服务", "健康检查", "初始化与打包"]),
        ("前端公共层", "王昱皓", "#2f8f9e",
         ["api.js 统一请求", "common.js 导航", "style.css 变量", "十四页响应式"]),
        ("质量保障", "安远", "#8a5fa8",
         ["110 项 pytest 用例", "并发下单验证", "Bug 追踪表", "接口与文档核对"]),
    ]

    row_h, pad, gap = 11.5, 6, 6
    heights = [max(24, -(-len(lv) // 2) * row_h + pad * 2) for _, _, _, lv in groups]
    stack = sum(heights) + gap * (len(groups) - 1)
    total = 8 + stack + 22
    c = Canvas(453, total)

    root_h = 28
    root_y = 8 + (stack - root_h) / 2
    c.rect((6, root_y, 96, root_y + root_h), fill=NAVY, outline=NAVY, width=0.8, radius=4)
    c.fit_text(12, root_y + root_h / 2 - 4.6, 80, "校园二手交易", size=7.4, bold=True, fill="#ffffff")
    c.fit_text(12, root_y + root_h / 2 + 4.6, 80, "交易平台", size=7.4, bold=True, fill="#ffffff")

    y = 8
    spine = []
    for (name, owner, color, leaves), h in zip(groups, heights):
        c.rect((112, y, 212, y + h), fill="#ffffff", outline=color, width=1.0, radius=4)
        c.d.rounded_rectangle([112 * S, y * S, 116 * S, (y + h) * S], radius=2 * S, fill=color)
        c.fit_text(122, y + h / 2 - 4.6, 86, name, size=7.2, bold=True)
        c.fit_text(122, y + h / 2 + 4.8, 86, owner, size=6.0, fill=color)
        spine.append(y + h / 2)

        for i, leaf in enumerate(leaves):
            row, col = divmod(i, 2)
            lx = 222 + col * 113
            ly = y + pad + row * row_h
            c.rect((lx, ly, lx + 108, ly + 10.4), fill="#ffffff", outline="#d7e0ec", width=0.6, radius=2)
            c.fit_text(lx + 3, ly + 5.2, 101, leaf, size=6.2)
            c.line([(lx - 5, ly + 5.2), (lx, ly + 5.2)], fill=LINE, width=0.7)
        # 叶子分叉用一条竖向干线，避免每片叶子各自挂一段断头线
        rows_n = -(-len(leaves) // 2)
        centers = [y + pad + r * row_h + 5.2 for r in range(rows_n)]
        c.line([(217, min(centers)), (217, max(centers))], fill=LINE, width=0.7)
        c.line([(212, y + h / 2), (217, y + h / 2)], fill=LINE, width=0.7)
        y += h + gap

    c.line([(102, root_y + root_h / 2), (107, root_y + root_h / 2)], fill=NAVY, width=1.0)
    c.line([(107, spine[0]), (107, spine[-1])], fill=NAVY, width=1.0)
    for cy in spine:
        c.arrow([(107, cy), (112, cy)], fill=NAVY, width=1.0, head=3.2)
    for cy in spine:
        c.line([(212, cy), (217, cy)], fill=LINE, width=0.7)

    c.text((6, total - 4), "说明：负责人口径与《分工说明》一致；同一模块出现两人时为共同承担，"
                           "消息与收藏归郝津德，买家评价与评分统计归安远。",
           size=6.4, fill=MUTED, anchor="ls")
    return c.save("fig3_modules.png")


# -------------------------------------------------------- 图 4 状态机图
def build_state() -> Path:
    """第四张图：订单状态机，六条合法转移（当前状态 + 目标状态 + 角色）。"""
    c = Canvas(453, 286)

    def state(x, y, w, name, cn, color):
        c.rect((x, y, x + w, y + 26), fill="#ffffff", outline=color, width=1.2, radius=4)
        c.d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + 5) * S], radius=3 * S, fill=color)
        c.fit_text(x + w / 2, y + 10.5, w - 6, name, size=7.2, bold=True, anchor="mm")
        c.fit_text(x + w / 2, y + 20.5, w - 6, cn, size=6.2, fill=MUTED, anchor="mm")

    state(10, 120, 92, "PENDING", "待确认", "#b03a48")
    state(176, 30, 104, "PAID_PENDING", "待付款", "#2f4b7c")
    state(330, 30, 104, "COMPLETED", "已完成", "#2f6fb3")
    state(176, 208, 104, "CANCELLED", "已取消", "#5b6b7f")

    def label(x, y, text, sub=""):
        w = max(c.tw(text, 6.2, True), c.tw(sub, 5.8)) + 5
        h = 14 if sub else 8.4
        c.rect((x - w / 2, y - h / 2, x + w / 2, y + h / 2), fill="#ffffff",
               outline="#e6ecf5", width=0.6, radius=2)
        c.text((x, y - 3.2 if sub else y), text, size=6.2, bold=True, fill=INK, anchor="mm")
        if sub:
            c.text((x, y + 4.4), sub, size=5.8, fill=MUTED, anchor="mm")

    c.arrow([(102, 128), (176, 48)], fill=NAVY, width=0.9, head=3.6)
    label(122, 84, "确认出售", "卖家")

    c.arrow([(102, 142), (176, 216)], fill=NAVY, width=0.9, head=3.6)
    label(116, 184, "拒绝 / 撤销", "卖家 / 买家")

    c.arrow([(280, 43), (330, 43)], fill=NAVY, width=0.9, head=3.6)
    label(305, 36, "确认收货", "买家")

    c.arrow([(228, 56), (228, 208)], fill=NAVY, width=0.9, head=3.6)
    label(256, 138, "取消订单", "买家")

    c.arrow([(382, 56), (382, 221), (280, 221)], fill=NAVY, width=0.9, head=3.6)
    label(404, 142, "申请退款", "买家")

    c.text((10, 184), "越权操作返回 403，", size=6.2, fill=MUTED)
    c.text((10, 194), "非法流转返回 409。", size=6.2, fill=MUTED)

    c.text((300, 176), "商品状态联动", size=7.0, bold=True, fill=NAVY)
    c.text((300, 188), "· 下单：商品置为已售", size=6.2, fill=MUTED)
    c.text((300, 198), "· 取消 / 退款：商品回「在售」", size=6.2, fill=MUTED)

    c.text((6, 278), "说明：起点为买家下单；「已完成」只能申请退款，不再回到「在售」——"
                     "交易已实际发生，回退会让同一件物品被卖两次。",
           size=6.4, fill=MUTED, anchor="ls")
    return c.save("fig4_order_state.png")


# -------------------------------------------------------- 图 5 流程图
ROLE_COLOR = {"买家": "#2f6fb3", "卖家": "#c77d2a", "系统": "#5b6b7f"}


def build_flow() -> Path:
    """第五张图：核心业务流程图，向右为失败分支。"""
    c = Canvas(453, 422)

    x1, w, h, pitch = 6, 248, 34, 44
    cx = x1 + w / 2

    def step(y, role, text, no):
        color = ROLE_COLOR[role]
        c.rect((x1, y, x1 + w, y + h), fill="#ffffff", outline=color, width=1.0, radius=3)
        c.d.rounded_rectangle([x1 * S, y * S, (x1 + 4) * S, (y + h) * S], radius=2 * S, fill=color)
        c.text((x1 + 13, y + h / 2), str(no), size=7.4, bold=True, fill=color, anchor="mm")
        c.text((x1 + 23, y + h / 2 - 5.2), role, size=6.2, bold=True, fill=color, anchor="lm")
        c.fit_text(x1 + 23, y + h / 2 + 5.4, w - 30, text, size=7.0)

    def diamond(y, text):
        hw, hh = 96, 20
        cy = y + hh
        c.d.polygon([(cx * S, y * S), ((cx + hw) * S, cy * S),
                     (cx * S, (y + 2 * hh) * S), ((cx - hw) * S, cy * S)],
                    fill="#fdf3f3", outline="#b03a48", width=max(1, int(1.0 * S)))
        c.text((cx, cy), text, size=7.0, bold=True, fill="#8c2f3a", anchor="mm")
        return cy

    def aside(cy, lines):
        bx = 352
        c.line([(cx + hw_ref, cy), (bx, cy)], fill="#b03a48", width=1.0)
        c.text((cx + hw_ref + 3, cy - 12), "否", size=6.2, bold=True, fill="#b03a48")
        hh = 7 + 10 * len(lines)
        c.rect((bx, cy - hh / 2, 447, cy + hh / 2), fill="#fdf3f3", outline="#e2b7bc",
               width=0.8, radius=3)
        for i, ln in enumerate(lines):
            c.fit_text(bx + 4, cy - hh / 2 + 8 + i * 10, 90, ln, size=6.0,
                       bold=(i == 0), fill="#8c2f3a" if i == 0 else MUTED)

    hw_ref = 96
    y = [8 + pitch * i for i in range(9)]
    step(y[0], "卖家", "发布商品：分类、标题、价格、传图", 1)
    step(y[1], "系统", "写 goods 表，状态「在售」", 2)
    step(y[2], "买家", "浏览：关键词、分类、价格排序", 3)
    step(y[3], "买家", "打开详情，点「立即购买」", 4)
    step(y[4], "系统", "开启事务：FOR UPDATE 锁商品行", 5)
    d1 = diamond(y[5], "在售且非自购？")
    aside(d1, ["409 商品已被抢购", "400 不能买自己发布的商品", "回滚，商品仍在售"])
    step(y[6], "系统", "建单「待确认」，商品置「已售」", 6)
    d2 = diamond(y[7], "卖家确认出售？")
    aside(d2, ["403 非卖家本人无权操作", "取消：拒绝或买家撤销", "商品回「在售」"])
    step(y[8], "买家", "线下付款 → 确认收货 → 评价", 7)

    for i in range(4):
        c.arrow([(cx, y[i] + h), (cx, y[i + 1])], fill=NAVY, width=0.9, head=3.4)
    c.arrow([(cx, y[4] + h), (cx, y[5])], fill=NAVY, width=0.9, head=3.4)
    c.arrow([(cx, d1 + 20), (cx, y[6])], fill=NAVY, width=0.9, head=3.4)
    c.text((cx - 6, (d1 + 20 + y[6]) / 2 + 1), "是", size=6.2, fill=MUTED, anchor="rm")
    c.arrow([(cx, y[6] + h), (cx, y[7])], fill=NAVY, width=0.9, head=3.4)
    c.arrow([(cx, d2 + 20), (cx, y[8])], fill=NAVY, width=0.9, head=3.4)
    c.text((cx - 6, (d2 + 20 + y[8]) / 2 + 1), "是", size=6.2, fill=MUTED, anchor="rm")

    for i, role in enumerate(("买家", "卖家", "系统")):
        yy = 96 + i * 11
        c.d.rounded_rectangle([352 * S, yy * S, 356 * S, (yy + 4) * S], radius=1 * S,
                              fill=ROLE_COLOR[role])
        c.text((359, yy + 2), f"{role}的动作", size=6.0, fill=MUTED, anchor="lm")
    c.text((352, 84), "图例", size=6.4, bold=True, fill=NAVY, anchor="lm")

    c.text((6, 414), "说明：主流程七个节点，其中三个由系统（含事务）完成；"
                     "两个判断节点决定交易能否继续。",
           size=6.4, fill=MUTED, anchor="ls")
    return c.save("fig5_flow.png")


# -------------------------------------------------------- 图 6 用例图
def actor(c: Canvas, x: float, y: float, label: str, color: str = NAVY) -> None:
    """画 UML 火柴人，(x, y) 为躯干中心。"""
    c.d.ellipse([(x - 4) * S, (y - 15) * S, (x + 4) * S, (y - 7) * S],
                outline=color, width=max(1, int(0.9 * S)))
    c.line([(x, y - 7), (x, y + 3)], fill=color, width=0.9)
    c.line([(x - 7, y - 3), (x + 7, y - 3)], fill=color, width=0.9)
    c.line([(x, y + 3), (x - 6, y + 12)], fill=color, width=0.9)
    c.line([(x, y + 3), (x + 6, y + 12)], fill=color, width=0.9)
    c.text((x, y + 18), label, size=6.6, bold=True, fill=color, anchor="mm")


def build_usecase() -> Path:
    """第六张图：用例图，游客、买家、卖家三个角色与用例的对应关系。"""
    c = Canvas(453, 292)

    c.rect((52, 40, 400, 274), fill="#fbfcfe", outline="#b9c8da", width=0.9, radius=5)
    c.text((58, 48), "校园二手交易平台", size=7.0, bold=True, fill=NAVY, anchor="lm")

    ew, eh = 96, 18
    rows = [60 + 30 * i for i in range(7)]
    cols = {1: 62, 2: 178, 3: 294}

    def uc(col, row, text):
        x, y = cols[col], rows[row]
        c.d.ellipse([x * S, y * S, (x + ew) * S, (y + eh) * S],
                    fill="#eef3fa", outline="#2f4b7c", width=max(1, int(0.8 * S)))
        c.fit_text(x + ew / 2, y + eh / 2, ew - 14, text, size=6.2, anchor="mm")
        return x, y + eh / 2

    buyer = ["浏览与搜索商品", "收藏商品", "下单购买", "确认收货",
             "取消订单 / 退款", "站内私信卖家", "评价卖家"]
    seller = ["发布商品", "编辑与上下架", "确认出售 / 拒绝", "查看我的商品"]

    ab, as_ = (24, 168), (430, 150)
    for i, name in enumerate(buyer):
        left, cy = uc(1, i, name)
        c.line([ab, (left, cy)], fill="#cdd8e6", width=0.7)
    actor(c, *ab, "买家")

    for i, name in enumerate(seller):
        left, cy = uc(3, i, name)
        c.line([as_, (left + ew, cy)], fill="#cdd8e6", width=0.7)
    actor(c, *as_, "卖家")

    uc(2, 2, "注册与登录")
    actor(c, 226, 22, "")
    c.text((236, 19), "游客", size=6.6, bold=True, fill=NAVY, anchor="lm")
    c.arrow([(226, 30), (226, rows[2] - 1)], fill="#cdd8e6", width=0.7, head=3.2)

    c.text((6, 294), "说明：三个角色不是三套账号，同一账号按订单上下文判定身份；"
                     "未登录只能浏览与搜索。",
           size=6.4, fill=MUTED, anchor="ls")
    return c.save("fig6_usecase.png")


# ------------------------------------------------------ 图 7 提交历史
AUTHOR_COLOR = {"郝津德": "#7fb2f0", "王昱皓": "#6fd6c4", "杨云凇": "#f0b46a", "安远": "#c8a2e8"}


def build_gitlog() -> Path:
    """第七张图：按 git log 真实输出渲染最近 18 条提交。"""
    fmt = "%h%x09%ad%x09%an%x09%s"
    raw = subprocess.run(
        ["git", "log", f"--pretty=format:{fmt}", "--date=format:%m-%d", "-18"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip().splitlines()
    total = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True, check=True).stdout.strip()

    c = Canvas(453, 300, bg="#eef2f8")
    c.rect((4, 4, 449, 296), fill="#1e2430", outline="#38414f", width=0.8, radius=5)
    c.d.rounded_rectangle([4 * S, 4 * S, 449 * S, 20 * S], radius=5 * S, fill="#2b3342")
    c.d.rectangle([4 * S, 14 * S, 449 * S, 20 * S], fill="#2b3342")
    for i, col in enumerate(("#e06c6c", "#e0c06c", "#6ec08a")):
        c.d.ellipse([(12 + i * 8) * S, 9 * S, (17 + i * 8) * S, 14 * S], fill=col)
    c.text((226, 12), "git log --oneline --graph -18", size=6.2, fill="#c9d3e0",
           anchor="mm", fnt=mono(6.2))

    c.text((12, 26), "PS D:\\secondhand-market> git log --oneline --graph -18", size=6.2,
           fill="#9fe0a8", fnt=mono(6.2))
    c.text((12, 36), f"共 {total} 次提交 · 4 位作者 · main 与 origin/main 同步", size=6.0,
           fill="#7f8ea3")

    y = 48
    for line in raw:
        parts = line.split("\t")
        if len(parts) != 4:
            continue
        sha, date, author, msg = parts
        c.text((12, y), "*", size=6.2, fill="#9fe0a8", fnt=mono(6.2))
        c.text((20, y), sha, size=6.0, fill="#e0c07a", fnt=mono(6.0))
        c.text((48, y), date, size=6.0, fill="#7f8ea3", fnt=mono(6.0))
        c.text((72, y), author, size=6.2, fill=AUTHOR_COLOR.get(author, "#c9d3e0"))
        c.text((98, y), msg, size=6.2, fill="#dbe3ee")
        y += 12.6

    c.text((12, y + 4), "（灰：日期　黄：短哈希　彩色：提交人　白：提交说明）", size=5.8,
           fill="#7f8ea3")
    return c.save("fig7_gitlog.png")


if __name__ == "__main__":
    for f in (build_er(), build_architecture(), build_modules(), build_state(),
              build_flow(), build_usecase(), build_gitlog()):
        print(f"已生成 {f.relative_to(ROOT)}")
