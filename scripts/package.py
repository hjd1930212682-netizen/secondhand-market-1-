# Author: 郝津德
"""生成最终交付文件夹。

用法：
    python scripts/package.py           # 只生成文件夹
    python scripts/package.py --zip     # 额外打成同名 zip

产物位于项目同级的 交付_二手交易平台/，结构：
    00_先读我.txt        课程信息、组员、启动与验收步骤
    01_源代码/           完整仓库（含 .git，可现场查提交历史）
    02_数据库脚本/       init.sql 与建库说明
    03_实验报告/         实验报告 docx
    04_过程材料/         Git 记录、测试报告、分工、Bug 追踪、接口文档
    05_截图素材/         截图清单（报告配图按此补齐）

脚本可重复执行，每次先清空再重建，因此每天收工后都能刷出一份最新交付物。
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DELIVER_NAME = "交付_二手交易平台"
DELIVER_ROOT = PROJECT_ROOT.parent / DELIVER_NAME

# 打包时排除的目录 / 文件后缀，避免把虚拟环境、密钥、本地库带进交付物
EXCLUDE_DIRS = {".venv", "__pycache__", ".pytest_cache", ".idea", ".vscode", "node_modules"}
EXCLUDE_SUFFIXES = {".db", ".pyc", ".pyo", ".log"}
EXCLUDE_FILES = {".env", "local_dev.db"}


def _ignore(directory: str, names: list[str]) -> set[str]:
    """copytree 的忽略回调：过滤虚拟环境、缓存与本地数据库。"""
    ignored: set[str] = set()
    for name in names:
        path = Path(directory) / name
        if name in EXCLUDE_DIRS or name in EXCLUDE_FILES:
            ignored.add(name)
        elif path.suffix in EXCLUDE_SUFFIXES:
            ignored.add(name)
    return ignored


def _force_remove(func, path, _exc_info) -> None:
    """删除失败时去掉只读属性再试一次。

    Git 把松散对象设为只读，Windows 上 rmtree 会直接跳过，
    残留文件挡住 copytree 的覆盖写入，故在此强制改回可写。
    """
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        pass


def _clean(path: Path) -> None:
    """尽力清空目录内容。

    沙箱或杀毒软件可能锁住个别文件，删除失败时忽略该文件，
    后续复制用覆盖模式写入，避免整个打包流程中断。
    """
    if not path.exists():
        return
    for child in path.iterdir():
        try:
            if child.is_dir():
                shutil.rmtree(child, onerror=_force_remove)
            else:
                os.chmod(child, stat.S_IWRITE)
                child.unlink()
        except OSError:
            continue


def _copy(source: Path, target: Path) -> None:
    """覆盖式复制单个文件；目标被占用时先尝试删除再复制。"""
    if target.exists():
        try:
            target.unlink()
        except OSError:
            pass
    shutil.copy2(source, target)

def _run(command: list[str], output: Path, title: str) -> None:
    """执行命令并把 标准输出+错误 写入文件；失败时写入提示而不是中断打包。"""
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        body = (result.stdout or "") + (result.stderr or "")
        footer = f"\n\n[退出码] {result.returncode}\n"
    except Exception as error:  # noqa: BLE001 打包过程不应因单条命令失败而中断
        body = f"命令执行失败：{command}\n"
        footer = f"\n[异常] {error}\n"
    output.write_text(f"{title}\n生成时间：{_now()}\n{'=' * 60}\n{body}{footer}", encoding="utf-8")


def _now() -> str:
    """返回当前时间的可读字符串。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _write_readme(target: Path) -> None:
    """生成交付说明，交代怎么跑、怎么查、怎么验收。"""
    content = f"""《操作系统与工具链》课程项目 · 最终交付物
==================================================

题目：校园二手交易平台（闲置集市）
方向：方向一 校园生活与服务类
指导教师：王佳婧
小组：郝津德（组长）、王昱皓、杨云凇、安远
生成时间：{_now()}

一、文件夹说明
--------------------------------------------------
00_先读我.txt        本文件
01_源代码/           完整项目仓库，含 .git 提交历史
02_数据库脚本/       MySQL 建库建表脚本与说明
03_实验报告/         实验报告 Word 文档
04_过程材料/         分工说明、Git 记录、测试报告、Bug 追踪、接口文档
05_截图素材/         报告配图清单（提交前请补齐实际截图）

二、怎么跑起来
--------------------------------------------------
1) 建库（已装 MySQL 8.0 时）
   mysql -u root -p < 02_数据库脚本/init.sql

2) 配置连接
   进入 01_源代码/secondhand-market/，复制 .env.example 为 .env，
   把 DATABASE_URL 改成自己的账号密码，例如：
   DATABASE_URL=mysql+pymysql://root:你的密码@127.0.0.1:3306/secondhand_market?charset=utf8mb4

3) 装依赖
   python -m venv .venv
   Windows: .venv\\Scripts\\activate      macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt

4) 建表写种子数据
   python scripts/init_db.py --demo

5) 启动
   uvicorn app.main:app --reload

6) 访问
   前端页面  http://127.0.0.1:8000/pages/index.html
   接口文档  http://127.0.0.1:8000/docs
   健康检查  http://127.0.0.1:8000/api/health

   注意：必须通过 http://127.0.0.1:8000 访问页面，
   直接双击 HTML 文件会因跨域导致接口全部失败。

   演示账号：demo_seller / demo_buyer，密码均为 pass1234

三、没有 MySQL 时的应急方案
--------------------------------------------------
项目支持 SQLite 直接运行，答辩前若环境未就绪可临时使用：
   DATABASE_URL="sqlite:///./local_dev.db" JWT_SECRET="local-dev-secret" \\
     uvicorn app.main:app --reload
（sql/init.sql 仍按 MySQL 8.0 编写，作为正式交付的库表设计依据。）

四、怎么查提交历史
--------------------------------------------------
在 01_源代码/secondhand-market/ 下执行：
   git log --pretty=format:"%ad | %an | %s" --date=format:"%Y-%m-%d %H:%M"
线上快照见 04_过程材料/Git提交记录.txt

五、怎么验证质量
--------------------------------------------------
   pip install -r requirements.txt
   pytest -q
快照见 04_过程材料/测试报告.txt
"""
    (target / "00_先读我.txt").write_text(content, encoding="utf-8")


def _write_shot_list(target: Path) -> None:
    """生成报告配图清单，避免交稿时漏图。"""
    content = """# 截图素材清单

报告 15 分「文档与过程材料」要求截图与最终代码一致，请按下面清单在**最终版本**上截取，
不要使用开发中途的旧图。文件名建议按序号命名，便于排版时对应章节。

## 一、运行与功能截图（对应第 4、5 章）

| 序号 | 截图内容 | 建议文件名 | 对应章节 |
|---|---|---|---|
| 1 | 首页（含分类筛选与商品卡片） | 01_首页.png | 4.2 |
| 2 | 商品列表（搜索结果 + 分页） | 02_商品列表.png | 4.2 |
| 3 | 商品详情（多图切换） | 03_商品详情.png | 4.2 |
| 4 | 发布商品页（含多图上传） | 04_发布商品.png | 4.2 |
| 5 | 登录页（含错误提示） | 05_登录.png | 4.2 |
| 6 | 个人中心（头像与资料） | 06_个人中心.png | 4.2 |
| 7 | 我的商品（在售/已售/下架） | 07_我的商品.png | 4.2 |
| 8 | 我的订单（状态标签与流转按钮） | 08_我的订单.png | 4.3 |
| 9 | 订单详情（状态流转记录） | 09_订单详情.png | 4.3 |
| 10 | 消息中心（未读提醒） | 10_消息中心.png | 4.2 |
| 11 | 我的收藏 | 11_我的收藏.png | 4.2 |
| 12 | 评价页（评分与内容） | 12_评价.png | 4.2 |

## 二、接口与调试截图（对应第 3、4 章）

| 序号 | 截图内容 | 建议文件名 | 对应章节 |
|---|---|---|---|
| 13 | Swagger 接口总览 `/docs` | 13_接口总览.png | 3.4 |
| 14 | 非法状态流转返回 422 的响应 | 14_非法流转.png | 4.3 |
| 15 | 并发下单只成交一单的日志 | 15_并发下单.png | 4.3 |
| 16 | `EXPLAIN` 索引前后对比 | 16_索引优化.png | 4.4 |

## 三、工程与过程截图（对应第 4、6 章）

| 序号 | 截图内容 | 建议文件名 | 对应章节 |
|---|---|---|---|
| 17 | `git log --graph` 提交历史 | 17_Git历史.png | 4.5 |
| 18 | 四个 feature 分支合并图 | 18_分支图.png | 4.5 |
| 19 | pytest 全部通过的控制台输出 | 19_测试通过.png | 5.2 |
| 20 | MySQL 表结构（Workbench 或 desc） | 20_表结构.png | 3.3 |
"""
    (target / "05_截图素材" / "截图清单.md").write_text(content, encoding="utf-8")


def build(with_zip: bool = False) -> Path:
    """重建交付文件夹；with_zip 为真时额外生成压缩包，返回交付目录路径。"""
    if DELIVER_ROOT.exists() and DELIVER_ROOT.name != DELIVER_NAME:
        raise RuntimeError(f"拒绝清理非交付目录：{DELIVER_ROOT}")
    DELIVER_ROOT.mkdir(parents=True, exist_ok=True)
    _clean(DELIVER_ROOT)

    for child in ("01_源代码", "02_数据库脚本", "03_实验报告", "04_过程材料", "05_截图素材"):
        (DELIVER_ROOT / child).mkdir(parents=True, exist_ok=True)

    shutil.copytree(
        PROJECT_ROOT,
        DELIVER_ROOT / "01_源代码" / "secondhand-market",
        ignore=_ignore,
        dirs_exist_ok=True,
    )

    _copy(PROJECT_ROOT / "sql" / "init.sql", DELIVER_ROOT / "02_数据库脚本" / "init.sql")
    (DELIVER_ROOT / "02_数据库脚本" / "数据库说明.md").write_text(
        "# 数据库说明\n\n"
        "- 数据库：MySQL 8.0，字符集 utf8mb4 / utf8mb4_unicode_ci，存储引擎 InnoDB\n"
        "- 主库 `secondhand_market`，测试库 `secondhand_market_test`（由 pytest 夹具自动建表）\n"
        "- 共 7 张表：users、categories、goods、orders、reviews、favorites、messages\n"
        "- 索引：goods(status, created_at)、goods(category_id)、orders(buyer_id)、\n"
        "  orders(seller_id)、orders(status)、messages(receiver_id, is_read)\n"
        "- 约束：goods 状态与价格 CHECK、reviews 评分 1-5 CHECK、favorites(user_id, goods_id) 唯一\n"
        "- 建库方式：`mysql -u root -p < init.sql`，随后执行 `python scripts/init_db.py --demo` 写入分类\n",
        encoding="utf-8",
    )

    report = PROJECT_ROOT / "docs" / "实验报告.docx"
    if report.exists():
        _copy(report, DELIVER_ROOT / "03_实验报告" / "实验报告.docx")
    (DELIVER_ROOT / "03_实验报告" / "待办.txt").write_text(
        "提交前请确认：\n1. 报告 6 章齐全，封面信息已填写\n"
        "2. 文档中的接口数量、状态转移条数与最终代码一致\n"
        "3. 所有截图来自最终版本\n",
        encoding="utf-8",
    )

    for name in (
        "分工说明.md",
        "Git提交计划.md",
        "Bug追踪.md",
        "接口文档.md",
        "系统设计.md",
        "进度日志.md",
    ):
        source = PROJECT_ROOT / "docs" / name
        if source.exists():
            shutil.copy2(source, DELIVER_ROOT / "04_过程材料" / name)

    # 设计文档引用的四张图随文档一起交付，否则 04_过程材料 里的图片链接会断
    figures = PROJECT_ROOT / "docs" / "figures"
    if figures.is_dir():
        target = DELIVER_ROOT / "04_过程材料" / "figures"
        target.mkdir(parents=True, exist_ok=True)
        for png in sorted(figures.glob("*.png")):
            shutil.copy2(png, target / png.name)

    _run(
        ["git", "log", "--graph", "--pretty=format:%ad | %an | %s", "--date=format:%Y-%m-%d %H:%M"],
        DELIVER_ROOT / "04_过程材料" / "Git提交记录.txt",
        "Git 提交历史（按时间倒序）",
    )
    _run(
        [
            sys.executable, "-m", "pytest", "-q",
            "--tb=short", "-p", "no:cacheprovider",
            "--junit-xml", str(DELIVER_ROOT / "04_过程材料" / "pytest-result.xml"),
        ],
        DELIVER_ROOT / "04_过程材料" / "测试报告.txt",
        "pytest 自动化测试结果",
    )

    _write_readme(DELIVER_ROOT)
    _write_shot_list(DELIVER_ROOT)

    if with_zip:
        archive = PROJECT_ROOT.parent / DELIVER_NAME
        shutil.make_archive(str(archive), "zip", root_dir=PROJECT_ROOT.parent, base_dir=DELIVER_NAME)
    return DELIVER_ROOT


if __name__ == "__main__":
    path = build(with_zip="--zip" in sys.argv)
    files = sum(1 for _ in path.rglob("*") if _.is_file())
    print(f"交付文件夹已生成：{path}")
    print(f"文件总数：{files}")
