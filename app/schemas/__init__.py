# Author: 郝津德
"""所有请求模型；校验输入边界，业务规则由服务层判断。"""

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class RegisterIn(BaseModel):
    """注册所需账号、密码与昵称。"""

    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=6, max_length=72)
    nickname: str = Field(min_length=1, max_length=80)


class LoginIn(BaseModel):
    """登录凭据。"""

    username: str
    password: str


class ProfileIn(BaseModel):
    """可修改的个人资料。"""

    nickname: str = Field(min_length=1, max_length=80)
    phone: str | None = Field(default=None, max_length=30)
    avatar: str | None = Field(default=None, max_length=255)


class PasswordIn(BaseModel):
    """旧密码与新密码。"""

    old_password: str
    new_password: str = Field(min_length=6, max_length=72)


class GoodsIn(BaseModel):
    """商品发布与编辑字段。"""

    category_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=10000)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    images: str = Field(default="", max_length=5000)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        """接收标题，拒绝纯空白并返回清理后的标题。"""
        if not value.strip():
            raise ValueError("商品标题不能为空")
        return value.strip()


class GoodsStatusIn(BaseModel):
    """商品上下架状态。"""

    status: str


class OrderIn(BaseModel):
    """下单目标商品。"""

    goods_id: int = Field(gt=0)


class OrderStatusIn(BaseModel):
    """订单目标状态。"""

    to_status: str


class ReviewIn(BaseModel):
    """星级与评价文字。"""

    rating: int = Field(ge=1, le=5)
    content: str = Field(min_length=1, max_length=2000)


class FavoriteIn(BaseModel):
    """收藏目标商品。"""

    goods_id: int = Field(gt=0)


class MessageIn(BaseModel):
    """消息接收人、关联商品与内容。"""

    receiver_id: int = Field(gt=0)
    goods_id: int | None = Field(default=None, gt=0)
    content: str = Field(min_length=1, max_length=2000)


class ReadMessagesIn(BaseModel):
    """标记某位联系人的消息为已读。"""

    peer_id: int = Field(gt=0)
