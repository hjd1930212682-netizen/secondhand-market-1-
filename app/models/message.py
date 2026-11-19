# Author: 郝津德
"""站内消息与未读计数索引的数据模型。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Message(Base):
    """映射 messages 表；支持按接收人快速统计未读消息。"""

    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_messages_receiver", "receiver_id", "is_read"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", name="fk_messages_sender"), nullable=False)
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id", name="fk_messages_receiver"), nullable=False)
    goods_id: Mapped[int | None] = mapped_column(ForeignKey("goods.id", name="fk_messages_goods"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
