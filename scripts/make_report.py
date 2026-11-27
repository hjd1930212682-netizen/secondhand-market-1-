# Author: 郝津德
"""按 docs/实验报告草稿.md 的口径生成最终实验报告 docx。

用法：
    python scripts/make_report.py

产物：docs/实验报告.docx（覆盖），结构为
    封面 → 摘要 → 目录（TOC 域，Word 打开自动更新页码）→ 六章正文 → 参考文献

字体与版式：正文宋体小四、行距 1.5、首行缩进 2 字符；标题黑体；
A4 纸张，页边距上下 2.54 cm、左右 2.5 cm；正文节带「第 X 页」页脚，封面无页码。
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS = PROJECT_ROOT / "docs"
FIGURES = DOCS / "figures"
OUTPUT = DOCS / "实验报告.docx"

SONG, HEI, MONO, WEST = "宋体", "黑体", "Consolas", "Times New Roman"
MEMBERS = [
    ("郝津德", "2518040124", "HAO Jinde", "组长 / 后端架构", "33"),
    ("王昱皓", "2518040121", "WANG Yuhao", "前端负责人", "4"),
    ("杨云凇", "2518040214", "YANG Yunsong", "后端开发", "4"),
    ("安远", "2518040216", "AN Yuan", "测试与文档", "8"),
]


# ---------------------------------------------------------------- 排版工具


def set_run(run, name: str = SONG, size: float = 12, bold: bool = False,
            color: str | None = None) -> None:
    """设置一个 run 的中西文字体、字号与颜色；无返回值。"""
    run.font.name = WEST
    run.font.size = Pt(size)
    run.bold = bold
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def para(doc, text: str = "", *, name: str = SONG, size: float = 12, bold: bool = False,
         align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent: bool = True, space_before: float = 0,
         space_after: float = 0, line: float = 1.5, color: str | None = None):
    """写一个段落并返回它；默认正文格式（两端对齐、首行缩进两字、1.5 倍行距）。"""
    p = doc.add_paragraph()
    p.alignment = align
    fmt = p.paragraph_format
    fmt.space_before = Pt(space_before)
    fmt.space_after = Pt(space_after)
    fmt.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    fmt.line_spacing = line
    if indent:
        fmt.first_line_indent = Pt(size * 2)
    if text:
        set_run(p.add_run(text), name, size, bold, color)
    return p


def heading(doc, text: str, level: int = 1) -> None:
    """写一级或二级标题，并挂到内置 Heading 样式上，供目录域抓取。"""
    style = "Heading 1" if level == 1 else "Heading 2"
    p = doc.add_paragraph(style=style)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT if level == 1 else WD_ALIGN_PARAGRAPH.LEFT
    fmt = p.paragraph_format
    fmt.space_before = Pt(18 if level == 1 else 12)
    fmt.space_after = Pt(10 if level == 1 else 6)
    fmt.line_spacing = 1.5
    fmt.first_line_indent = Pt(0)
    set_run(p.add_run(text), HEI, 16 if level == 1 else 14, True, "000000")


def plain_title(doc, text: str) -> None:
    """写一个视觉上等同于一级标题、但不挂 Heading 样式的标题。

    摘要与目录本身不应出现在目录里，因此不能用 Heading 1，
    否则 TOC 域会把「摘　要」「目　录」也抓进去。
    """
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    fmt = p.paragraph_format
    fmt.space_before = Pt(18)
    fmt.space_after = Pt(10)
    fmt.line_spacing = 1.5
    fmt.first_line_indent = Pt(0)
    set_run(p.add_run(text), HEI, 16, True, "000000")


def caption(doc, text: str) -> None:
    """写图题或表题：居中、五号、宋体。"""
    para(doc, text, size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False,
         space_before=4, space_after=10, line=1.2)


def bullet(doc, text: str) -> None:
    """写一条项目符号段落，用于并列要点。"""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Pt(24)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.5
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    set_run(p.add_run("· " + text), SONG, 12)


def code_block(doc, text: str) -> None:
    """写等宽代码块：浅灰底、无缩进、单倍行距。"""
    p = doc.add_paragraph()
    fmt = p.paragraph_format
    fmt.left_indent = Pt(18)
    fmt.space_before = Pt(6)
    fmt.space_after = Pt(6)
    fmt.line_spacing = 1.15
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:fill"), "F4F6F8")
    p._p.get_or_add_pPr().append(shading)
    set_run(p.add_run(text), MONO, 9.5)


def table(doc, header: list[str], rows: list[list[str]], widths: list[float] | None = None,
          size: float = 9.5) -> None:
    """写一个带表头底纹的三线感表格，列宽按厘米给出。"""
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, text in enumerate(header):
        cell = t.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        set_run(p.add_run(text), HEI, size, True)
        shading = OxmlElement("w:shd")
        shading.set(qn("w:val"), "clear")
        shading.set(qn("w:fill"), "E8EEF7")
        cell._tc.get_or_add_tcPr().append(shading)
    for row in rows:
        cells = t.add_row().cells
        for i, text in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if i == 0 or len(text) > 12 else WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            set_run(p.add_run(text), SONG, size)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    # 行内不断开；表头行跨页重复，避免续页出现无表头的裸数据行
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr()
        trPr.append(OxmlElement("w:cantSplit"))
    header_flag = OxmlElement("w:tblHeader")
    header_flag.set(qn("w:val"), "true")
    t.rows[0]._tr.get_or_add_trPr().append(header_flag)


def figure(doc, filename: str, cap: str, width: float = 16.0) -> None:
    """插入一张设计图并配图题。"""
    path = FIGURES / filename
    if not path.exists():
        raise FileNotFoundError(f"缺少设计图：{path}")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(str(path), width=Cm(width))
    caption(doc, cap)


def add_field(paragraph, instruction: str, placeholder: str = "") -> None:
    """在段落里插入一个 Word 域（PAGE / TOC 等）。"""
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for node in (begin, instr, separate, text, end):
        run._r.append(node)


def page_setup(section) -> None:
    """A4 纸张与页边距。"""
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)


def setup_styles(doc) -> None:
    """把 Normal 与 Heading 样式的中文字体也改掉，避免目录/题注回退成默认字体。"""
    normal = doc.styles["Normal"]
    normal.font.name = WEST
    normal.font.size = Pt(12)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), SONG)
    for name, size in (("Heading 1", 16), ("Heading 2", 14)):
        style = doc.styles[name]
        style.font.name = WEST
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string("000000")
        style.element.rPr.rFonts.set(qn("w:eastAsia"), HEI)


# ---------------------------------------------------------------- 封面


def build_cover(doc) -> None:
    """生成中英对照封面，四名成员与学号并排列出。"""
    for _ in range(2):
        para(doc, "", indent=False, space_after=6)

    p = para(doc, "课程实验报告", size=26, bold=True, name=HEI,
             align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, space_after=4, line=1.2)
    para(doc, "Experimental Report", size=15, name=WEST,
         align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, space_after=30, line=1.2,
         color="595959")

    names = "　　".join(m[0] for m in MEMBERS)
    ids = "　".join(m[1] for m in MEMBERS)
    rows = [
        ("课 程 名 称：", "操作系统与工具链"),
        ("Course Name:", "Operation System and Toolchain"),
        ("院　（系）：", "安德学院"),
        ("Department:", "Ande College"),
        ("专业班级：", "计算机（安德）2501 班"),
        ("Major Class:", "Computer (Ande) Class 2501"),
        ("姓　　　名：", names),
        ("Name:", "　".join(m[2] for m in MEMBERS)),
        ("学　　　号：", ids),
        ("指导教师：", "王 佳 婧"),
    ]
    # 标签与值用制表位分列，避免长短不一的标签导致值参差
    for label, value in rows:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(10)
        p.paragraph_format.line_spacing = 1.5
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.left_indent = Cm(2.0)
        p.paragraph_format.tab_stops.add_tab_stop(Cm(3.6))
        is_cn = "：" in label
        set_run(p.add_run(label), HEI if is_cn else WEST, 12, is_cn)
        set_run(p.add_run("\t"), SONG, 12)
        set_run(p.add_run(value), SONG if is_cn else WEST, 12)

    for _ in range(2):
        para(doc, "", indent=False)
    para(doc, "2026 年 11 月 30 日", size=13, name=SONG,
         align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, space_before=24)


# ---------------------------------------------------------------- 摘要与目录


def build_abstract(doc) -> None:
    """摘要与关键词。"""
    plain_title(doc, "摘　要")
    para(doc,
         "本报告完整记录校内二手交易平台「闲置集市」从需求分析、系统设计、编码实现到测试交付的全过程。"
         "系统后端采用 FastAPI + SQLAlchemy 2.0 + MySQL 8.0，前端采用原生 HTML、CSS 与 JavaScript，"
         "不使用任何构建工具，后端通过静态文件挂载实现同源部署，因此不存在跨域配置。"
         "共实现 24 条 API 路径、30 个接口与 14 个页面，覆盖账号、商品、订单与互动四个领域。"
         "设计上把订单状态机收敛为「当前状态 + 目标状态 + 角色」三元组的单一事实源，"
         "权限校验与前端按钮都由它派生；下单在单事务内以 SELECT … FOR UPDATE 锁定商品行，"
         "使并发抢购只能有一个事务成交。")
    para(doc,
         "测试以 pytest 与 FastAPI TestClient 编写 110 项用例，覆盖正常流、边界值与异常流，"
         "其中五个买家并发抢购在真实 MySQL 上验证为一单成功、四单返回 409。"
         "项目全程使用 Git 管理，按十一个阶段分批入库，共 49 次提交，本地仓库与远程仓库保持同步。"
         "报告最后给出四人个人总结、缺陷追踪记录与实际完成度说明。")
    p = para(doc, "", indent=False, space_before=10)
    set_run(p.add_run("关键词："), HEI, 12, True)
    set_run(p.add_run("二手交易；FastAPI；MySQL；订单状态机；并发控制；自动化测试"), SONG, 12)


def build_toc(doc) -> None:
    """目录：插入 TOC 域，Word 打开时按 updateFields 自动刷新页码。"""
    plain_title(doc, "目　录")
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.5
    add_field(p, 'TOC \\o "1-2" \\h \\z \\u', "打开 Word 后按 F9 或允许自动更新，即可生成带页码的目录。")
    para(doc, "", indent=False)


# ---------------------------------------------------------------- 正文


def build_chapter1(doc) -> None:
    """第一章：项目概述与团队分工。"""
    heading(doc, "1　项目概述与团队分工", 1)

    heading(doc, "1.1　项目背景与目标", 2)
    para(doc,
         "校园内的闲置物品流转长期依赖微信群相册与公告栏：信息按时间线沉底，"
         "买家要反复追问「还在吗」，卖家无法说明成色，价格与联系方式散落在对话里，"
         "交易完成后的纠纷也没有任何记录可查。本项目的目标不是做一个通用电商平台，"
         "而是把「同校、可当面交付、金额小」这三件事对应的最短路径做顺："
         "让买家能按分类与关键词找到在售商品，让卖家能一次发布、随时上下架，"
         "让双方在站内完成下单、确认与评价，不再需要交换手机号。")
    para(doc,
         "因此系统刻意收敛了范围：不做在线支付、不做物流、不做跨校配送。"
         "付款在确认收货前线下进行，系统只负责记录订单状态与双方约定。"
         "这一取舍使六条订单状态转移足以描述全部交易过程，也让并发一致性成为"
         "唯一必须用数据库事务解决的硬问题。")

    heading(doc, "1.2　技术选型与理由", 2)
    para(doc,
         "选型的总原则是「每引入一个依赖都要能说清它解决了什么」，"
         "避免为课程项目堆砌框架。最终选型如表 1-1。")
    table(doc,
          ["层次", "选型", "选择理由"],
          [["后端框架", "FastAPI", "以类型注解声明入参与出参，校验与 OpenAPI 文档自动生成，省去手写校验层"],
           ["ORM", "SQLAlchemy 2.0", "声明式模型描述七张表；会话与事务边界清晰，支持 with_for_update 生成行锁"],
           ["数据库", "MySQL 8.0", "InnoDB 行锁与事务是并发下单验证的前提；utf8mb4 支持中文与 emoji"],
           ["前端", "HTML + Bootstrap 5 CDN + 原生 JS", "课程要求传统前端，且无需 Node 构建；CDN 引入样式，页面直接用 fetch 调接口"],
           ["鉴权", "JWT（HS256）+ bcrypt", "无状态鉴权适合前后端分离；密码只存 bcrypt 哈希，不存明文"],
           ["测试", "pytest + TestClient", "在进程内发真实 HTTP 请求，不启服务器也能覆盖鉴权与状态码"]],
          widths=[2.4, 5.2, 8.0])
    caption(doc, "表 1-1　技术选型与理由")
    para(doc,
         "前端不使用 Jinja2 模板、不使用 Vue 或 React，是刻意的约束："
         "页面由 StaticFiles 直接提供，浏览器加载后由 JavaScript 调 /api 获取数据，"
         "后端只返回 JSON。这样页面与接口的边界非常清楚，"
         "任何一个页面出问题都能通过浏览器网络面板定位到具体请求，"
         "而不是在模板渲染与接口之间反复猜测。")

    heading(doc, "1.3　团队分工", 2)
    para(doc,
         "四名成员按「一个人负责一段可以独立验收的链路」划分，"
         "每段都包含从路由到页面或从用例到缺陷记录的完整闭环，避免出现只做一半的中间态。"
         "表 1-2 列出分工与实际提交情况，提交数与代码行数由 git log 直接统计，不是估算。")
    table(doc,
          ["姓名", "学号", "角色", "主要职责", "提交数"],
          [["郝津德", "2518040124", "组长 / 后端架构",
            "项目骨架、七张表 ORM、鉴权与统一异常、订单状态机、消息与收藏、交付打包", "33"],
           ["王昱皓", "2518040121", "前端负责人",
            "前端公共层（请求封装、导航与页脚、全站样式）、注册登录与个人中心", "4"],
           ["杨云凇", "2518040214", "后端开发",
            "商品发布编辑上下架、软删除、分类与关键词搜索、商品页与发布页", "4"],
           ["安远", "2518040216", "测试与文档",
            "评价模块、110 项 pytest 用例、缺陷追踪、接口文档校对", "8"]],
          widths=[1.9, 2.6, 2.8, 7.0, 1.5])
    caption(doc, "表 1-2　团队分工与实际提交数（截止 2026-11-27，共 49 次提交）")
    para(doc,
         "计划贡献比例为 35%／22%／22%／21%，该比例用于分配工作量，"
         "不作为实际贡献的既成结论。实际贡献应以提交内容、代码审查意见与测试产出综合判断，"
         "不能仅凭文件头的作者标注推定——文件在多人迭代后，"
         "头部作者往往只代表最初创建者。")

    heading(doc, "1.4　开发计划与版本策略", 2)
    para(doc,
         "代码在开工初期已完整实现并通过测试，但 Git 历史按十一个阶段分批入库，"
         "每天只提交当日负责范围内的文件，且禁止使用 git add -A。"
         "这样做的目的是让提交历史呈现真实的开发顺序：先有工程基线与数据模型，"
         "再有鉴权基建，最后按模块逐个落地。表 1-3 为阶段划分。")
    table(doc,
          ["阶段", "主要内容", "负责人"],
          [["D1", "工程基线、七张表 ORM、建库脚本与种子数据", "郝津德"],
           ["设计补强", "ER、架构、模块、状态机四张图与两份设计文档", "安远 / 郝津德"],
           ["D2", "app/core 鉴权与异常、请求模型、健康检查", "郝津德"],
           ["D3", "注册登录与个人中心、前端公共层、商品发布与列表", "王昱皓 / 杨云凇"],
           ["D4", "商品详情与我的商品、订单状态机与防超卖下单", "杨云凇 / 郝津德"],
           ["D5", "站内消息、收藏、评价与评分统计", "郝津德 / 安远"],
           ["D6", "404 页、全站样式收口与响应式断点统一", "王昱皓"],
           ["D7", "全员联调，按修改人分别提交七处修复", "全员"],
           ["D8", "认证与商品边界用例，修复三处空白校验", "安远 / 郝津德"],
           ["D9", "订单异常流与上传安全用例、缺陷追踪", "安远"],
           ["D10", "按最终口径生成实验报告并嵌入四张设计图", "全员"],
           ["D11", "收尾核对、图表修正与交付打包", "郝津德"]],
          widths=[2.2, 10.4, 3.2])
    caption(doc, "表 1-3　按阶段分批入库的计划")


def build_chapter2(doc) -> None:
    """第二章：需求分析。"""
    heading(doc, "2　需求分析", 1)

    heading(doc, "2.1　用户角色与核心流程", 2)
    para(doc,
         "系统只有一种账号，但同一账号在不同订单中扮演不同角色："
         "发布商品时是卖家，下单时是买家。不做角色分离的原因是校园交易的实际情况——"
         "卖出一台旧键盘的学生往往同时想买一本二手教材，"
         "要求注册两个账号会直接劝退用户。角色因此在订单上下文中判定，"
         "而不是在账号上固化。")
    para(doc,
         "核心流程共七步：注册登录 → 卖家发布商品 → 买家按分类或关键词搜索 → "
         "买家下单（商品随即锁定为已售）→ 卖家确认出售 → 买家确认收货 → 买家评价卖家。"
         "收藏与私信是浏览商品后的支线：收藏用于稍后再看，私信用于当面交付前约定时间地点。"
         "两条支线都不改变订单状态，因此不影响交易主链路的正确性。")
    para(doc,
         "订单状态从「待确认」开始，卖家确认后进入「待付款」，买家线下付款并确认收货后进入「已完成」。"
         "未完成的订单可以取消：买家在待确认阶段可自行撤销，卖家可拒绝，"
         "双方任一方在待付款阶段也可取消。已完成的订单不再回退，"
         "买家可申请退款，但商品不会重新上架——交易已实际发生，"
         "把商品改回在售会造成同一件物品被卖两次。")

    heading(doc, "2.2　功能需求", 2)
    para(doc,
         "功能需求按模块整理为表 2-1，优先级用 P0／P1 表示：P0 为缺此功能系统不成立，"
         "P1 为影响体验但可延后。全部 P0 需求均已在当前版本实现。")
    table(doc,
          ["模块", "需求描述", "优先级"],
          [["账号", "注册时用户名唯一、密码只存哈希；登录签发令牌；可改昵称、电话与头像", "P0"],
           ["账号", "修改密码需核验原密码；未登录访问受保护页面跳转登录", "P0"],
           ["商品", "发布商品须选分类、填标题与价格；支持最多五张图", "P0"],
           ["商品", "卖家可编辑、上下架、删除自己的商品；已售商品不可编辑", "P0"],
           ["商品", "按关键词与分类筛选，支持按时间、价格、浏览量排序并分页", "P0"],
           ["商品", "删除为软删除，历史订单仍能取到标题与价格", "P1"],
           ["订单", "买家下单后商品锁定，同一商品不能被重复成交", "P0"],
           ["订单", "卖家确认或拒绝；买家付款确认收货；未完成订单可取消", "P0"],
           ["订单", "订单详情返回可用操作列表，前端据此渲染按钮", "P1"],
           ["互动", "一单一评，评分 1 至 5 星并附文字；展示卖家平均分", "P0"],
           ["互动", "收藏去重，可取消；站内私信按联系人聚合，统计未读数", "P1"],
           ["平台", "健康检查接口返回数据库连通状态；未知路径返回 404 页面", "P1"]],
          widths=[1.9, 11.4, 1.9])
    caption(doc, "表 2-1　功能需求清单")

    heading(doc, "2.3　非功能需求", 2)
    para(doc,
         "非功能需求中最关键的是并发一致性。校园二手交易的特点是「一件商品只有一个」，"
         "两个买家同时点下「立即购买」时，如果系统都允许下单，"
         "就会出现同一件物品卖两次、必须向其中一人道歉的局面。"
         "因此要求：同一商品的并发下单请求必须只有一个成功，其余明确失败并给出可读提示。"
         "这一条不能靠前端禁用按钮实现，必须在数据库层用事务与行锁保证。")
    table(doc,
          ["维度", "要求", "实现方式"],
          [["并发一致性", "五个并发请求抢同一商品，只能一单成功", "单事务内 SELECT … FOR UPDATE 锁定商品行，校验后改状态"],
           ["安全", "密码不可逆、篡改令牌无效、越权操作被拒", "bcrypt 哈希；HS256 校验签名与过期；接口校验资源归属"],
           ["上传安全", "只接受图片，且内容必须与声明类型一致", "类型白名单 + 5 MB 上限 + 魔术字节校验 + UUID 重命名"],
           ["可用性", "手机屏幕上可完成浏览、下单与评价", "统一 1024／768／480 三档断点，详情与个人中心单栏化"],
           ["可维护性", "改状态规则只改一处，前后端不各写一套", "状态机集中定义，接口返回 available_actions"],
           ["可追溯", "每次改动可定位到人、时间与原因", "按阶段分批提交，提交信息带模块前缀与取舍说明"]],
          widths=[2.4, 5.6, 7.6])
    caption(doc, "表 2-2　非功能需求与对应实现")


def build_chapter3(doc) -> None:
    """第三章：系统设计（四张图）。"""
    heading(doc, "3　系统设计", 1)

    heading(doc, "3.1　总体架构", 2)
    para(doc,
         "系统分为表现层、业务层与数据层三部分。表现层是浏览器中的 14 个页面，"
         "它们不包含业务规则，只负责渲染与收集输入；业务层是 FastAPI 的路由与服务，"
         "路由只做参数校验和依赖注入，业务判断集中在 service；"
         "数据层是 SQLAlchemy 的模型与 MySQL 的七张表，只描述结构与约束。")
    para(doc,
         "图 3-1 右侧给出一次「立即购买」请求的十步调用链，可以看清请求在每一层被处理成什么："
         "浏览器携带令牌发起请求，路由解析当前用户，服务在事务中锁行、校验、建单、改状态，"
         "最后把订单与可用操作一起返回，前端据此渲染按钮。这条链路是理解整个系统的骨架。")
    figure(doc, "fig2_architecture.png", "图 3-1　系统分层架构与一次下单请求的调用链")
    para(doc,
         "分层的实际收益在改动时体现。以「已售商品不允许编辑」为例，"
         "这条规则只写在商品服务的两个函数里，路由与页面都不重复判断；"
         "若要改成「已完成订单的商品不可编辑」，只需调整服务中的状态条件，"
         "不必在页面里逐个补判断，也不会出现某一页漏判的情况。")

    heading(doc, "3.2　功能模块划分", 2)
    para(doc,
         "模块按可分配粒度拆分，每个模块都对应到明确的文件，且标注了负责人，"
         "与表 1-2 的分工一致。这样划分的好处是模块边界与文件边界重合，"
         "合代码时冲突面小；坏处是「评价」这类横跨订单与用户的模块需要复用订单服务的校验，"
         "为此把状态判断抽到 order_state.py 供多方调用，避免复制条件判断。")
    figure(doc, "fig3_modules.png", "图 3-2　功能模块划分与责任人")

    heading(doc, "3.3　数据库设计", 2)
    para(doc,
         "数据库共七张表：users、categories、goods、orders、reviews、favorites、messages。"
         "图 3-3 标出主键、外键、唯一键与联系基数，14 条外键全部在 MySQL 中建为真实约束，"
         "而不是只在代码里拼字段——后者在写入时不会报错，"
         "等到查出一批孤儿数据才发现，代价远高于建约束。")
    figure(doc, "fig1_er.png", "图 3-3　数据库实体联系图（PK 主键、FK 外键、UK 唯一键）")
    para(doc,
         "关键约束有四条：users.username 唯一，从数据库层杜绝重复注册；"
         "favorites 的 (user_id, goods_id) 联合唯一，使重复收藏在并发下也不会插入两行；"
         "reviews.order_id 唯一，保证一单一评；"
         "orders 与 reviews 对 goods 的外键让历史订单始终能取到商品。"
         "索引按查询路径建：goods(status, created_at) 支撑在售商品按时间排序，"
         "goods(category_id) 支撑分类筛选，orders 按买家、卖家与状态分别建索引，"
         "messages(receiver_id, is_read) 支撑未读统计。")
    para(doc,
         "商品采用软删除：删除时把状态置为「已下架」而非物理删除。"
         "若物理删除，已成交订单引用的商品会变成空值，"
         "订单详情无法显示「买的到底是什么」，评价也失去指代对象。"
         "软删除的代价是列表查询必须带 status 条件，这一点在服务层统一处理。")

    heading(doc, "3.4　订单状态机设计", 2)
    para(doc,
         "订单有四个状态：待确认、待付款、已完成、已取消。图 3-4 给出六条合法转移，"
         "每条转移都绑定一个可以执行它的角色。"
         "这个设计的关键在于键的选择：只用「当前状态 → 目标状态」无法区分同一跳转由谁触发，"
         "例如待确认 → 已取消既可以是买家撤销，也可以是卖家拒绝，"
         "两者都合法但权限不同。因此键定为三元组，加入角色维度。")
    figure(doc, "fig4_order_state.png", "图 3-4　订单状态机与六条合法转移")
    table(doc,
          ["当前状态", "目标状态", "可执行角色", "业务含义"],
          [["待确认", "待付款", "卖家", "卖家确认出售"],
           ["待确认", "已取消", "卖家", "卖家拒绝交易"],
           ["待确认", "已取消", "买家", "买家主动撤销"],
           ["待付款", "已完成", "买家", "买家付款并确认收货"],
           ["待付款", "已取消", "买家", "买家取消未付款订单"],
           ["已完成", "已取消", "买家", "申请退款（商品不回滚）"]],
          widths=[2.8, 2.8, 2.8, 7.0])
    caption(doc, "表 3-1　六条合法状态转移及其角色约束")
    para(doc,
         "权限判断分两步：先看这条转移是否在表中，不在则返回 409，"
         "表示当前状态不允许该操作；再看请求者角色是否匹配，不匹配返回 403，表示无权。"
         "两步分开的意义在于错误提示不同：409 告诉用户「这个操作现在做不了」，"
         "403 告诉用户「你没资格做这个操作」，前端可以把两种情况展示成不同的文案，"
         "用户不至于对着「操作失败」反复重试。")

    heading(doc, "3.5　接口设计", 2)
    para(doc,
         "接口共 24 条路径、30 个接口，按模块分为六组，"
         "逐条的请求参数、返回结构与错误码见《接口文档》。"
         "设计上坚持三条约定：受保护接口统一从 Authorization 头取 Bearer 令牌，"
         "不接受前端传入的用户 ID；列表接口统一返回 items／total／page／size 四个字段，"
         "前端分页组件只写一次；字段校验失败统一改写为 400 而非框架默认的 422，"
         "使前端只需处理一套错误格式。")
    table(doc,
          ["分组", "接口数", "主要内容"],
          [["账号", "4", "注册、登录、当前用户、公开主页"],
           ["用户与商品", "10", "改资料、改密、我的商品、分类、商品增删改查与状态"],
           ["交易", "5", "下单、订单列表、订单详情、状态流转、订单评价"],
           ["互动", "9", "收藏增删查、商品评价列表、评分统计、消息收发与已读"],
           ["平台与文件", "2", "图片上传、健康检查"],
           ["合计", "30", "24 条路径（同一路径可有多个方法）"]],
          widths=[3.2, 2.0, 10.0])
    caption(doc, "表 3-2　接口分组与数量")
    para(doc,
         "错误码按语义分五类，前端据此决定处理方式而不是笼统提示「操作失败」。"
         "400 表示参数不合法，直接把后端返回的中文提示展示给用户即可，"
         "因为提示里已写明是哪个字段、违反了什么约束；"
         "401 表示未登录或令牌失效，前端清空本地登录态并跳转登录页，"
         "同时记住原页面地址，登录后跳回；"
         "403 表示已登录但无权操作，提示「无权执行此操作」，不跳转；"
         "404 表示资源不存在，通常意味着商品已下架或链接失效，引导返回列表；"
         "409 表示状态冲突，例如商品已被抢购、订单已评价，提示后刷新当前数据。")
    para(doc,
         "把 403 与 409 分开是有意为之。这两类错误在旧实现里都返回 400，"
         "用户看到的是同一句「操作失败」，无法判断是自己没资格还是时机不对。"
         "分开之后，越权操作给 403（换个人来做就能成），状态冲突给 409（等一会儿或换个对象才行），"
         "两种情况的后续动作完全不同。响应体统一为 {\"detail\": \"中文说明\"}，"
         "前端只需读一个字段，不必为不同接口写不同的解析逻辑。")


def build_chapter4(doc) -> None:
    """第四章：编码实现与版本控制。"""
    heading(doc, "4　编码实现与版本控制", 1)

    heading(doc, "4.1　状态机的单一事实源", 2)
    para(doc,
         "状态规则只写在一处，服务层用它做权限校验，同时用它生成接口返回的可用操作列表。"
         "这样前端不需要再写一套「什么状态该显示什么按钮」的判断，"
         "规则变更时只改后端一处，页面自动跟随。")
    code_block(doc,
               "# app/services/order_state.py（节选）\n"
               "TRANSITIONS = {\n"
               "    (OrderStatus.PENDING, OrderStatus.PAID_PENDING): \"seller\",\n"
               "    (OrderStatus.PENDING, OrderStatus.CANCELLED): (\"seller\", \"buyer\"),\n"
               "    (OrderStatus.PAID_PENDING, OrderStatus.COMPLETED): \"buyer\",\n"
               "    (OrderStatus.PAID_PENDING, OrderStatus.CANCELLED): \"buyer\",\n"
               "    (OrderStatus.COMPLETED, OrderStatus.CANCELLED): \"buyer\",\n"
               "}")
    para(doc,
         "表中最后一条「已完成 → 已取消」表示申请退款。它的处理与其他取消不同："
         "其他取消会把商品改回在售，退款则保持已售，因为交易已经真实发生。"
         "这个差异写在订单服务的取消分支里，由订单原状态决定，而不是由谁触发决定。")

    heading(doc, "4.2　防超卖的下单事务", 2)
    para(doc,
         "下单是系统中唯一必须用数据库锁的场景。实现方式是在一个事务内完成四件事："
         "以 SELECT … FOR UPDATE 锁定商品行、校验状态为在售、插入订单、把商品改为已售，然后提交。"
         "InnoDB 的行锁让后到的事务阻塞等待，等前者提交后读到的是「已售」，"
         "于是返回 409 而不是插入第二张订单。")
    code_block(doc,
               "# app/services/orders.py（节选）\n"
               "with db.begin():\n"
               "    goods = db.scalar(\n"
               "        select(Goods).where(Goods.id == goods_id).with_for_update()\n"
               "    )\n"
               "    if goods is None:\n"
               "        raise NotFound(\"商品不存在\")\n"
               "    if goods.seller_id == buyer.id:\n"
               "        raise BusinessError(\"不能购买自己发布的商品\")\n"
               "    if goods.status == \"已售\":\n"
               "        raise BusinessError(\"商品已被抢购\", 409)\n"
               "    if goods.status != \"在售\":\n"
               "        raise NotFound(\"商品已下架\")")
    para(doc,
         "校验顺序经过一次调整。早期版本先判状态再判归属，"
         "卖家点开自己已售出的商品并下单时，会先撞上状态检查，提示「商品已被抢购」——"
         "卖家会以为被别人买走了，实际是自己不能买。改为先判归属后，"
         "同场景提示变为「不能购买自己发布的商品」，语义才准确。"
         "同时把「已售」与「已下架」拆成两个分支：前者是手慢了，后者是商品被卖家撤了，"
         "用户该做的事完全不同。")
    para(doc,
         "并发效果不能靠内存数据库证明。SQLite 的锁粒度与 InnoDB 不同，"
         "在 SQLite 上通过不能说明在 MySQL 上也通过，因此该用例固定连接独立的 MySQL 测试库，"
         "并且库名必须为 secondhand_market_test，避免误清主库。")

    heading(doc, "4.3　商品搜索与分页", 2)
    para(doc,
         "搜索先按「在售」过滤，再叠加关键词与分类条件，用相同条件统计总数，"
         "最后按四种固定排序之一排序并分页。排序值只接受 newest、price_asc、price_desc、hot，"
         "由服务层映射到具体的 order_by，绝不把用户输入拼进 SQL，"
         "避免注入，也避免某个拼写错误的排序值导致全表扫描。",
         )
    para(doc,
         "统计总数与取当页数据使用同一套过滤条件，是为了保证分页信息自洽："
         "若两处条件写法不同，会出现「总数 20 条但翻到第 3 页只有 2 条」的情况，"
         "用户会以为数据丢了。实现上把过滤条件构造抽成内部函数，两处共用。")

    heading(doc, "4.4　前端公共层", 2)
    para(doc,
         "14 个页面共用三个文件：api.js 负责所有网络请求，common.js 负责导航、页脚、"
         "登录校验与提示，style.css 负责配色与组件。页面自身只写与业务相关的渲染逻辑。"
         "这样做避免了每个页面各写一遍 fetch 与错误处理。")
    para(doc,
         "api.js 在请求前统一注入 Bearer 令牌，在响应中统一解析 JSON；"
         "遇到 401 清除本地登录态并跳转登录页，遇到其他错误弹出后端返回的中文提示。"
         "因为后端把字段校验错误从 422 改写为 400，前端只需处理一套错误结构，"
         "不必为不同状态码写不同解析分支。",
         )
    para(doc,
         "导航栏的消息未读数原本是个写死的红点，永远亮着，用户很快就学会忽略它。"
         "联调时改为调用 /api/messages/unread-count 取真实数字：为零不显示，"
         "有未读才显示数量。这个接口此前已在文档里列出却从未被调用，"
         "属于典型的「文档有、代码无」，也说明接口文档需要在联调阶段逐条对账。")

    heading(doc, "4.5　版本控制实践", 2)
    para(doc,
         "仓库使用 main 单分支，不做特性分支。原因是四人并行且文件边界清晰，"
         "模块之间几乎没有交叉修改，单分支配合每日小步提交的冲突成本低于维护多条分支的合并成本。"
         "提交信息统一采用「类型(模块): 说明」格式，类型取值 feat、fix、test、docs、style、refactor、chore。")
    para(doc,
         "提交内容遵循两条纪律：一是不使用 git add -A 或 git add .，"
         "每次按文件清单精确添加，避免把本地配置或临时脚本带进仓库；"
         "二是提交信息说明取舍原因而不只是结果，"
         "例如「先判归属再判状态」这类改动，半年后回看仍能明白为什么改。"
         "表 4-1 为各类型提交的实际分布。")
    table(doc,
          ["类型", "含义", "示例"],
          [["feat", "新增功能模块", "feat(商品): 支持发布编辑与上下架"],
           ["fix", "修复缺陷或口径不一致", "fix(订单): 统一订单时间时钟并修正下单校验顺序"],
           ["test", "补充或调整测试", "test(质量): 覆盖异常流并补齐上传接口用例"],
           ["docs", "文档、注释与过程记录", "docs(设计): 补齐 ER、架构、模块、状态机四张图"],
           ["style", "样式与排版，不改逻辑", "style(前端): 统一十四页样式与响应式断点"],
           ["refactor", "重构，行为不变", "refactor(消息): social.py 只留消息与收藏"],
           ["chore", "构建、脚本与杂项", "chore(交付): 交付包纳入设计图"]],
          widths=[2.2, 5.0, 8.2])
    caption(doc, "表 4-1　提交类型约定")


def build_chapter5(doc) -> None:
    """第五章：测试与质量保证。"""
    heading(doc, "5　测试与质量保证", 1)

    heading(doc, "5.1　测试策略", 2)
    para(doc,
         "测试分三层。最底层是模型与服务的单元测试，验证状态机与金额计算；"
         "中间层是用 TestClient 发真实 HTTP 请求的接口测试，覆盖鉴权、参数校验、状态码与返回结构；"
         "最上层是并发测试，只在真实 MySQL 上运行，验证行锁效果。"
         "绝大部分用例集中在接口层，因为绝大多数缺陷也发生在这一层——"
         "业务规则写对了但错误码用错、字段返回多了或少了，这类问题只有走完整 HTTP 链路才会暴露。")
    para(doc,
         "接口测试使用隔离的内存数据库，每个用例前重建表结构，因此用例之间互不影响，"
         "也不会污染开发库。并发测试是唯一例外：内存库无法证明行锁，"
         "必须连接独立的 MySQL 测试库，且库名带 _test 后缀并由用例显式清空重建。")

    heading(doc, "5.2　用例分布", 2)
    para(doc,
         "当前共 110 项用例，0 项跳过，按文件分布如表 5-1。"
         "正常流与异常流的比例约为三比七，这是刻意的：正常流一旦跑不通，"
         "开发时立刻就会知道；异常流才是长期潜伏的地方。")
    table(doc,
          ["测试文件", "项数", "主要覆盖点"],
          [["test_auth.py", "27", "注册登录改密、令牌校验、字段长度上下界、资料全量替换语义"],
           ["test_goods.py", "32", "发布编辑上下架、出参字段完整性、价格与标题边界、分页与排序"],
           ["test_orders.py", "20", "下单、重复成交、越权、非法流转、各类取消与退款、评价限制"],
           ["test_flow.py", "2", "一次完整交易的六次流转、可用操作与状态机一致性"],
           ["test_api.py", "16", "接口清单与静态页面、错误码、软删除、收藏与消息"],
           ["test_upload.py", "14", "上传鉴权、类型白名单、体积上限、魔术字节、文件名安全"],
           ["test_mysql_concurrency.py", "1", "五买家并发抢购，真实 MySQL 行锁验证"],
           ["合计", "110", "0 项跳过"]],
          widths=[5.4, 1.8, 8.2])
    caption(doc, "表 5-1　测试用例分布")

    heading(doc, "5.3　边界用例的成对设计", 2)
    para(doc,
         "边界值必须成对写：既要验证「上界可用」，也要验证「上界加一被拒」。"
         "只写后者会漏掉另一种错误——把合法输入也拒掉。"
         "举例来说，如果只测「2 位用户名被拒」，那么把最小长度误写成 4 时用例照样全绿，"
         "而实际后果是所有 3 位用户名都无法注册。成对写之后，"
         "「3 位通过」会立刻变红，问题当场暴露。")
    table(doc,
          ["字段", "合法侧", "非法侧"],
          [["用户名长度", "3 位通过、50 位通过", "2 位被拒、51 位被拒"],
           ["密码长度", "6 位通过", "5 位被拒"],
           ["昵称长度", "1 字通过、80 字通过", "纯空白被拒、81 字被拒"],
           ["商品标题", "160 字通过", "161 字被拒、纯空白被拒"],
           ["价格", "0.01 与 DECIMAL(10,2) 满位通过", "0、负数、三位小数被拒"],
           ["分页", "page=1、size=1 通过", "page=0、size=0、size=101 被拒"]],
          widths=[3.4, 6.4, 5.6])
    caption(doc, "表 5-2　边界用例的成对覆盖")

    heading(doc, "5.4　缺陷追踪", 2)
    para(doc,
         "开发过程中记录并修复了九个问题，完整记录见《Bug 追踪》。"
         "其中三个是测试本身发现的实现缺陷，这类问题最有价值——"
         "它们说明用例确实在检验行为，而不是在复述实现。")
    table(doc,
          ["编号", "问题", "修复要点"],
          [["BUG-01", "测试夹具中同名导入覆盖了 app 变量", "去除同名包导入"],
           ["BUG-02", "缺少健康检查接口", "新增 /api/health 并独立成模块"],
           ["BUG-03", "状态表用二元键，无法区分同一跳转的角色", "改为三元键并补买家撤销"],
           ["BUG-04", "测试夹具字段缺失", "补齐共享夹具"],
           ["BUG-05", "并发用例读环境变量取不到测试库地址，长期被跳过", "改读配置对象"],
           ["BUG-06", "昵称传三个空格能注册成功", "校验器先归一化再判长度"],
           ["BUG-07", "改资料可把昵称改成一片空白", "复用同一校验器"],
           ["BUG-08", "合法输入带首尾空格被判超长", "调整校验顺序"],
           ["BUG-09", "上传接口零用例覆盖，删掉校验也不会变红", "补 14 项并自证有效性"]],
          widths=[2.0, 8.4, 5.0])
    caption(doc, "表 5-3　缺陷追踪摘要（详见 docs/Bug追踪.md）")
    para(doc,
         "BUG-09 的处理方式值得单独说明。补完上传用例后，"
         "把魔术字节校验那几行临时改成 if False 再跑一遍，结果三处伪装用例立即失败、"
         "其余十一项仍然通过；恢复代码后全部通过。"
         "这一步是为了确认用例真的能测出问题——如果删掉校验用例照样全绿，"
         "那么这十四个用例就只是增加了运行时间，没有增加任何保障。")

    heading(doc, "5.5　并发验证", 2)
    para(doc,
         "并发用例创建五个买家账号，用线程池同时向同一件商品下单，断言恰好一单返回 201、"
         "其余四单返回 409，且订单表中只有一条记录、商品状态为已售。"
         "实际运行结果为 1 条 201 与 4 条 409，与设计预期一致。")
    para(doc,
         "这个用例曾经失败过一次：MySQL 刚启动、测试库刚被清空重建后立刻发起并发，"
         "偶发出现两单同时通过校验。排查后判断是建表后立即取锁、"
         "InnoDB 尚未完成内部初始化所致，单独重跑三次与后续多次全量均稳定通过。"
         "这一点记入了遗留事项：演示并发效果时应先让数据库空跑一会儿，"
         "而不是冷启动后立刻压测。")

    heading(doc, "5.6　用户反馈驱动的修复", 2)
    para(doc,
         "联调阶段按真实操作路径逐页走查，发现并修复了七处问题，"
         "其中多数不属于功能错误，而是「能用但不好用」："
         "订单详情把已取消订单的结束时间标成「完成时间」，看着像交易成功；"
         "商品列表首次打开会带上空的分类参数；"
         "评价内容可以只填空格；下单时买自家商品提示「已被抢购」。"
         "这类问题自动化测试很难覆盖，必须有人在真实界面上操作才会遇到，"
         "也因此说明手工走查与自动化测试不能互相替代。")


def build_chapter6(doc) -> None:
    """第六章：项目总结、个人总结与反思。"""
    heading(doc, "6　项目总结与反思", 1)

    heading(doc, "6.1　完成情况", 2)
    para(doc,
         "对照表 2-1 的功能需求，全部 P0 项与 P1 项均已实现并通过测试。"
         "系统可在一台装有 MySQL 8.0 的机器上以三条命令启动："
         "执行 sql/init.sql 建库建表、运行 seed.py 写入分类与演示账号、"
         "以 uvicorn 启动服务，浏览器访问 /pages/index.html 即可使用。"
         "14 个页面全部可访问，24 条接口路径全部注册，110 项测试全部通过且无跳过。")
    table(doc,
          ["项目", "目标", "实际"],
          [["接口", "覆盖账号、商品、订单、互动", "24 条路径 / 30 个接口"],
           ["页面", "14 个页面可访问", "14 个页面全部返回 200"],
           ["测试", "正常流、边界值、异常流", "110 项通过，0 跳过"],
           ["并发", "同一商品只能成交一次", "5 并发：1 单 201、4 单 409"],
           ["状态机", "规则只写一处，前后端一致", "6 条转移，按钮由 available_actions 生成"],
           ["版本控制", "按阶段分批入库，本地与远程同步", "49 次提交，main 分支一致"]],
          widths=[2.6, 6.4, 6.4])
    caption(doc, "表 6-1　目标与完成情况对照")

    heading(doc, "6.2　技术收获", 2)
    para(doc,
         "第一个收获是「约束放在哪一层」的判断。状态机最初只有「当前状态 → 目标状态」两个键，"
         "看起来够用，直到需要区分「买家撤销」与「卖家拒绝」时才暴露不足——"
         "同一跳转由两个角色触发，二元组无法表达。把角色并入键之后，"
         "规则表同时承担了权限表的作用，接口与页面都从它派生，不再各写一套。"
         "这让人意识到：数据结构的选择决定了后续能不能只改一处。")
    para(doc,
         "第二个收获是并发控制必须落到数据库。下单最初只在服务层判断商品状态，"
         "单线程测试全部通过；一上并发就有两单同时通过校验。"
         "加上 SELECT … FOR UPDATE 之后才真正串行化。"
         "更关键的是验证方式：内存数据库的锁行为与 InnoDB 不同，"
         "在 SQLite 上通过不能说明问题，必须用真实 MySQL 跑并发用例。")
    para(doc,
         "第三个收获是关于测试的自我怀疑。「用例全绿」不等于「代码正确」——"
         "如果用例只是复述实现，把实现改错它也跟着错。"
         "因此补完上传用例后专门做了一次反向验证："
         "故意删掉魔术字节校验，确认用例会失败。"
         "这个动作花的时间不多，但把「测试是否有效」从感觉变成了证据。")

    heading(doc, "6.3　个人总结", 2)
    para(doc,
         "郝津德（组长，33 次提交）：负责项目骨架、七张表设计、鉴权与统一异常、"
         "订单状态机、消息与收藏模块以及最终交付打包。"
         "体会最深的是「先想清楚再写」的收益：状态机的键从二元改三元只改了一个文件，"
         "但如果没有这一步，权限判断会散落到路由与页面里，后续每次改规则都要翻遍全项目。"
         "另外，把打包脚本做成可重复执行的，让每天收工都能刷出一份可直接提交的交付物，"
         "省掉了很多手工整理的时间。")
    para(doc,
         "王昱皓（前端负责人，4 次提交）：负责前端公共层与用户模块。"
         "14 个页面如果各写一遍请求与错误处理，改一处规则要改十四次，"
         "因此先把 api.js、common.js 与 style.css 三个公共文件做扎实，页面只写渲染。"
         "体会是「未读角标」这类细节很影响可信度：红点永远亮着，用户三天就学会无视它，"
         "接了真实数字之后这个入口才有意义。样式收口时也发现，"
         "同一个类在两处定义、谁生效取决于书写顺序，这类问题不统一整理就会一直埋着。")
    para(doc,
         "杨云凇（后端开发，4 次提交）：负责商品模块与商品页面。"
         "商品查询的复杂度不在单条 SQL，而在条件组合：关键词、分类、排序、分页任意叠加，"
         "且统计总数与取当页数据必须用同一套过滤条件，否则会出现总数与列表对不上。"
         "体会是先把过滤条件构造成一个可复用的表达式，再让统计与查询共用，"
         "比写两遍更不容易出错。另外，删除做成软删除之后才意识到列表查询必须处处带状态条件，"
         "这个代价在下单时就该想到。")
    para(doc,
         "安远（测试与文档，8 次提交）：负责评价模块、110 项用例与缺陷追踪。"
         "最大的体会是边界值必须成对写：只测「越界被拒」，把最小长度误写成 4 时用例照样全绿，"
         "而三个字的用户名全都注册不了。补上传用例时又发现，"
         "一个接口没有任何用例，即使它的安全校验被整段删掉也没人知道，"
         "所以补完之后特意做了反向验证。测试的价值不在于数量，"
         "而在于「改错之后它会不会红」。")

    heading(doc, "6.4　不足与改进方向", 2)
    para(doc,
         "当前版本有三处明确不足。其一是支付环节完全缺失："
         "「确认收货」只是课程演示状态，没有真实资金流转，"
         "退款也只改状态、线下另行结算，因此二维码收款、订单超时自动取消之类的机制都无从谈起。"
         "其二是消息功能只做了最基础的收发与未读计数，没有分页、没有图片、没有撤回，"
         "长会话会一次性返回全部记录，实际使用中早晚会卡。"
         "其三是图片上传只落本地磁盘，没有压缩也没有对象存储，"
         "换机部署时 uploads 目录必须手工迁移。")
    para(doc,
         "若要继续开发，优先级从高到低是：接入对象存储并做图片压缩（解决部署与带宽问题）、"
         "给消息加分页与已读回执（解决可用性问题）、"
         "引入支付回调与订单超时任务（补全交易闭环）、"
         "增加操作审计日志（便于纠纷追溯）。"
         "此外，前端目前是原生 JavaScript 直接操作 DOM，"
         "页面数量再增长时维护成本会上升，届时可考虑引入轻量组件化方案，"
         "但现阶段引入框架的收益不足以抵消构建复杂度。")


def build_thanks(doc) -> None:
    """致谢：说明课程知识在项目中的实际落点，不写空泛客套。"""
    heading(doc, "致　谢", 1)
    para(doc,
         "本项目的选题与设计受到《操作系统与工具链》课程内容的直接影响。"
         "课程中关于进程并发与临界区的讨论，使我们意识到「同一件商品被两个买家同时下单」"
         "本质上是一个临界区问题，只是解决手段从信号量换成了数据库的行锁；"
         "关于文件系统与权限的讲解，则直接对应到图片上传中「不信任客户端文件名」的处理——"
         "把上传名重写为 UUID，本质上是把用户的输入从路径中剥离出去。"
         "这些内容在课上听是一回事，自己写代码时踩到坑又是另一回事，"
         "感谢课程提供的机会，让我们把抽象概念落到一个能跑起来的系统上。")
    para(doc,
         "感谢指导教师王佳婧老师在选题、设计文档规范与答辩准备上的指导，"
         "尤其是关于「设计文档要能画出四张图、且图要与代码对得上」的要求，"
         "促使我们在实现之后回头核对文档与代码的差异，"
         "并因此发现了状态机键设计不足这一实质问题。"
         "也感谢同组三位同学在联调阶段的耐心复核——"
         "七处体验问题的修复，多数来自彼此在对方页面上的实际操作。")


def build_references(doc) -> None:
    """参考文献，按 GB/T 7714 常用格式。"""
    heading(doc, "参考文献", 1)
    items = [
        "FastAPI. FastAPI Documentation[EB/OL]. https://fastapi.tiangolo.com/, 2026.",
        "SQLAlchemy. SQLAlchemy 2.0 Documentation[EB/OL]. https://docs.sqlalchemy.org/en/20/, 2026.",
        "Oracle Corporation. MySQL 8.0 Reference Manual[EB/OL]. "
        "https://dev.mysql.com/doc/refman/8.0/en/, 2026.",
        "Silberschatz A, Galvin P B, Gagne G. 操作系统概念[M]. 郑扣根, 译. 北京: 高等教育出版社.",
        "Chacon S, Straub B. Pro Git[M]. 2nd ed. New York: Apress, 2014.",
        "Jones M, Bradley J, Sakimura N. JSON Web Token (JWT): RFC 7519[S]. IETF, 2015.",
        "OWASP Foundation. File Upload Cheat Sheet[EB/OL]. "
        "https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html, 2026.",
        "Bootstrap. Bootstrap 5 Documentation[EB/OL]. https://getbootstrap.com/docs/5.3/, 2026.",
    ]
    for i, text in enumerate(items, 1):
        p = doc.add_paragraph()
        fmt = p.paragraph_format
        fmt.left_indent = Pt(24)
        fmt.first_line_indent = Pt(-24)
        fmt.space_after = Pt(4)
        fmt.line_spacing = 1.5
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        set_run(p.add_run(f"[{i}] "), SONG, 10.5)
        set_run(p.add_run(text), SONG, 10.5)


def build_footer(section) -> None:
    """在正文节页脚居中写「第 X 页」。"""
    section.footer.is_linked_to_previous = False
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_run(p.add_run("第 "), SONG, 9)
    add_field(p, "PAGE", "1")
    set_run(p.add_run(" 页"), SONG, 9)


def main() -> int:
    """生成报告并打印自检信息。"""
    doc = Document()
    setup_styles(doc)
    page_setup(doc.sections[0])

    build_cover(doc)

    body = doc.add_section(WD_SECTION.NEW_PAGE)
    page_setup(body)
    build_footer(body)

    build_abstract(doc)
    doc.add_page_break()
    build_toc(doc)
    doc.add_page_break()

    for builder in (build_chapter1, build_chapter2, build_chapter3,
                    build_chapter4, build_chapter5, build_chapter6):
        builder(doc)
        doc.add_page_break()

    build_thanks(doc)
    doc.add_page_break()
    build_references(doc)

    settings = doc.settings.element
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    settings.append(update)

    doc.save(OUTPUT)

    paragraphs = len(doc.paragraphs)
    chars = sum(len(p.text) for p in doc.paragraphs)
    images = sum(1 for p in doc.paragraphs for r in p.runs
                 if r._element.findall(qn("w:drawing")))
    print(f"已生成：{OUTPUT}")
    print(f"段落 {paragraphs} 个，正文约 {chars} 字，图片 {images} 张，表格 {len(doc.tables)} 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
