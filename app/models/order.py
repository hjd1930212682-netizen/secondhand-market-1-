# Author: 郝津德
"""交易订单及状态机持久化模型。"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Order(Base):
    """映射 orders 表；状态合法流转由服务层控制。"""

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'PAID_PENDING', 'COMPLETED', 'CANCELLED')", name="ck_orders_status"),
        Index("idx_orders_buyer", "buyer_id"),
        Index("idx_orders_seller", "seller_id"),
        Index("idx_orders_status", "status"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    goods_id: Mapped[int] = mapped_column(ForeignKey("goods.id", name="fk_orders_goods"), nullable=False)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id", name="fk_orders_buyer"), nullable=False)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id", name="fk_orders_seller"), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'PENDING'"))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

