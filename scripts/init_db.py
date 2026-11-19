# Author: 郝津德
"""一键初始化数据库：建表 + 写入分类与演示数据。

用法：
    python scripts/init_db.py            # 建表并写分类
    python scripts/init_db.py --demo     # 额外写两个演示账号和商品

脚本对已存在的表使用 CREATE TABLE IF NOT EXISTS 语义，重复执行安全。
连接串来自 .env 的 DATABASE_URL，MySQL 与 SQLite 均可运行。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings  # noqa: E402
from app.database import Base, build_engine, get_session_factory  # noqa: E402
from app.models import Category  # noqa: E402,F401  导入即注册全部七张表

LOGGER = logging.getLogger("init_db")
CATEGORIES = ("数码电子", "书籍资料", "生活用品", "运动户外", "服饰配件", "其他")
DEMO_PASSWORD = "pass1234"


def create_tables(url: str) -> None:
    """按 ORM 元数据建表；url 为数据库连接串，无返回值。"""
    engine = build_engine(url)
    Base.metadata.create_all(bind=engine)
    LOGGER.info("建表完成：%s", engine.url.render_as_string(hide_password=True))


def seed_categories() -> None:
    """补齐六个一级分类，重复执行不会产生重复行。"""
    from sqlalchemy import select

    with get_session_factory().begin() as db:
        existing = {
            row.name
            for row in db.scalars(select(Category).where(Category.parent_id.is_(None)))
        }
        for name in CATEGORIES:
            if name not in existing:
                db.add(Category(name=name))
        LOGGER.info("分类就绪，共 %d 个", len(existing | set(CATEGORIES)))


def seed_demo() -> None:
    """写入两个演示账号与两件在售商品，供前端联调使用。"""
    import os

    from passlib.context import CryptContext
    from sqlalchemy import select

    from app.models import Goods, User

    context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    with get_session_factory().begin() as db:
        users: dict[str, User] = {}
        for username, nickname in (("demo_seller", "校园卖家"), ("demo_buyer", "校园买家")):
            user = db.scalar(select(User).where(User.username == username))
            if user is None:
                user = User(
                    username=username,
                    nickname=nickname,
                    password_hash=context.hash(DEMO_PASSWORD),
                )
                db.add(user)
                db.flush()
            users[username] = user

        category = db.scalar(select(Category).where(Category.name == "数码电子"))
        if category is None:
            category = db.scalar(select(Category))
        already = db.scalar(select(Goods.id).where(Goods.seller_id == users["demo_seller"].id))
        if already is None and category is not None:
            db.add_all([
                Goods(
                    seller_id=users["demo_seller"].id,
                    category_id=category.id,
                    title="九成新机械键盘",
                    description="校内自提，功能正常，键帽无打油。",
                    price="129.00",
                    images="",
                    status="在售",
                ),
                Goods(
                    seller_id=users["demo_seller"].id,
                    category_id=category.id,
                    title="操作系统教材",
                    description="书页完整，适合课程复习。",
                    price="25.00",
                    images="",
                    status="在售",
                ),
            ])
        LOGGER.info("演示数据就绪，账号 demo_seller / demo_buyer 密码 %s", DEMO_PASSWORD)


def main() -> None:
    """读取配置并串起建表与种子写入。"""
    settings = get_settings()
    create_tables(settings.database_url)
    seed_categories()
    if "--demo" in sys.argv:
        seed_demo()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
