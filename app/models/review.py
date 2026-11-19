# Author: 郝津德
"""一笔订单最多一条评价的数据库模型。"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, SmallInteger, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Review(Base):
    """映射 reviews 表；评分限定在 1 至 5。"""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", name="fk_reviews_order"), unique=True, nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id", name="fk_reviews_reviewer"), nullable=False)
    target_id: Mapped[int] = mapped_column(ForeignKey("users.id", name="fk_reviews_target"), nullable=False)
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

