# Author: 郝津德
"""统计产品代码的物理行数，按「谁主责哪个文件」汇总，供报告的贡献度表使用。

口径（与报告 6.3 节一致）：
- 只统计产品代码：app/、frontend/、tests/、sql/ 与 seed.py；
- 行数取 `wc -l` 的物理行数，含注释与空行（这是「写了多少」而不是「编译后多少」）；
- 文档、图、脚本不计入产品代码，`scripts/` 的交付脚本单独汇总。
- `frontend/js/pages.js` 是四人共用文件（每人往里加自己页面的逻辑），
  整体归前端负责人，但在输出里单列一行，避免把共用文件算成某个人的独有产出。

用法：python scripts/count_lines.py
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 文件名 -> 主责人。按表 1-1 的模块归属，不按文件头的 # Author 行
# （文件头记的是最初创建者，多人迭代后与主责人已经不一致）。
OWNERS = {
    "郝津德": [
        "app/config.py", "app/database.py", "app/main.py", "seed.py", "sql/init.sql",
        "app/core/security.py", "app/core/deps.py", "app/core/exceptions.py", "app/core/logger.py",
        "app/models/__init__.py",
        "app/schemas/__init__.py",
        "app/routers/system.py", "app/routers/orders.py", "app/routers/upload.py",
        "app/routers/messages.py", "app/routers/favorites.py",
        "app/services/orders.py", "app/services/order_state.py",
        "app/services/social.py", "app/services/presenters.py",
    ],
    "王昱皓": [
        "frontend/css/style.css", "frontend/js/api.js", "frontend/js/common.js",
        "frontend/pages/index.html", "frontend/pages/login.html",
        "frontend/pages/register.html", "frontend/pages/profile.html",
        "frontend/pages/404.html",
        "app/routers/auth.py", "app/routers/users.py", "app/services/users.py",
    ],
    "杨云凇": [
        "frontend/pages/publish.html", "frontend/pages/goods-list.html",
        "frontend/pages/goods-detail.html", "frontend/pages/my-goods.html",
        "app/routers/goods.py", "app/services/goods.py",
    ],
    "安远": [
        "frontend/pages/review.html",
        "app/routers/reviews.py", "app/services/reviews.py",
        "tests/conftest.py", "tests/test_auth.py", "tests/test_goods.py",
        "tests/test_orders.py", "tests/test_flow.py", "tests/test_api.py",
        "tests/test_upload.py", "tests/test_mysql_concurrency.py",
    ],
}

SHARED = ["frontend/js/pages.js"]


def lines(rel: str) -> int:
    """物理行数；文件不存在时返回 0，避免清单漏项时整体报错。"""
    path = ROOT / rel
    if not path.exists():
        return 0
    with path.open("rb") as fh:
        return sum(1 for _ in fh)


def main() -> int:
    print(f"{'姓名':<8}{'产品代码':>8}{'文件数':>8}")
    total = 0
    for who, files in OWNERS.items():
        n = sum(lines(f) for f in files)
        total += n
        print(f"{who:<8}{n:>8}{len(files):>8}")
    for f in SHARED:
        n = lines(f)
        total += n
        print(f"{'共用':<8}{n:>8}{1:>8}  {f}")

    scripts = sorted((ROOT / "scripts").glob("*.py"))
    extra = sum(lines(str(p.relative_to(ROOT))) for p in scripts if p.name != "count_lines.py")
    print(f"\n产品代码合计 {total} 行（含共用 {sum(lines(f) for f in SHARED)} 行）")
    print(f"scripts/ 交付脚本 {extra} 行（绘图、报告生成、打包、建库，不计入产品代码）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
