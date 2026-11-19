# Author: 郝津德
"""用户与商品之间去重的收藏关系。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Favorite(Base):
    """映射 favorites 表；联合唯一约束防止重复收藏。"""

    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "goods_id", name="uq_favorites_user_goods"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", name="fk_favorites_user"), nullable=False)
    goods_id: Mapped[int] = mapped_column(ForeignKey("goods.id", name="fk_favorites_goods"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

