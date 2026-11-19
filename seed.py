# Author: 郝津德
"""为已初始化的 MySQL 数据库幂等写入分类和可选演示商品。"""

import logging
import os
from decimal import Decimal

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session_factory
from app.models import Category, Goods, User


LOGGER = logging.getLogger(__name__)
CATEGORIES = ("数码电子", "书籍资料", "生活用品", "运动户外", "服饰配件", "其他")
PASSWORD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed_categories(db: Session) -> list[Category]:
    """补齐一级分类；db 为数据库会话，返回分类对象列表。"""
    existing = {row.name: row for row in db.scalars(select(Category).where(Category.parent_id.is_(None)))}
    for name in CATEGORIES:
        if name not in existing:
            row = Category(name=name)
            db.add(row)
            existing[name] = row
    db.flush()
    return [existing[name] for name in CATEGORIES]


def seed_demo(db: Session, categories: list[Category], password: str) -> None:
    """可选写入两个演示用户和商品；参数为会话、分类及演示密码，无返回值。"""
    users = {}
    for username, nickname in (("demo_seller", "校园卖家"), ("demo_buyer", "校园买家")):
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            user = User(username=username, nickname=nickname, password_hash=PASSWORD_CONTEXT.hash(password))
            db.add(user)
            db.flush()
        users[username] = user
    if db.scalar(select(Goods.id).where(Goods.seller_id == users["demo_seller"].id)) is None:
        db.add_all([
            Goods(seller_id=users["demo_seller"].id, category_id=categories[0].id,
                  title="九成新机械键盘", description="校内自提，功能正常。", price=Decimal("129.00"), images="", status="在售"),
            Goods(seller_id=users["demo_seller"].id, category_id=categories[1].id,
                  title="操作系统教材", description="书页完整，适合课程复习。", price=Decimal("25.00"), images="", status="在售"),
        ])


def main() -> None:
    """在单个事务中执行种子写入；无参数和返回值。"""
    password = os.getenv("SEED_DEMO_PASSWORD", "")
    with get_session_factory().begin() as db:
        categories = seed_categories(db)
        if password:
            seed_demo(db, categories, password)
    LOGGER.info("种子数据已就绪；演示账号%s创建", "已" if password else "未")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()

