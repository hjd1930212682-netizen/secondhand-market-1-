# Author: 安远
"""交易评价业务：提交评价、按商品读评价、卖家评分统计。

评价原本和消息、收藏一起挤在 services/social.py 里，三段互不相干的逻辑共用一个
文件头（# Author: 郝津德），评价这块的改动只能跟着别人的提交走。D7 联调修评价
漏洞时按模块拆出来，评价三段逻辑归评价负责人维护，social.py 只留消息与收藏。
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, Forbidden, NotFound
from app.models import Goods, Order, Review, User
from app.schemas import ReviewIn
from app.services.orders import get_order
from app.services.presenters import page_result, review_data


def create_review(db: Session, order_id: int, user: User, rating: ReviewIn) -> dict:
    """已完成订单由买家提交一次评价；返回评价数据。"""
    order = get_order(db, order_id, user.id)
    if order.buyer_id != user.id:
        raise Forbidden("只有买家可以评价")
    if order.status != "COMPLETED":
        raise BusinessError("交易完成后才能评价")
    if db.scalar(select(Review.id).where(Review.order_id == order_id)):
        raise BusinessError("该订单已评价", 409)
    # 请求模型只要求 content 长度 ≥ 1，纯空格能过校验；strip 之后是空串，
    # 会存进一条「看不见的评价」，商品详情页上就是一片空白加几颗星。
    # 消息接口早有同样的判断，评价这里是对齐，不是新增规则。
    content = rating.content.strip()
    if not content:
        raise BusinessError("评价内容不能为空")
    review = Review(order_id=order_id, reviewer_id=user.id, target_id=order.seller_id,
                    rating=rating.rating, content=content)
    db.add(review)
    try:
        db.commit()
    except IntegrityError as exc:
        # order_id 上有唯一索引，并发双击提交时靠它兜底，避免两行评价。
        db.rollback()
        raise BusinessError("该订单已评价", 409) from exc
    db.refresh(review)
    return review_data(review, user)


def goods_reviews(db: Session, goods_id: int, page: int, size: int) -> dict:
    """按商品分页读取评价；返回统一列表结构。"""
    if db.get(Goods, goods_id) is None:
        raise NotFound("商品不存在")
    stmt = select(Review, User).join(Order, Review.order_id == Order.id).join(
        User, Review.reviewer_id == User.id).where(Order.goods_id == goods_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(stmt.order_by(Review.created_at.desc()).offset((page - 1) * size).limit(size)).all()
    return page_result([review_data(review, reviewer) for review, reviewer in rows], total, page, size)


def user_rating(db: Session, user_id: int) -> dict:
    """计算用户平均评分和评价数；返回统计对象。"""
    if db.get(User, user_id) is None:
        raise NotFound("用户不存在")
    average, count = db.execute(select(func.avg(Review.rating), func.count(Review.id))
                                .where(Review.target_id == user_id)).one()
    return {"user_id": user_id, "average": round(float(average or 0), 1), "count": count}
