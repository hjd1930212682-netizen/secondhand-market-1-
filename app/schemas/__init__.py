# Author: 郝津德
"""所有请求模型；校验输入边界，业务规则由服务层判断。"""

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


def strip_text(value: str | None) -> str | None:
    """去掉首尾空白后再交给长度校验；接收任意文本，返回清理结果。

    字段上的 min_length / max_length 默认校验的是「原字符串」，
    所以昵称传 "   " 能过 min_length=1，标题贴进来带两个空格就会超长被拒。
    统一在 before 阶段先 strip，长度约束才对用户看到的文本生效。
    """
    return value.strip() if isinstance(value, str) else value


class RegisterIn(BaseModel):
    """注册所需账号、密码与昵称。"""

    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=6, max_length=72)
    nickname: str = Field(min_length=1, max_length=80)

    @field_validator("nickname", mode="before")
    @classmethod
    def nickname_strip(cls, value: str) -> str:
        """先清理昵称首尾空格，纯空格会因此落到空串被 min_length 拦下。"""
        return strip_text(value)


class LoginIn(BaseModel):
    """登录凭据。"""

    username: str
    password: str


class ProfileIn(BaseModel):
    """可修改的个人资料。"""

    nickname: str = Field(min_length=1, max_length=80)
    phone: str | None = Field(default=None, max_length=30)
    avatar: str | None = Field(default=None, max_length=255)

    @field_validator("nickname", mode="before")
    @classmethod
    def nickname_strip(cls, value: str) -> str:
        """与注册同一口径：改资料也不允许把昵称改成一片空白。"""
        return strip_text(value)

    @field_validator("phone", mode="before")
    @classmethod
    def phone_strip(cls, value: str | None) -> str | None:
        """去掉手机号两端空格，避免「 138…」存进去后前端 tel: 链接失效。"""
        return strip_text(value)


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

    @field_validator("title", mode="before")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        """接收标题，先去首尾空白再校验；纯空白会变成空串被 min_length 拦下。"""
        return strip_text(value)


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
