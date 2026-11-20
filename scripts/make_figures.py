# Author: 安远
"""生成设计文档所需的四张图：ER 图、系统架构图、功能模块图、订单状态机图。

用法：python scripts/make_figures.py
输出：docs/figures/fig1_er.png、fig2_architecture.png、fig3_modules.png、fig4_order_state.png
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "figures"
S = 2  # 2 倍绘制后缩小，边缘更平滑

FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"
FONT_REG = "C:/Windows/Fonts/msyh.ttc"

INK = "#1b2431"
MUTED = "#5b6b7f"
LINE = "#9aabc0"
NAVY = "#2f4b7c"
PALE = "#eef3fa"

# 四位成员的标识色，模块图与分工表共用
OWNER_COLOR = {
    "郝津德": "#2f6fb3",
    "王昱皓": "#2f9e8f",
    "杨云凇": "#c77d2a",
    "安远": "#8a5fa8",
}

_font_cache: dict = {}


def font(size: int, bold: bool = False):
    """按字号取字体，带缓存；size 为逻辑像素。"""
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size * S)
    return _font_cache[key]


class Canvas:
    """按逻辑坐标绘制的画布，内部放大 S 倍后缩回，得到平滑边缘。"""

    def __init__(self, w: int, h: int, bg: str = "#ffffff") -> None:
        self.W, self.H = w, h
        self.img = Image.new("RGB", (w * S, h * S), bg)
        self.d = ImageDraw.Draw(self.img)

    def _box(self, xy):
        x1, y1, x2, y2 = xy
        return [x1 * S, y1 * S, x2 * S, y2 * S]

    def rect(self, xy, fill="#ffffff", outline=LINE, width=1, radius=8):
        """画圆角矩形，坐标按逻辑像素给出。"""
        self.d.rounded_rectangle(self._box(xy), radius=radius * S, fill=fill,
                                 outline=outline, width=max(1, int(width * S)))

    def text(self, xy, s, size=14, bold=False, fill=INK, anchor="la"):
        """在逻辑坐标处写字。"""
        self.d.text((xy[0] * S, xy[1] * S), s, font=font(size, bold), fill=fill, anchor=anchor)

    def line(self, pts, fill=LINE, width=1.4):
        """画折线，pts 为逻辑坐标点列表。"""
        self.d.line([(x * S, y * S) for x, y in pts], fill=fill,
                    width=max(1, int(width * S)), joint="curve")

    def arrow(self, pts, fill=LINE, width=1.6, head=9):
        """画带箭头的折线，箭头落在最后一段末端。"""
        self.line(pts, fill=fill, width=width)
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        dx, dy = x2 - x1, y2 - y1
        length = (dx * dx + dy * dy) ** 0.5 or 1
        ux, uy = dx / length, dy / length
        px, py = -uy, ux
        tip = (x2 * S, y2 * S)
        left = ((x2 - ux * head + px * head * 0.45) * S, (y2 - uy * head + py * head * 0.45) * S)
        right = ((x2 - ux * head - px * head * 0.45) * S, (y2 - uy * head - py * head * 0.45) * S)
        self.d.polygon([tip, left, right], fill=fill)

    def badge(self, cx, cy, s, fill=NAVY, fg="#ffffff", r=11, size=12):
        """画圆形标记，用于联系基数与序号。"""
        self.d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=fill)
        self.text((cx, cy), s, size=size, bold=True, fill=fg, anchor="mm")

    def save(self, name: str) -> Path:
        """缩回逻辑尺寸并保存；返回文件路径。"""
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / name
        self.img.resize((self.W, self.H), Image.LANCZOS).save(path)
        return path


def title_bar(c: Canvas, text: str, sub: str = "") -> None:
    """在左上角写图题，右侧可选副标题。"""
    c.text((40, 34), text, size=22, bold=True, fill=NAVY)
    if sub:
        c.text((c.W - 40, 42), sub, size=13, fill=MUTED, anchor="ra")


def entity(c: Canvas, x: int, y: int, w: int, name: str, color: str,
           rows: list[tuple[str, str, str]]) -> dict:
    """画一张实体表并返回其矩形；rows 每项为（字段, 类型, 键标记）。"""
    head = 40
    rh = 26
    h = head + len(rows) * rh + 12
    c.rect((x, y, x + w, y + h), fill="#ffffff", outline=color, width=1.6, radius=10)
    c.d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + head) * S],
                          radius=10 * S, fill=color)
    c.d.rectangle([x * S, (y + head - 12) * S, (x + w) * S, (y + head) * S], fill=color)
    c.text((x + 16, y + head / 2), name, size=15, bold=True, fill="#ffffff", anchor="lm")
    c.text((x + w - 16, y + head / 2), f"{len(rows)} 字段", size=11,
           fill="#e8eef8", anchor="rm")
    for i, (col, typ, key) in enumerate(rows):
        ty = y + head + 8 + i * rh
        c.text((x + 16, ty + rh / 2), col, size=13, bold=bool(key == "PK"), fill=INK, anchor="lm")
        c.text((x + 152, ty + rh / 2), typ, size=11, fill=MUTED, anchor="lm")
        if key:
            badge_color = {"PK": "#b03a48", "FK": "#2f6fb3", "UK": "#5a8f3c"}.get(key, MUTED)
            c.d.rounded_rectangle([(x + w - 48) * S, (ty + 5) * S, (x + w - 14) * S, (ty + 21) * S],
                                  radius=4 * S, fill=badge_color)
            c.text((x + w - 31, ty + rh / 2), key, size=10, bold=True, fill="#ffffff", anchor="mm")
    return {"x1": x, "y1": y, "x2": x + w, "y2": y + h, "cx": x + w / 2, "cy": y + h / 2}


def anchor(box: dict, side: str, slot: float = 0.5) -> tuple[float, float]:
    """取矩形某条边上的连接点；slot 为沿边的比例位置。"""
    if side == "L":
        return (box["x1"], box["y1"] + (box["y2"] - box["y1"]) * slot)
    if side == "R":
        return (box["x2"], box["y1"] + (box["y2"] - box["y1"]) * slot)
    if side == "T":
        return (box["x1"] + (box["x2"] - box["x1"]) * slot, box["y1"])
    return (box["x1"] + (box["x2"] - box["x1"]) * slot, box["y2"])


def _shift(p, q, dist: float = 13) -> tuple[float, float]:
    """把点 p 沿 p→q 方向挪 dist，避免基数标记压在实体边框上。"""
    dx, dy = q[0] - p[0], q[1] - p[1]
    length = (dx * dx + dy * dy) ** 0.5 or 1
    return (p[0] + dx / length * dist, p[1] + dy / length * dist)


def _label_point(pts, ratio: float = 0.45, offset: float = 16):
    """沿折线按长度取比例点，并沿法向偏移，用于把标签贴在自己的连线上。"""
    segs = [((pts[i][0], pts[i][1]), (pts[i + 1][0], pts[i + 1][1])) for i in range(len(pts) - 1)]
    spans = [(((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5) for a, b in segs]
    total = sum(spans) or 1
    target = total * ratio
    for (a, b), ln in zip(segs, spans):
        if target <= ln or (a, b) == segs[-1]:
            t = (target / ln) if ln else 0
            px, py = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            ux, uy = (b[0] - a[0]) / ln, (b[1] - a[1]) / ln
            nx, ny = -uy, ux
            if ny > 0 or (abs(ny) < 1e-6 and nx > 0):
                nx, ny = -nx, -ny
            return (px + nx * offset, py + ny * offset)
        target -= ln
    return pts[0]


def relation(c: Canvas, pts, one_at: str = "start", label: str = "", ratio: float = 0.45,
             color: str = LINE) -> None:
    """画一条联系线，两端标 1 与 N；label 写在 label_at 附近。"""
    c.arrow(pts, fill=color)
    start, end = pts[0], pts[-1]
    s_pt = _shift(start, pts[1])
    e_pt = _shift(end, pts[-2])
    if one_at == "start":
        c.badge(s_pt[0], s_pt[1], "1", fill="#ffffff", fg=color, r=9, size=11)
        c.badge(e_pt[0], e_pt[1], "N", fill=color, fg="#ffffff", r=9, size=11)
    else:
        c.badge(e_pt[0], e_pt[1], "1", fill="#ffffff", fg=color, r=9, size=11)
        c.badge(s_pt[0], s_pt[1], "N", fill=color, fg="#ffffff", r=9, size=11)
    if label:
        lx, ly = _label_point(pts, ratio, 18)
        tw = font(12).getlength(label) / S
        c.d.rounded_rectangle([(lx - tw / 2 - 6) * S, (ly - 10) * S, (lx + tw / 2 + 6) * S, (ly + 10) * S],
                              radius=5 * S, fill="#ffffff", outline="#dde5ef")
        c.text((lx, ly), label, size=12, fill=MUTED, anchor="mm")


def build_er() -> Path:
    """第一张图：七张表的 ER 图，标注主键、外键与联系基数。"""
    c = Canvas(1840, 1210)
    title_bar(c, "图 1　数据库实体联系图（ER）", "七张表 / 14 个外键约束 / 联系基数已标注")

    user_c, goods_c, trade_c, social_c = "#2f6fb3", "#2f9e8f", "#c77d2a", "#8a5fa8"

    favorites = entity(c, 120, 60, 340, "favorites 收藏", social_c, [
        ("id", "int PK", "PK"), ("user_id", "int →users", "FK"),
        ("goods_id", "int →goods", "FK"), ("created_at", "datetime", ""),
    ])
    categories = entity(c, 120, 470, 340, "categories 分类", goods_c, [
        ("id", "int PK", "PK"), ("name", "varchar(80)", ""),
        ("parent_id", "int →categories", "FK"),
    ])
    users = entity(c, 620, 60, 380, "users 用户", user_c, [
        ("id", "int PK", "PK"), ("username", "varchar(50)", "UK"),
        ("password_hash", "varchar(255)", ""), ("nickname", "varchar(80)", ""),
        ("avatar", "varchar(255)", ""), ("phone", "varchar(30)", ""),
        ("credit_score", "int 默认100", ""), ("created_at", "datetime", ""),
    ])
    goods = entity(c, 620, 470, 380, "goods 商品", goods_c, [
        ("id", "int PK", "PK"), ("seller_id", "int →users", "FK"),
        ("category_id", "int →categories", "FK"), ("title", "varchar(160)", ""),
        ("price", "decimal(10,2)", ""), ("images", "text 逗号分隔", ""),
        ("status", "在售/已售/已下架", ""), ("view_count", "int 默认0", ""),
        ("created_at", "datetime", ""),
    ])
    orders = entity(c, 1230, 470, 380, "orders 订单", trade_c, [
        ("id", "int PK", "PK"), ("order_no", "varchar(40)", "UK"),
        ("goods_id", "int →goods", "FK"), ("buyer_id", "int →users", "FK"),
        ("seller_id", "int →users", "FK"), ("price", "decimal(10,2)", ""),
        ("status", "PENDING 等四态", ""), ("created_at", "datetime", ""),
        ("finished_at", "datetime 可空", ""),
    ])
    reviews = entity(c, 1230, 860, 380, "reviews 评价", social_c, [
        ("id", "int PK", "PK"), ("order_id", "int →orders", "FK"),
        ("reviewer_id", "int →users", "FK"), ("target_id", "int →users", "FK"),
        ("rating", "tinyint 1~5", ""), ("content", "text", ""), ("created_at", "datetime", ""),
    ])
    messages = entity(c, 620, 860, 380, "messages 站内消息", social_c, [
        ("id", "int PK", "PK"), ("sender_id", "int →users", "FK"),
        ("receiver_id", "int →users", "FK"), ("goods_id", "int →goods 可空", "FK"),
        ("content", "text", ""), ("is_read", "tinyint(1) 默认0", ""), ("created_at", "datetime", ""),
    ])

    # 一个用户收藏多件商品、一件商品被多人收藏
    relation(c, [anchor(favorites, "R", 0.4), anchor(users, "L", 0.28)], "start", "收藏",
             0.5)
    relation(c, [anchor(favorites, "B", 0.5), anchor(goods, "L", 0.42)], "start", "收藏",
             0.3)
    # 分类与商品：一个分类下多件商品
    relation(c, [anchor(categories, "R", 0.5), anchor(goods, "L", 0.86)], "start", "归类",
             0.78)
    # 卖家发布商品
    relation(c, [anchor(users, "B", 0.5), anchor(goods, "T", 0.5)], "start", "发布", 0.55)
    # 商品被下单
    relation(c, [anchor(goods, "R", 0.5), anchor(orders, "L", 0.52)], "start", "成交",
             0.4)
    # 买家、卖家两类订单
    relation(c, [anchor(users, "R", 0.3), anchor(orders, "L", 0.14)], "start", "买家下单",
             0.55)
    relation(c, [anchor(users, "R", 0.62), anchor(orders, "L", 0.30)], "start", "卖家接单",
             0.55)
    # 订单与评价一一对应
    relation(c, [anchor(orders, "B", 0.5), anchor(reviews, "T", 0.5)], "start", "一次评价",
             0.5)
    # 评价人、被评价人共用一条线注明
    relation(c, [anchor(users, "R", 0.95), (1090, 300), (1090, 897),
                 anchor(reviews, "L", 0.15)], "start", "评价人/被评人", 0.72)
    # 消息的收发双方
    relation(c, [anchor(messages, "L", 0.3), (520, 930), (520, 250),
                 anchor(users, "L", 0.62)], "start", "收发消息", 0.38)
    # 消息关联商品
    relation(c, [anchor(messages, "T", 0.5), anchor(goods, "B", 0.5)], "start", "关联商品",
             0.5)
    # 分类自关联（父子分类）
    c.arrow([(230, 470), (230, 428), (400, 428), (400, 464)], fill=goods_c)
    c.text((315, 412), "父子分类 1:N", size=12, fill=MUTED, anchor="mm")

    c.text((40, 1150), "说明：实线箭头由「1」端指向「N」端；PK 主键、FK 外键、UK 唯一键。"
                       "全部外键在 MySQL 中建成真实约束（14 条），不使用代码层拼接。",
           size=12, fill=MUTED)
    return c.save("fig1_er.png")


def layer(c: Canvas, x: int, y: int, w: int, h: int, name: str, note: str, color: str):
    """画一条分层带：左侧色块写层名，右侧留给内容盒子。"""
    c.rect((x, y, x + w, y + h), fill="#f7f9fc", outline="#dde5ef", width=1.2, radius=10)
    c.d.rounded_rectangle([x * S, y * S, (x + 118) * S, (y + h) * S], radius=10 * S, fill=color)
    c.d.rectangle([(x + 100) * S, y * S, (x + 118) * S, (y + h) * S], fill=color)
    c.text((x + 22, y + h / 2 - 8), name, size=15, bold=True, fill="#ffffff", anchor="lm")
    c.text((x + 22, y + h / 2 + 15), note, size=10, fill="#e6eefa", anchor="lm")


def chip(c: Canvas, x: int, y: int, w: int, h: int, name: str, note: str = "",
         fill="#ffffff", outline="#cfdae8", name_size=13):
    """画一个组件小盒：主标题 + 次要说明。"""
    c.rect((x, y, x + w, y + h), fill=fill, outline=outline, width=1.1, radius=7)
    if note:
        c.text((x + w / 2, y + h / 2 - 8), name, size=name_size, bold=True, fill=INK, anchor="mm")
        c.text((x + w / 2, y + h / 2 + 10), note, size=10, fill=MUTED, anchor="mm")
    else:
        c.text((x + w / 2, y + h / 2), name, size=name_size, fill=INK, anchor="mm")


def build_architecture() -> Path:
    """第二张图：三层架构 + 中间件 + 一次下单请求的数据流。"""
    c = Canvas(1800, 1050)
    title_bar(c, "图 2　系统架构与请求调用链", "表现层 / 业务层 / 数据层，右侧为一次下单的完整数据流")

    # 表现层
    layer(c, 40, 100, 1200, 190, "表现层", "浏览器", "#2f9e8f")
    cw, gap = 258, 14
    names = [("首页 / 列表", "index·goods-list"), ("商品详情", "goods-detail"),
             ("发布 / 我的商品", "publish·my-goods"), ("订单与消息", "my-orders·messages")]
    for i, (n, sub) in enumerate(names):
        chip(c, 172 + i * (cw + gap), 118, cw, 60, n, sub)
    names2 = [("登录 / 注册", "login·register"), ("个人中心", "profile"),
              ("收藏 / 评价", "favorites·review"), ("公共脚本", "api·common·pages.js")]
    for i, (n, sub) in enumerate(names2):
        chip(c, 172 + i * (cw + gap), 190, cw, 60, n, sub)

    # 接入层
    layer(c, 40, 310, 1200, 96, "接入层", "Uvicorn", "#2f6fb3")
    chip(c, 172, 324, 300, 68, "CORS 中间件", "跨域与预检放行")
    chip(c, 486, 324, 300, 68, "请求日志中间件", "方法·路径·耗时·状态码")
    chip(c, 800, 324, 300, 68, "统一异常处理器", "BusinessError → detail")
    chip(c, 1114, 324, 90, 68, "Static", "/pages")

    # 业务层
    layer(c, 40, 426, 1200, 236, "业务层", "FastAPI", "#2f4b7c")
    c.text((172, 442), "路由层 routers（只做参数与身份校验）", size=12, bold=True, fill=NAVY)
    routers = ["auth", "users", "goods", "orders", "favorites", "messages", "reviews", "upload", "system"]
    rw = 110
    for i, r in enumerate(routers):
        chip(c, 172 + i * (rw + 6), 462, rw, 46, r, name_size=12)
    c.text((172, 528), "服务层 services（业务规则、事务、状态机）", size=12, bold=True, fill=NAVY)
    services = [("goods", "检索排序"), ("orders", "行锁下单"), ("order_state", "六条转移"),
                ("users", "账号资料"), ("social", "收藏评价"), ("presenters", "字段收敛")]
    sw = 166
    for i, (n, sub) in enumerate(services):
        chip(c, 172 + i * (sw + 8), 548, sw, 56, n, sub)
    c.text((172, 620), "依赖注入 deps：解析 Bearer 令牌 → 当前用户；越权 403、找不到 404、状态冲突 409",
           size=11, fill=MUTED)

    # 数据层
    layer(c, 40, 682, 1200, 150, "数据层", "SQLAlchemy 2.0", "#c77d2a")
    chip(c, 172, 698, 340, 118, "ORM 模型 models", "7 张表 · 14 外键 · 6 索引")
    chip(c, 526, 698, 340, 118, "会话与事务", "Session 绑定 · commit/rollback")
    chip(c, 880, 698, 324, 118, "连接池 PyMySQL", "utf8mb4 · 预检探活")

    # 存储
    c.rect((40, 852, 1240, 952), fill="#fdf7ee", outline="#e8d3b4", width=1.2, radius=10)
    c.d.rounded_rectangle([40 * S, 852 * S, 158 * S, 952 * S], radius=10 * S, fill="#8a6a3a")
    c.d.rectangle([140 * S, 852 * S, 158 * S, 952 * S], fill="#8a6a3a")
    c.text((62, 892), "存储", size=15, bold=True, fill="#ffffff", anchor="lm")
    c.text((62, 916), "持久化", size=10, fill="#f0e6d6", anchor="lm")
    chip(c, 172, 866, 500, 72, "MySQL 8.0 InnoDB", "secondhand_market 库 · 行锁 SELECT … FOR UPDATE")
    chip(c, 686, 866, 518, 72, "本地文件系统", "frontend/uploads 图片，≤5MB，JPG/PNG/WebP")

    # 层间箭头与协议
    for y1, y2, label in [(290, 310, "HTTP 同源请求"), (406, 426, "ASGI"),
                          (662, 682, "Session / SQL"), (832, 852, "InnoDB 读写")]:
        c.arrow([(640, y1), (640, y2)], fill="#b9c7d8", width=1.6, head=8)
        c.text((652, (y1 + y2) / 2), label, size=10, fill=MUTED, anchor="lm")

    # 右侧调用链
    c.rect((1290, 100, 1760, 952), fill="#f7f9fc", outline="#dde5ef", width=1.2, radius=10)
    c.text((1312, 122), "一次「立即购买」的数据流", size=14, bold=True, fill=NAVY)
    steps = [
        ("1", "买家点击按钮", "pages.js 取 goods_id，读 localStorage 中的令牌"),
        ("2", "fetch POST /api/orders", "api.js 统一加 Authorization: Bearer <token>"),
        ("3", "CORS 与日志中间件", "记录方法、路径、耗时"),
        ("4", "依赖注入解析令牌", "deps 校验签名与过期，取出当前用户"),
        ("5", "路由转服务层", "orders.create_order 接管校验"),
        ("6", "开启事务并加行锁", "SELECT … FOR UPDATE 锁住商品行"),
        ("7", "校验商品状态", "非「在售」直接 409，事务回滚"),
        ("8", "写订单并改商品状态", "同一事务内插入订单、商品置为已售"),
        ("9", "presenter 组装响应", "附带 available_actions 供前端渲染按钮"),
        ("10", "浏览器渲染", "订单页出现「撤销订单 / 等待卖家确认」"),
    ]
    y = 156
    for no, name, note in steps:
        c.badge(1330, y + 12, no, fill=NAVY, r=11, size=11)
        c.text((1352, y + 2), name, size=12, bold=True, fill=INK)
        c.text((1352, y + 20), note, size=10, fill=MUTED)
        if no != "10":
            c.line([(1330, y + 24), (1330, y + 62)], fill="#c6d3e2", width=1.2)
        y += 78

    c.text((40, 985), "说明：路由层不写业务判断，状态转移只在 order_state.py 一张表里定义；"
                      "前端按钮完全由接口返回的 available_actions 决定，避免前后端各写一套状态规则。",
           size=12, fill=MUTED)
    return c.save("fig2_architecture.png")


def build_modules() -> Path:
    """第三张图：功能模块树，每个模块标注负责人。"""
    groups = [
        ("账号与鉴权", "王昱皓", ["注册与登录", "JWT 会话保持", "个人资料修改", "头像上传", "密码修改"]),
        ("商品模块", "杨云凇", ["发布商品（多图）", "编辑与软删除", "上架 / 下架", "关键词搜索", "分类筛选与价格排序", "我的商品管理"]),
        ("交易模块", "郝津德", ["下单防超卖", "订单状态机", "订单列表与详情", "取消与退款"]),
        ("互动模块", "郝津德 / 安远", ["站内消息会话", "未读数提醒", "商品收藏", "交易后互评", "评分统计"]),
        ("平台支撑", "郝津德", ["配置与数据库连接", "ORM 模型与建库脚本", "统一异常与日志", "图片上传服务", "健康检查", "初始化与打包脚本"]),
        ("前端公共层", "王昱皓", ["api.js 统一请求", "common.js 导航注入", "style.css 设计变量", "十四页响应式布局"]),
        ("质量保障", "安远", ["68 项 pytest 用例", "并发下单验证", "Bug 追踪表", "接口与文档一致性核对"]),
    ]
    rows = [(-(-len(leaves) // 2)) for _, _, leaves in groups]
    heights = [max(78, r * 50 + 14) for r in rows]
    content_end = 76 + sum(heights) + 14 * (len(groups) - 1)
    total = content_end + 64
    c = Canvas(1340, total)
    title_bar(c, "图 3　功能模块划分与责任人", "自上而下拆到可分配粒度，每个模块标注负责人")

    root_y = 76 + (content_end - 76) // 2 - 40
    c.rect((40, root_y, 250, root_y + 80), fill=NAVY, outline=NAVY, radius=10)
    c.text((145, root_y + 30), "校园二手", size=16, bold=True, fill="#ffffff", anchor="mm")
    c.text((145, root_y + 54), "交易平台", size=16, bold=True, fill="#ffffff", anchor="mm")

    y = 76
    spine = []
    for (name, owner, leaves), h in zip(groups, heights):
        color = OWNER_COLOR.get(owner.split(" / ")[0], NAVY)
        c.rect((330, y, 640, y + h), fill="#ffffff", outline=color, width=1.6, radius=9)
        c.d.rounded_rectangle([330 * S, y * S, 340 * S, (y + h) * S], radius=4 * S, fill=color)
        c.text((356, y + h / 2 - 10), name, size=14, bold=True, fill=INK, anchor="lm")
        c.text((356, y + h / 2 + 12), owner, size=11, fill=color, anchor="lm")
        spine.append((y + h / 2, color))

        # 叶子模块用一条竖向干线分叉，避免从模块盒射出扇形连线
        rows_n = -(-len(leaves) // 2)
        centers = [y + 8 + r * 50 + 20 for r in range(rows_n)]
        c.line([(640, y + h / 2), (664, y + h / 2)], fill="#c3d0e0", width=1.3)
        c.line([(664, min(centers + [y + h / 2])), (664, max(centers + [y + h / 2]))],
               fill="#c3d0e0", width=1.3)
        for i, leaf in enumerate(leaves):
            row, col = divmod(i, 2)
            lx, ly = 690 + col * 292, y + 8 + row * 50
            c.rect((lx, ly, lx + 272, ly + 40), fill="#ffffff", outline="#c9d6e6", width=1.1, radius=6)
            c.text((lx + 14, ly + 20), leaf, size=12, fill=INK, anchor="lm")
            c.line([(664, ly + 20), (lx, ly + 20)], fill="#c3d0e0", width=1.3)
            c.line([(lx, ly + 20), (lx + 8, ly + 16)], fill="#c3d0e0", width=1.3)
            c.line([(lx, ly + 20), (lx + 8, ly + 24)], fill="#c3d0e0", width=1.3)
        y += h + 14

    # 主干：根节点连到各模块
    c.line([(250, root_y + 40), (300, root_y + 40)], fill=NAVY, width=1.6)
    top, bottom = spine[0][0], spine[-1][0]
    c.line([(300, top), (300, bottom)], fill=NAVY, width=1.6)
    for cy, color in spine:
        c.arrow([(300, cy), (330, cy)], fill=NAVY, width=1.6, head=7)
    c.text((40, content_end + 26), "说明：负责人口径与《分工说明》一致；同一模块出现两人时为共同承担（消息与收藏归郝津德，互评与评分统计归安远）。",
           size=12, fill=MUTED)
    return c.save("fig3_modules.png")


def build_state() -> Path:
    """第四张图：订单状态机，标注每个动作的触发角色。"""
    c = Canvas(1560, 490)
    title_bar(c, "图 4　订单状态机", "六条合法转移，按「当前状态 + 目标状态 + 角色」唯一确定")

    def state(x, y, name, cn, color):
        c.rect((x, y, x + 250, y + 74), fill="#ffffff", outline=color, width=1.8, radius=12)
        c.d.rounded_rectangle([x * S, y * S, (x + 250) * S, (y + 10) * S], radius=5 * S, fill=color)
        c.text((x + 125, y + 30), name, size=15, bold=True, fill=INK, anchor="mm")
        c.text((x + 125, y + 55), cn, size=12, fill=MUTED, anchor="mm")
        return {"x1": x, "y1": y, "x2": x + 250, "y2": y + 74}

    pending = state(150, 300, "PENDING", "待确认", "#b03a48")
    paid = state(620, 150, "PAID_PENDING", "待收货", "#2f4b7c")
    done = state(1090, 150, "COMPLETED", "已完成", "#2f6fb3")
    cancel = state(620, 480, "CANCELLED", "已取消", "#5b6b7f")

    c.badge(90, 337, "", fill="#b03a48", r=8, size=1)
    c.arrow([(105, 337), (150, 337)], fill="#b03a48", width=1.8)
    c.text((72, 337), "下单", size=11, fill=MUTED, anchor="rm")

    def move(p1, p2, label, role, mid=None):
        c.arrow([p1, p2], fill=NAVY, width=1.7, head=8)
        lx, ly = mid or ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        tw = max(font(12).getlength(label), font(10).getlength(role)) / S + 20
        c.d.rounded_rectangle([(lx - tw / 2) * S, (ly - 22) * S, (lx + tw / 2) * S, (ly + 22) * S],
                              radius=6 * S, fill="#ffffff", outline="#dde5ef")
        c.text((lx, ly - 9), label, size=12, bold=True, fill=INK, anchor="mm")
        c.text((lx, ly + 9), role, size=10, fill=MUTED, anchor="mm")

    move(anchor(pending, "R", 0.25), anchor(paid, "L", 0.6), "确认出售", "卖家", (508, 268))
    move(anchor(pending, "R", 0.8), anchor(cancel, "L", 0.3), "拒绝 / 撤销", "卖家 / 买家", (452, 452))
    move(anchor(paid, "R", 0.3), anchor(done, "L", 0.3), "确认收货", "买家", (980, 172))
    move(anchor(paid, "B", 0.5), anchor(cancel, "T", 0.5), "取消订单", "买家", (745, 352))
    c.arrow([(1215, 224), (1215, 517), (870, 517)], fill=NAVY, width=1.7, head=8)
    c.d.rounded_rectangle([(1230 - 66) * S, (352 - 22) * S, (1230 + 66) * S, (352 + 22) * S],
                          radius=6 * S, fill="#ffffff", outline="#dde5ef")
    c.text((1230, 343), "申请退款", size=12, bold=True, fill=INK, anchor="mm")
    c.text((1230, 361), "买家", size=10, fill=MUTED, anchor="mm")

    c.text((1420, 300), "商品联动", size=13, bold=True, fill=NAVY)
    notes = ["下单：商品置为已售", "取消：商品回到在售", "退款：商品保持已售", "非法流转返回 409", "角色越权返回 403"]
    yy = 328
    for n in notes:
        c.text((1420, yy), "· " + n, size=11, fill=MUTED)
        yy += 22
    return c.save("fig4_order_state.png")


if __name__ == "__main__":
    for f in (build_er(), build_architecture(), build_modules(), build_state()):
        print(f"已生成 {f.relative_to(ROOT)}")
