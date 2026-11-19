# Author: 郝津德
"""商品与搜索、状态所需索引的数据模型。"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Goods(Base):
    """映射 goods 表；删除由服务层改为下架。"""

    __tablename__ = "goods"
    __table_args__ = (
        CheckConstraint("status IN ('在售', '已售', '已下架')", name="ck_goods_status"),
        CheckConstraint("price > 0", name="ck_goods_price"),
        Index("idx_goods_status_created", "status", "created_at"),
        Index("idx_goods_category", "category_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id", name="fk_goods_seller"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", name="fk_goods_category"), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    images: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default=text("'在售'"))
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

