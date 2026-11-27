# Author: 郝津德
"""按《报告封面结构及评分标准》（2026-11 修订版）生成实验报告 docx。

用法：
    python scripts/make_report.py

产物：docs/实验报告.docx（覆盖），结构为
    封面 → 摘要 → 目录（TOC 域，Word 打开自动更新页码）→ 六章正文 → 致谢 → 参考文献

封面字段与章节编号严格对齐老师模板：
    1 项目概述与团队分工（1.1 背景目标 / 1.2 分工表 / 1.3 工具链）
    2 需求分析（2.1 业务流程图 / 2.2 用例图 / 2.3 FR 与 NFR）
    3 系统设计（3.1 架构图 / 3.2 模块图 / 3.3 数据库 / 3.4 接口文档）
    4 编码实现与版本控制（4.1 状态机 / 4.2 下单事务 / 4.3 其他要点 / 4.4 Git / 4.5 代码规范）
    5 测试与质量保证（5.1 策略 / 5.2 用例表 / 5.3 缺陷 / 5.4 并发 / 5.5 反馈修复）
    6 项目总结与反思（6.1 亮点与不足 / 6.2 改进 / 6.3 个人贡献度）

字体与版式：正文宋体小四、行距 1.5、首行缩进 2 字符；标题黑体；
A4 纸张，页边距上下 2.54 cm、左右 2.5 cm；正文节带「第 X 页」页脚，封面无页码。
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS = PROJECT_ROOT / "docs"
FIGURES = DOCS / "figures"
OUTPUT = DOCS / "实验报告.docx"

SONG, HEI, MONO, WEST = "宋体", "黑体", "Consolas", "Times New Roman"

# 姓名、学号、角色与提交数。提交数口径：git shortlog -sn HEAD @ c1f2190，
# 合计 52 次；报告文档自身的提交不计入，避免「统计对象包含统计结果」的循环。
MEMBERS = [
    ("郝津德", "2518040124", "组长 / 后端架构", "35"),
    ("王昱皓", "2518040121", "前端负责人", "4"),
    ("杨云凇", "2518040214", "商品模块", "4"),
    ("安远", "2518040216", "测试与文档", "9"),
]

COURSE = "操作系统与工具链"
COLLEGE = "安德学院"
CLASS_NAME = "计算机（安德）2501 班"
TEACHER = "王 佳 婧"
DATE_CN = "2026 年 11 月 30 日"


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
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
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
    # 整表尽量不跨页：所有行都设「与下段同页」，
    # 末行也设，是为了让紧随其后的表题不会单独掉到下一页成孤行。
    # 表格比一页还高时 Word 会自动放弃该约束，不会造成排版错乱。
    for row in t.rows:
        for cell in row.cells:
            for cp in cell.paragraphs:
                cp.paragraph_format.keep_with_next = True
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
    # 目录条目样式由 Word 首次更新域时生成（默认模板里没有 TOC 1/2），
    # 因此压行距的动作放在 scripts/build_pdf.ps1 里，先更新域再改样式。
    for name, size in (("Heading 1", 16), ("Heading 2", 14)):
        style = doc.styles[name]
        style.font.name = WEST
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string("000000")
        style.element.rPr.rFonts.set(qn("w:eastAsia"), HEI)


# ---------------------------------------------------------------- 封面


def build_cover(doc) -> None:
    """按老师模板生成封面：单语种、姓名与学号同行、四人逐行列出。"""
    for _ in range(2):
        para(doc, "", indent=False, space_after=6)

    para(doc, "课程实验报告", size=30, bold=True, name=HEI,
         align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, space_after=6, line=1.3)
    para(doc, "", indent=False, space_after=54)

    # 标签用固定制表位右对齐到同一列，值从 4.9 cm 处起排，四人姓名与学号自然对齐
    rows = [
        ("课 程 名 称：", COURSE),
        ("院　　（系）：", COLLEGE),
        ("专 业 班 级：", CLASS_NAME),
    ]
    for label, value in rows:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after = Pt(14)
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.left_indent = Cm(2.6)
        p.paragraph_format.tab_stops.add_tab_stop(Cm(4.9))
        set_run(p.add_run(label), HEI, 13, True)
        set_run(p.add_run("\t"), SONG, 13)
        set_run(p.add_run(value), SONG, 13)

    for i, (name, sid, _, _) in enumerate(MEMBERS):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.left_indent = Cm(2.6)
        p.paragraph_format.tab_stops.add_tab_stop(Cm(4.9))
        p.paragraph_format.tab_stops.add_tab_stop(Cm(7.0))
        label = "学 生 姓 名：" if i == 0 else "　　　　　　"
        set_run(p.add_run(label), HEI, 13, i == 0)
        set_run(p.add_run("\t"), SONG, 13)
        set_run(p.add_run(name), SONG, 13)
        set_run(p.add_run("\t"), SONG, 13)
        set_run(p.add_run(sid), SONG, 13)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(14)
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.left_indent = Cm(2.6)
    p.paragraph_format.tab_stops.add_tab_stop(Cm(4.9))
    set_run(p.add_run("授 课 教 师："), HEI, 13, True)
    set_run(p.add_run("\t"), SONG, 13)
    set_run(p.add_run(TEACHER), SONG, 13)

    para(doc, "", indent=False, space_after=40)
    para(doc, DATE_CN, size=13, name=SONG,
         align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, space_before=24)


# ---------------------------------------------------------------- 摘要与目录


def build_abstract(doc) -> None:
    """摘要与关键词。"""
    plain_title(doc, "摘　要")
    para(doc,
         "本报告完整记录校内二手交易平台「闲置集市」从需求分析、系统设计、编码实现到测试交付的全过程。"
         "系统后端采用 FastAPI + SQLAlchemy 2.0 + MySQL 8.0，前端采用原生 HTML、CSS 与 JavaScript，"
         "不使用任何构建工具，后端通过静态文件挂载实现同源部署，因此不存在跨域配置。"
         "共实现 24 条 API 路径、30 个接口与 14 个页面，覆盖账号、商品、订单与互动四个领域。")
    para(doc,
         "设计上把订单状态机收敛为「当前状态 + 目标状态 + 角色」三元组的单一事实源，"
         "权限校验与前端按钮都由它派生；下单在单事务内以 SELECT … FOR UPDATE 锁定商品行，"
         "使并发抢购只能有一个事务成交。"
         "测试以 pytest 与 FastAPI TestClient 编写 110 项用例，覆盖正常流、边界值与异常流，"
         "其中五个买家并发抢购在真实 MySQL 上验证为一单成功、四单返回 409。")
    para(doc,
         "项目全程使用 Git 管理，按十一个阶段分批入库，共 52 次提交（截至 c1f2190），本地仓库与远程仓库保持同步。"
         "报告按老师给定的章节结构组织：需求分析给出业务流程图与用例图，系统设计给出分层架构、"
         "功能模块、ER 与接口文档，编码实现部分逐一说明两个技术难点，"
         "最后按人统计贡献度并给出改进方向。")
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


# ---------------------------------------------------------------- 第一章


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

    heading(doc, "1.2　团队角色分工表", 2)
    para(doc,
         "四名成员按「一个人负责一段可以独立验收的链路」划分，"
         "每段都包含从路由到页面或从用例到缺陷记录的完整闭环，避免出现只做一半的中间态。"
         "分工表明确到文件与模块，不出现「共同完成」这类无法追责的表述；"
         "表 1-1 中的提交数由 git shortlog 直接统计，不是估算。")
    table(doc,
          ["姓名", "角色", "主责模块（文件）", "具体交付", "提交数"],
          [["郝津德", "组长 / 后端架构",
            "core、models、services（订单/状态机/消息/收藏）、sql、交付脚本",
            "七张表 ORM、JWT 鉴权与统一异常、三元键状态机、行锁防超卖、上传服务、报告与打包脚本",
            "35"],
           ["王昱皓", "前端负责人",
            "css/style.css、js/api.js、js/common.js、登录注册与个人中心",
            "请求封装与 401 统一跳转、导航与页脚注入、全站样式与三档响应式、资料与改密",
            "4"],
           ["杨云凇", "商品模块",
            "routers/services/goods.py、列表/详情/发布/我的商品页",
            "发布与编辑、上下架、软删除、关键词搜索、四种排序与分页",
            "4"],
           ["安远", "测试与文档",
            "tests（110 项用例）、services/reviews.py、订单与互动页",
            "评价模块与评分统计、110 项用例、并发验证、缺陷追踪与接口文档校对",
            "9"]],
          widths=[1.5, 2.2, 4.3, 6.2, 1.8])
    caption(doc, "表 1-1　团队角色分工与提交情况（截至 c1f2190，共 52 次提交）")
    para(doc,
         "计划贡献比例为 35%／22%／22%／21%，该比例用于分配工作量，"
         "不作为实际贡献的既成结论。实际贡献应以提交内容、代码审查意见与测试产出综合判断，"
         "不能仅凭文件头的作者标注推定——文件在多人迭代后，"
         "头部作者往往只代表最初创建者。第 6.3 节按人给出代码行数与解决的具体问题。")

    heading(doc, "1.3　开发工具与工具链说明", 2)
    para(doc,
         "项目的工具链围绕「四个人、一台能跑起来的服务器、可复现的交付」来选，"
         "每引入一个依赖都要求能说清它解决了什么问题，避免为课程项目堆砌框架。"
         "版本控制用 Git + GitHub，四人各自配置了学校邮箱身份，提交记录可按人追溯；"
         "编辑器统一 VS Code，接口调试用浏览器 DevTools 与 curl 交替，"
         "不依赖 Postman 集合文件，避免配置文件本身成为交付负担。")
    para(doc,
         "运行环境是 Python 3.12+ 虚拟环境与 MySQL 8.0。数据库选择 MySQL 而非 SQLite 的原因很具体："
         "并发下单需要 InnoDB 的行锁与事务，SQLite 的锁粒度不同，"
         "在 SQLite 上通过的并发用例不能说明 MySQL 上也能通过。"
         "所有表使用 utf8mb4，避免中文与 emoji 写入报错。表 1-2 汇总了选型与理由。")
    table(doc,
          ["工具 / 组件", "版本或形态", "在本项目中的作用"],
          [["Python + venv", "3.12+", "后端语言；虚拟环境隔离依赖，requirements.txt 锁定版本"],
           ["FastAPI", "0.11x", "以类型注解声明入参与出参，校验与 OpenAPI 文档自动生成"],
           ["SQLAlchemy", "2.0", "声明式模型描述七张表；with_for_update 生成行锁"],
           ["MySQL", "8.0 / InnoDB", "真实外键约束与行锁，是并发用例的前提"],
           ["Uvicorn", "标准启动", "ASGI 服务器；静态目录与 /api 同源部署"],
           ["HTML + CSS + 原生 JS", "Bootstrap 5 CDN", "课程要求传统前端；无 Node 构建，浏览器直接跑"],
           ["JWT + bcrypt", "HS256", "无状态鉴权；密码只存 bcrypt 哈希"],
           ["pytest + TestClient", "8.x", "进程内发真实 HTTP 请求，覆盖鉴权与状态码"],
           ["Git + GitHub", "main 单分支", "按阶段分批提交，远程同步，可按人统计提交"],
           ["VS Code", "—", "统一编辑器；用 DevTools 网络面板逐个核对请求"],
           ["Pillow / python-docx", "—", "生成七张设计图与实验报告，保证图与文同源"],
           ["PowerShell COM", "Word", "更新目录域并导出 PDF，用于交付前视觉核对"]],
          widths=[4.2, 3.4, 9.2])
    caption(doc, "表 1-2　技术栈与工具链")

    para(doc,
         "开发节奏按十一个阶段推进，每个阶段结束时把当日范围内的文件单独入库，"
         "并且禁止使用 git add -A，避免把本地配置或临时脚本带进仓库。"
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
           ["D10", "需求流程图与用例图、报告正文与七张图入册", "全员"],
           ["D11", "按新版封面与章节规范重排报告，收尾打包", "郝津德"]],
          widths=[2.2, 10.4, 3.2])
    caption(doc, "表 1-3　按阶段分批入库的计划")


# ---------------------------------------------------------------- 第二章


def build_chapter2(doc) -> None:
    """第二章：需求分析（流程图 + 用例图 + FR/NFR）。"""
    heading(doc, "2　需求分析", 1)

    heading(doc, "2.1　核心业务流程图", 2)
    para(doc,
         "系统只有一种账号，但同一账号在不同订单中扮演不同角色："
         "发布商品时是卖家，下单时是买家。不做角色分离的原因是校园交易的实际情况——"
         "卖出一台旧键盘的学生往往同时想买一本二手教材，"
         "要求注册两个账号会直接劝退用户。角色因此在订单上下文中判定，"
         "而不是在账号上固化。图 2-1 按「谁在动作」给每一步标了责任人，"
         "可以看到主流程只有七个节点，其中三个由系统（含事务）完成。")
    figure(doc, "fig5_flow.png", "图 2-1　核心业务流程图（向右为失败分支）")
    para(doc,
         "主流程是：卖家发布商品并进入在售 → 买家浏览与搜索 → 打开详情下单 → "
         "系统在一个事务内锁定商品行、校验、建单并把商品置为已售 → "
         "卖家确认出售 → 买家线下付款并确认收货 → 买家评价卖家。"
         "收藏与私信是浏览后的支线，不改变订单状态，因此不影响主链路的正确性。")
    para(doc,
         "流程图上两个判断节点是整个系统的关键分歧点。第一个是「在售且非自购」，"
         "不通过就返回 409 或 400，事务回滚，商品仍可被别人买走；"
         "第二个是「卖家确认出售」，不通过时订单转为已取消、商品回到在售，可以再次成交。"
         "把两个分支画出来，是为了说明系统在什么情况下不继续——"
         "这比只画成功路径更能反映实现。")
    para(doc,
         "未完成的订单可以取消：买家在待确认阶段可撤销，卖家可拒绝，待付款阶段双方均可取消；"
         "已完成订单只能申请退款，商品不再上架——交易已实际发生，"
         "改回在售会造成同一件物品被卖两次。")

    heading(doc, "2.2　用例图", 2)
    para(doc,
         "图 2-2 把角色与用例的对应关系画清楚。三个角色是游客、买家与卖家，"
         "其中游客只能浏览与搜索，注册登录后按订单上下文切换买家与卖家身份。"
         "这样画而不是画成三个互斥角色，是因为实现上只有一个 users 表，"
         "没有 role 字段——角色是推导出来的，不是存储的。")
    figure(doc, "fig6_usecase.png", "图 2-2　系统用例图（三个角色与 12 个用例）")
    table(doc,
          ["角色", "可用用例", "约束"],
          [["游客（未登录）", "浏览商品列表、搜索与排序、查看商品详情、查看卖家主页与评分",
            "下单、收藏、私信、评价均被 401 拦截并跳转登录"],
           ["买家（登录后）", "下单购买、确认收货、取消订单、申请退款、收藏、私信卖家、评价卖家",
            "只能操作自己作为买家的订单；评价仅限已完成的订单"],
           ["卖家（登录后）", "发布商品、编辑与上下架、删除（软删除）、确认出售或拒绝、查看我的商品与订单",
            "只能操作自己发布的商品；已售商品不可编辑"],
           ["共用", "注册、登录、修改资料、修改密码、查看未读消息", "改密码需核验原密码"]],
          widths=[3.0, 8.6, 5.2])
    caption(doc, "表 2-1　角色与用例的对应关系")
    para(doc,
         "用例之间存在三条隐含的前置约束，写在图上会显得拥挤，因此在实现中体现："
         "下单要求商品处于在售且下单人不是卖家；评价要求订单已完成且当前用户是买家；"
         "收藏只允许对在售商品发起，商品下架后再点收藏返回 404。"
         "这三条都写在服务层，页面只根据接口返回的 available_actions 决定按钮是否出现，"
         "不做第二套判断。")

    heading(doc, "2.3　功能需求与非功能需求", 2)
    para(doc,
         "功能需求按模块整理为表 2-2，优先级用 P0／P1 表示：P0 为缺此功能系统不成立，"
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
    caption(doc, "表 2-2　功能需求清单（FR）")

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
    caption(doc, "表 2-3　非功能需求与对应实现（NFR）")


# ---------------------------------------------------------------- 第三章


def build_chapter3(doc) -> None:
    """第三章：系统设计（架构、模块、数据库、接口）。"""
    heading(doc, "3　系统设计", 1)

    heading(doc, "3.1　系统架构图", 2)
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
    para(doc,
         "部署上只有一个进程：uvicorn 同时提供 /api 接口与 frontend 目录下的静态页面。"
         "静态挂载必须注册在所有 /api 路由之后，否则通配挂载会把接口请求一并吃掉，"
         "表现为所有接口都返回 404。这个顺序在 app/main.py 里用注释固定下来，"
         "避免后续有人调整 import 顺序时再次踩坑。")

    heading(doc, "3.2　功能模块图", 2)
    para(doc,
         "模块按可分配粒度拆分，每个模块都对应到明确的文件，且标注了负责人，"
         "与表 1-1 的分工一致。这样划分的好处是模块边界与文件边界重合，"
         "合代码时冲突面小；坏处是「评价」这类横跨订单与用户的模块需要复用订单服务的校验，"
         "为此把状态判断抽到 order_state.py 供多方调用，避免复制条件判断。")
    figure(doc, "fig3_modules.png", "图 3-2　功能模块划分与责任人")

    heading(doc, "3.3　数据库设计", 2)
    para(doc,
         "数据库共七张表：users、categories、goods、orders、reviews、favorites、messages。"
         "图 3-3 标出主键、外键、唯一键与联系基数，14 条外键全部在 MySQL 中建为真实约束——"
         "只在代码里拼字段不会在写入时报错，等查出孤儿数据时代价更高。")
    figure(doc, "fig1_er.png", "图 3-3　数据库实体联系图（PK 主键、FK 外键、UK 唯一键）")
    table(doc,
          ["表名", "作用", "关键字段与约束"],
          [["users", "账号与公开资料", "username UK；password_hash 存 bcrypt；avatar_url、rating 汇总"],
           ["categories", "商品分类", "name；parent_id 自引用 FK，支持两级分类"],
           ["goods", "商品", "seller_id FK→users、category_id FK→categories；status 在售/已售/已下架；images 存逗号分隔文件名"],
           ["orders", "订单", "goods_id FK、buyer_id FK、seller_id FK；status 四态；(buyer_id,status) 建索引"],
           ["reviews", "评价", "order_id UK（一单一评）；goods_id FK、reviewer_id FK、reviewee_id FK；score 1–5"],
           ["favorites", "收藏", "(user_id, goods_id) 联合 UK，重复收藏在并发下也不会插两行"],
           ["messages", "站内私信", "sender_id FK、receiver_id FK；is_read；(receiver_id,is_read) 支撑未读统计"]],
          widths=[2.6, 3.4, 10.8])
    caption(doc, "表 3-1　七张表的主要结构与约束")
    para(doc,
         "关键约束有四条：users.username 唯一，从数据库层杜绝重复注册；"
         "favorites 的 (user_id, goods_id) 联合唯一，靠数据库消除并发重复收藏；"
         "reviews.order_id 唯一，保证一单一评；"
         "orders 与 reviews 对 goods 的外键让历史订单始终能取到商品。"
         "索引按查询路径建：goods(status, created_at)、goods(category_id)、"
         "orders 的买卖双方与状态、messages(receiver_id, is_read)。")
    para(doc,
         "商品采用软删除：删除只把状态置为「已下架」。物理删除会让历史订单引用的商品变成空值，"
         "订单详情与评价都失去指代对象；代价是列表查询必须始终带 status 条件。")

    heading(doc, "3.4　接口文档", 2)
    para(doc,
         "接口共 24 条路径、30 个接口，按模块分为六组，逐条的请求参数、返回结构与错误码见 "
         "docs/接口文档.md。三条约定：受保护接口统一从 Authorization 头取 Bearer 令牌，"
         "不接受前端传入的用户 ID；列表接口统一返回 items／total／page／size；"
         "字段校验失败统一改写为 400 而非框架默认的 422。")
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
         "以最核心的下单接口为例：请求为 POST /api/orders，体里只有 goods_id 与留言；"
         "成功返回 201 与订单对象，订单对象内嵌 available_actions 数组，"
         "每项包含 label、to_status 与 style，前端直接用它渲染按钮。"
         "失败则按语义返回 400／401／403／404／409 五种之一，响应体统一为 "
         "{\"detail\": \"中文说明\"}。")
    table(doc,
          ["状态码", "语义", "典型场景", "前端处理"],
          [["400", "参数不合法", "标题为空、价格为负、标题超 161 字", "直接展示 detail 文案"],
           ["401", "未登录或令牌失效", "未带令牌、令牌过期、签名被篡改", "清登录态，跳登录页并记住原地址"],
           ["403", "已登录但无权", "改别人的商品、确认别人的订单", "提示无权，不跳转"],
           ["404", "资源不存在", "商品已下架、订单编号不存在", "引导返回列表"],
           ["409", "状态冲突", "商品已被抢购、订单已评价、非法流转", "提示后刷新当前数据"]],
          widths=[2.0, 3.4, 6.6, 4.8])
    caption(doc, "表 3-3　错误码语义与前端处理方式")
    para(doc,
         "把 403 与 409 分开是有意为之：旧实现里两类错误都返回 400，用户只看到同一句「操作失败」，"
         "分不清是没资格还是时机不对。分开后越权给 403（换个人来做就能成），"
         "状态冲突给 409（等一会儿或换对象），前端只读 detail 一个字段即可判定后续动作。")


# ---------------------------------------------------------------- 第四章


def build_chapter4(doc) -> None:
    """第四章：编码实现与版本控制。"""
    heading(doc, "4　编码实现与版本控制", 1)

    heading(doc, "4.1　核心技术难点一：订单状态机", 2)
    para(doc,
         "订单有四个状态：待确认、待付款、已完成、已取消。图 4-1 给出六条合法转移，"
         "每条转移都绑定一个可以执行它的角色。"
         "这个设计的关键在于键的选择：只用「当前状态 → 目标状态」无法区分同一跳转由谁触发，"
         "例如待确认 → 已取消既可以是买家撤销，也可以是卖家拒绝，"
         "两者都合法但权限不同。因此键定为三元组，加入角色维度。")
    figure(doc, "fig4_order_state.png", "图 4-1　订单状态机与六条合法转移")
    table(doc,
          ["当前状态", "目标状态", "可执行角色", "业务含义"],
          [["待确认", "待付款", "卖家", "卖家确认出售"],
           ["待确认", "已取消", "卖家", "卖家拒绝交易"],
           ["待确认", "已取消", "买家", "买家主动撤销"],
           ["待付款", "已完成", "买家", "买家付款并确认收货"],
           ["待付款", "已取消", "买家", "买家取消未付款订单"],
           ["已完成", "已取消", "买家", "申请退款（商品不回滚）"]],
          widths=[2.8, 2.8, 2.8, 7.0])
    caption(doc, "表 4-1　六条合法状态转移及其角色约束")
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
    para(doc,
         "权限判断分两步：先看这条转移是否在表中，不在则返回 409，"
         "表示当前状态不允许该操作；再看请求者角色是否匹配，不匹配返回 403，表示无权。"
         "两步分开的意义在于错误提示不同：409 告诉用户「这个操作现在做不了」，"
         "403 告诉用户「你没资格做这个操作」，用户不至于对着「操作失败」反复重试。")

    heading(doc, "4.2　核心技术难点二：防超卖的下单事务", 2)
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

    heading(doc, "4.3　其他实现要点", 2)
    para(doc,
         "搜索先按「在售」过滤，再叠加关键词与分类条件，用相同条件统计总数，"
         "最后按四种固定排序之一排序并分页。排序值只接受 newest、price_asc、price_desc、hot，"
         "由服务层映射到具体的 order_by，绝不把用户输入拼进 SQL，"
         "避免注入，也避免某个拼写错误的排序值导致全表扫描。")
    para(doc,
         "统计总数与取当页数据使用同一套过滤条件，是为了保证分页信息自洽："
         "若两处条件写法不同，会出现「总数 20 条但翻到第 3 页只有 2 条」的情况，"
         "用户会以为数据丢了。实现上把过滤条件构造抽成内部函数，两处共用。")
    para(doc,
         "前端 14 个页面共用三个文件：api.js 负责所有网络请求，common.js 负责导航、页脚、"
         "登录校验与提示，style.css 负责配色与组件。api.js 在请求前统一注入 Bearer 令牌，"
         "遇到 401 清除本地登录态并跳转登录页，遇到其他错误弹出后端返回的中文提示；"
         "因为后端把字段校验错误从 422 改写为 400，前端只需处理一套错误结构。")
    para(doc,
         "导航栏的消息未读数原本是个写死的红点，永远亮着，用户很快就学会忽略它。"
         "联调时改为调用 /api/messages/unread-count 取真实数字：为零不显示，"
         "有未读才显示数量。这个接口此前已在文档里列出却从未被调用，"
         "属于典型的「文档有、代码无」，也说明接口文档需要在联调阶段逐条对账。")

    heading(doc, "4.4　Git 提交历史与分支管理", 2)
    para(doc,
         "仓库使用 main 单分支，不做特性分支。原因是四人并行且文件边界清晰，"
         "模块之间几乎没有交叉修改，单分支配合每日小步提交的冲突成本低于维护多条分支的合并成本。"
         "四人各自配置学校邮箱身份，提交记录可按人追溯；本地与远程保持同步，"
         "每次阶段收尾都先 pull 再 push，避免出现孤儿提交。")
    figure(doc, "fig7_gitlog.png", "图 4-2　Git 提交历史（git log 导出，截取至 c1f2190，最近 18 条，按提交人着色）")
    para(doc,
         "提交信息统一采用「类型(模块): 说明」格式，类型取值 feat、fix、test、docs、style、refactor、chore。"
         "提交内容遵循两条纪律：一是不使用 git add -A 或 git add .，"
         "每次按文件清单精确添加，避免把本地配置或临时脚本带进仓库；"
         "二是提交信息说明取舍原因而不只是结果，"
         "例如「先判归属再判状态」这类改动，半年后回看仍能明白为什么改。"
         "表 4-2 为各类型提交的实际分布。"
         "统计口径上，表 1-1 与第 6 章的提交数一律截至 c1f2190（第 52 次提交）："
         "报告本身也是被提交的对象，若把「生成报告的这几次提交」也计入统计，"
         "每改一次稿总数就要改一次，等于统计对象包含统计结果，永远对不齐；"
         "故文档类提交不计入口径，读者用 git log 查到 c1f2190 即可复算。")
    table(doc,
          ["类型", "含义", "示例"],
          [["feat", "新增功能模块", "feat(订单): 实现状态机流转与防超卖下单事务"],
           ["fix", "修复缺陷或口径不一致", "fix(订单): 统一订单时间时钟并修正下单校验顺序"],
           ["test", "补充或调整测试", "test(质量): 覆盖异常流并补齐上传接口用例"],
           ["docs", "文档、注释与过程记录", "docs(过程): 记录 D7 联调发现的七处问题与修复"],
           ["style", "样式与排版，不改逻辑", "style(前端): 统一十四页样式与响应式断点"],
           ["refactor", "重构，行为不变", "refactor(消息): social.py 只留消息与收藏"],
           ["chore", "构建、脚本与杂项", "chore(交付): 交付包同时放入报告 PDF"]],
          widths=[2.2, 5.0, 8.2])
    caption(doc, "表 4-2　提交类型约定")
    para(doc,
         "提交节奏与开发阶段对应：D1 建骨架与数据模型，D2 做鉴权基建，"
         "D3 至 D5 按模块逐个落地，D7 之后进入联调与测试，每个修复单独成一条提交并注明所属缺陷。"
         "这样即使不看代码，只读提交历史也能还原「哪一天做了什么、为什么改」。"
         "完整的 52 条记录与每人明细见 docs/进度日志.md，"
         "阶段划分见前文表 1-3。")

    heading(doc, "4.5　代码规范说明", 2)
    para(doc,
         "命名规范：Python 模块与函数用小写下划线，类用大驼峰，常量全大写；"
         "数据库表名用复数、字段用小写下划线，与 ORM 模型一一对应，避免出现 "
         "goodsList 与 goods_list 混用；路由按领域前缀分组（/api/goods、/api/orders），"
         "同一资源的方法集中在一个文件。前端 id 用中划线命名，JavaScript 函数以动词开头，"
         "渲染函数统一叫 xxxPage()，与页面一一对应。")
    para(doc,
         "分层规范：routers 只做参数校验、依赖注入与调用服务，不允许出现 SQL 语句；"
         "services 承载全部业务判断，一个函数只做一件事，事务边界写在服务层；"
         "models 只描述表结构与关系，不写业务方法。这条约束的实际作用在排查问题时体现："
         "接口返回不对，先看 router 的入参，再看 service 的逻辑，"
         "不需要在三个文件之间反复跳。")
    para(doc,
         "注释规范：只在「为什么」处写注释，不写「是什么」。「先判归属再判状态，"
         "否则卖家会看到『已被抢购』」这类说明取舍的注释保留，复述代码的注释一律删除；"
         "每个文件头部标注 Author，复杂分支与魔法数字必须给出原因。")
    para(doc,
         "格式与提交规范：Python 单行不超过 100 字符，导入分标准库、第三方、本项目三组；"
         "前端两空格缩进。提交遵循「一次提交一件事」，信息用中文写清模块与原因，"
         "纯格式改动单独提交并标注 style，避免与逻辑改动混在一起无法回退。")


# ---------------------------------------------------------------- 第五章


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

    heading(doc, "5.2　测试用例表", 2)
    para(doc,
         "当前共 110 项用例，0 项跳过，按文件分布如表 5-1。"
         "正常流约占三成，边界值与异常流合计约七成，这是刻意的：正常流一旦跑不通，"
         "开发时立刻就会知道；异常流才是长期潜伏的地方。")
    table(doc,
          ["测试文件", "项数", "正常流", "边界值", "异常流", "主要覆盖点"],
          [["test_auth.py", "27", "7", "10", "10", "注册登录改密、令牌校验、字段长度上下界、资料全量替换语义"],
           ["test_goods.py", "32", "9", "12", "11", "发布编辑上下架、出参完整性、价格与标题边界、分页与排序"],
           ["test_orders.py", "20", "5", "5", "10", "下单、重复成交、越权、非法流转、各类取消与退款"],
           ["test_flow.py", "2", "2", "0", "0", "一次完整交易的六次流转、可用操作与状态机一致性"],
           ["test_api.py", "14", "7", "1", "6", "接口清单与静态页面、错误码、软删除、收藏与消息"],
           ["test_upload.py", "14", "3", "4", "7", "上传鉴权、类型白名单、体积上限、魔术字节、文件名安全"],
           ["test_mysql_concurrency.py", "1", "1", "0", "0", "五买家并发抢购，真实 MySQL 行锁验证"],
           ["合计", "110", "34", "32", "44", "0 项跳过"]],
          widths=[4.6, 1.4, 1.4, 1.4, 1.4, 5.8])
    caption(doc, "表 5-1　测试用例分布（按正常流、边界值、异常流分类）")

    para(doc,
         "为了让用例表能直接验收，表 5-2 抽了 12 条代表性用例，"
         "每条都写明前置条件、操作与预期结果，可与 tests/ 下的函数一一对应。")
    table(doc,
          ["类别", "前置条件", "操作", "预期结果"],
          [["正常流", "已注册用户", "正确用户名密码登录", "200，返回 access_token 与用户信息"],
           ["正常流", "卖家已发布在售商品", "另一用户下单", "201，商品转为已售，订单状态待确认"],
           ["正常流", "订单为待付款", "买家确认收货", "200，状态转已完成，商品保持已售"],
           ["正常流", "订单已完成", "买家提交 5 星评价", "201，一单一评生效，卖家均分更新"],
           ["边界值", "用户名 3 位 / 50 位", "注册", "均 200，上界与下界都可用"],
           ["边界值", "用户名 2 位 / 51 位", "注册", "400，提示长度不合法"],
           ["边界值", "图片 5 MB / 5 MB + 1 字节", "上传", "前者 200，后者 400"],
           ["边界值", "分页 size=100 / 101", "请求列表", "前者 200，后者 400"],
           ["异常流", "同一商品已被下单", "第二个买家再下单", "409，提示商品已被抢购"],
           ["异常流", "买家下单自己的商品", "下单", "400，提示不能购买自己发布的商品"],
           ["异常流", "令牌被篡改", "访问受保护接口", "401，前端清登录态跳登录"],
           ["异常流", "非订单参与者流转状态", "调用状态接口", "403，提示无权操作"]],
          widths=[1.8, 4.4, 4.4, 5.8])
    caption(doc, "表 5-2　正常流、边界值与异常流的代表性用例")

    heading(doc, "5.3　缺陷追踪记录与修复情况", 2)
    para(doc,
         "开发过程中记录并修复了九个问题，完整记录见 docs/Bug追踪.md。"
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

    heading(doc, "5.4　并发验证", 2)
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

    heading(doc, "5.5　用户反馈驱动的修复", 2)
    para(doc,
         "联调阶段按真实操作路径逐页走查，发现并修复了七处问题，"
         "其中多数不属于功能错误，而是「能用但不好用」："
         "订单详情把已取消订单的结束时间标成「完成时间」，看着像交易成功；"
         "商品列表首次打开会带上空的分类参数；"
         "评价内容可以只填空格；下单时买自家商品提示「已被抢购」。"
         "这类问题自动化测试很难覆盖，必须有人在真实界面上操作才会遇到，"
         "也因此说明手工走查与自动化测试不能互相替代。")


# ---------------------------------------------------------------- 第六章


def build_chapter6(doc) -> None:
    """第六章：亮点与不足、改进方向、个人贡献度。"""
    heading(doc, "6　项目总结与反思", 1)

    heading(doc, "6.1　项目亮点与不足", 2)
    para(doc,
         "对照表 2-2 的功能需求，全部 P0 项与 P1 项均已实现并通过测试。"
         "系统可在一台装有 MySQL 8.0 的机器上以三条命令启动："
         "执行 sql/init.sql 建库建表、运行 scripts/init_db.py 写入分类与演示账号、"
         "以 uvicorn 启动服务，浏览器访问 /pages/index.html 即可使用。"
         "14 个页面全部可访问，24 条接口路径全部注册，110 项测试全部通过且无跳过。")
    table(doc,
          ["项目", "目标", "实际"],
          [["接口", "覆盖账号、商品、订单、互动", "24 条路径 / 30 个接口"],
           ["页面", "14 个页面可访问", "14 个页面全部返回 200"],
           ["测试", "正常流、边界值、异常流", "110 项通过，0 跳过"],
           ["并发", "同一商品只能成交一次", "5 并发：1 单 201、4 单 409"],
           ["状态机", "规则只写一处，前后端一致", "6 条转移，按钮由 available_actions 生成"],
           ["版本控制", "按阶段分批入库，本地与远程同步", "截至 c1f2190 共 52 次提交，main 一致"]],
          widths=[2.6, 6.4, 6.4])
    caption(doc, "表 6-1　目标与完成情况对照")

    para(doc,
         "亮点集中在三处。第一是状态机的单一事实源：规则表同时承担权限表与按钮配置表的作用，"
         "改一处即可三处生效，这是本项目唯一一个「设计上省了力气」的地方。"
         "第二是并发一致性用数据库解决并通过真实 MySQL 验证，而不是靠前端禁用按钮假装安全。"
         "第三是文档与代码同源：七张图与报告都由脚本生成，"
         "图上的模块、责任人、提交数与代码一致，不会出现「文档说 68 项测试、"
         "实际 110 项」这类对不上的情况。")
    para(doc,
         "不足也有三处。其一是支付环节完全缺失：「确认收货」只是状态演示，"
         "没有真实资金流转，退款也只改状态、线下另行结算，"
         "因此订单超时自动取消、二维码收款这类机制都无从谈起。"
         "其二是消息功能只做了最基础的收发与未读计数，没有分页、没有图片、没有撤回，"
         "长会话会一次性返回全部记录。其三是图片上传只落本地磁盘，没有压缩也没有对象存储，"
         "换机部署时 uploads 目录必须手工迁移。")
    para(doc,
         "还有一处属于分工口径的不足：商品模块的代码行数（245 行）明显低于其他三人，"
         "与其 22% 的计划占比并不匹配。原因不是工作没做，而是这个模块的实现最薄——"
         "后端逻辑被订单与状态机吸收，前端页面逻辑又集中在公共的 pages.js 里，"
         "按文件统计时两部分都不落在它名下。这件事故意写出来："
         "它说明「按文件横切分工」会让行数统计失真，也说明行数本身不是可靠的贡献度量。")

    heading(doc, "6.2　改进方向", 2)
    para(doc,
         "如果重做一次，技术上的优先级从高到低是：接入对象存储并做图片压缩（解决部署与带宽问题）、"
         "给消息加分页与已读回执（解决可用性问题）、"
         "引入支付回调与订单超时任务（补全交易闭环）、"
         "增加操作审计日志（便于纠纷追溯）。"
         "此外，前端目前是原生 JavaScript 直接操作 DOM，"
         "页面数量再增长时维护成本会上升，届时可考虑引入轻量组件化方案，"
         "但现阶段引入框架的收益不足以抵消构建复杂度。")
    para(doc,
         "过程管理上的改进更值得写。第一，分工应从「按文件横切」改为「按功能纵切」，"
         "让每人负责一条从接口到页面再到用例的完整链路，而不是把后端、前端、测试切成三块——"
         "后者会让商品这类「逻辑薄、接口宽」的模块在统计上吃亏。"
         "第二，贡献度不应该只用行数衡量，应同时记录接口数、页面数、用例数与缺陷修复数。"
         "第三，测试应该在写实现之前先写失败用例，本项目多数异常流用例是事后补的，"
         "如果用例先行，BUG-03（状态机键设计不足）在编码阶段就会暴露，"
         "不至于等到写测试时才发现要改数据结构。")
    para(doc,
         "第四，Git 上可以更细：目前是 main 单分支，虽然冲突少，"
         "但无法体现「评审后合并」的过程。若时间充裕，"
         "可为每个阶段开一个短生命周期分支，由组长做一次合并前的代码走查，"
         "既保留提交密度，也能在协作痕迹上更完整。")

    heading(doc, "6.3　个人贡献度总结", 2)
    para(doc,
         "表 6-2 按人统计代码行数、提交数与解决的具体问题。行数口径为"
         "「本人主责文件的物理行数（wc -l，含注释与空行）」，按表 1-1 的模块归属汇总，"
         "由 scripts/count_lines.py 复算——脚本随仓库提交，改完代码重跑即可核对；"
         "frontend/js/pages.js 是四人共写的文件，按 240 行单列、不摊到个人；"
         "郝津德另写 2380 行交付脚本（绘图、报告生成、打包、建库），未计入产品代码。")
    table(doc,
          ["姓名", "代码行数", "提交数", "解决的具体问题", "占比"],
          [["郝津德", "1096", "35",
            "七张表 ORM 与 14 条外键；三元键状态机（BUG-03）；行锁防超卖；静态挂载顺序；统一异常与错误码",
            "35%"],
           ["王昱皓", "1688", "4",
            "401 统一跳转与令牌注入；未读角标接真实数量；三档响应式断点；十四页样式收口", "22%"],
           ["杨云凇", "245", "4",
            "商品 CRUD 与软删除；搜索条件复用使总数与列表自洽；编辑与上下架出参补全", "22%"],
           ["安远", "1557", "9",
            "110 项用例；上传 14 项并做反向验证（BUG-09）；评价模块；并发用例改读配置（BUG-05）",
            "21%"]],
          widths=[1.6, 2.1, 1.3, 9.1, 1.3])
    caption(doc, "表 6-2　个人贡献度统计（代码行数、提交数与解决的具体问题）")

    para(doc,
         "郝津德（组长，35 次提交，1096 行）：负责项目骨架、七张表设计、鉴权与统一异常、"
         "订单状态机、消息与收藏模块以及最终交付打包。"
         "体会最深的是「先想清楚再写」的收益：状态机的键从二元改三元只改了一个文件，"
         "但如果没有这一步，权限判断会散落到路由与页面里，后续每次改规则都要翻遍全项目。"
         "打包脚本也做成可重复执行的，收工即可刷出可提交的交付物。")
    para(doc,
         "王昱皓（前端负责人，4 次提交，1688 行）：负责前端公共层与用户模块。"
         "14 个页面如果各写一遍请求与错误处理，改一处规则要改十四次，"
         "因此先把 api.js、common.js 与 style.css 三个公共文件做扎实，页面只写渲染。"
         "体会是「未读角标」这类细节很影响可信度：红点永远亮着，用户三天就学会无视它，"
         "接了真实数字之后这个入口才有意义。")
    para(doc,
         "杨云凇（商品模块，4 次提交，245 行）：负责商品模块与五个商品页面。"
         "商品查询的复杂度不在单条 SQL，而在条件组合：关键词、分类、排序、分页任意叠加，"
         "且统计总数与取当页数据必须用同一套过滤条件，否则会出现总数与列表对不上。"
         "体会是先把过滤条件构造成一个可复用的表达式，再让统计与查询共用，"
         "比写两遍更不容易出错。软删除的代价是列表查询必须处处带状态条件。")
    para(doc,
         "安远（测试与文档，9 次提交，1557 行）：负责评价模块、110 项用例与缺陷追踪。"
         "最大的体会是边界值必须成对写：只测「越界被拒」，把最小长度误写成 4 时用例照样全绿，"
         "而三个字的用户名全都注册不了。补上传用例时又发现有个接口零覆盖——"
         "安全校验整段删掉也不会报错，因此补完之后特意做了反向验证。"
         "测试的价值不在数量，而在改错之后它会不会红。")
    para(doc,
         "四个人的共同结论是：难点不在写功能，而在让文档、代码与测试说的是同一件事；"
         "七张图、报告与打包都由脚本生成，让「一致」可以被重复验证。")


# ---------------------------------------------------------------- 致谢与参考文献


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
         "感谢授课教师王佳婧老师在选题、设计文档规范与答辩准备上的指导，"
         "尤其是关于「设计文档要能画出图、且图要与代码对得上」的要求，"
         "促使我们在实现之后回头核对文档与代码的差异，"
         "并因此发现了状态机键设计不足这一实质问题；"
         "也感谢老师在报告结构上给出的明确规范，"
         "使这份报告能按需求、设计、实现、测试、总结的线索组织，而不至于写成流水账。"
         "最后感谢同组三位同学在联调阶段的耐心复核——"
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
        "Object Management Group. OMG Unified Modeling Language Specification 2.5.1[S]. 2017.",
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

    # 不用 doc.add_page_break()：它会产生一个独立的空段落，若上一节正好排到页底，
    # 这个空段落自己就占掉一整页，正文里就出现一整页空白。
    # 改为在下一节的首个段落上设 page_break_before，由 Word 在排版时换页。
    builders = (build_abstract, build_toc, build_chapter1, build_chapter2,
                build_chapter3, build_chapter4, build_chapter5, build_chapter6,
                build_thanks, build_references)
    for index, builder in enumerate(builders):
        start = len(doc.paragraphs)
        builder(doc)
        if index > 0:
            first = next((p for p in doc.paragraphs[start:] if p.text.strip()), None)
            if first is not None:
                first.paragraph_format.page_break_before = True

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
