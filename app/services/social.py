# Author: 郝津德
"""评价、收藏和站内消息业务。"""

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, Forbidden, NotFound
from app.models import Favorite, Goods, Message, Order, Review, User
from app.schemas import MessageIn, ReviewIn
from app.services.orders import get_order
from app.services.presenters import goods_data, message_data, page_result, review_data


def create_review(db: Session, order_id: int, user: User, rating: ReviewIn) -> dict:
    """已完成订单由买家提交一次评价；返回评价数据。"""
    order = get_order(db, order_id, user.id)
    if order.buyer_id != user.id:
        raise Forbidden("只有买家可以评价")
    if order.status != "COMPLETED":
        raise BusinessError("交易完成后才能评价")
    if db.scalar(select(Review.id).where(Review.order_id == order_id)):
        raise BusinessError("该订单已评价", 409)
    review = Review(order_id=order_id, reviewer_id=user.id, target_id=order.seller_id,
                    rating=rating.rating, content=rating.content.strip())
    db.add(review)
    try:
        db.commit()
    except IntegrityError as exc:
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


def add_favorite(db: Session, user: User, goods_id: int) -> dict:
    """收藏在售商品；重复收藏返回 409。"""
    goods = db.get(Goods, goods_id)
    if goods is None or goods.status != "在售":
        raise NotFound("商品不存在")
    if db.scalar(select(Favorite.id).where(Favorite.user_id == user.id, Favorite.goods_id == goods_id)):
        raise BusinessError("已收藏该商品", 409)
    favorite = Favorite(user_id=user.id, goods_id=goods_id)
    db.add(favorite)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise BusinessError("已收藏该商品", 409) from exc
    db.refresh(favorite)
    return {"id": favorite.id, "goods_id": goods_id}


def remove_favorite(db: Session, user: User, goods_id: int) -> dict:
    """删除本人收藏；返回成功提示。"""
    favorite = db.scalar(select(Favorite).where(Favorite.user_id == user.id, Favorite.goods_id == goods_id))
    if favorite is None:
        raise NotFound("收藏不存在")
    db.delete(favorite)
    db.commit()
    return {"message": "已取消收藏"}


def list_favorites(db: Session, user: User, page: int, size: int) -> dict:
    """分页读取本人收藏及商品；返回统一列表。"""
    stmt = select(Favorite, Goods).join(Goods, Favorite.goods_id == Goods.id).where(Favorite.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(stmt.order_by(Favorite.created_at.desc()).offset((page - 1) * size).limit(size)).all()
    return page_result([{"id": favorite.id, "goods": goods_data(goods)} for favorite, goods in rows], total, page, size)


def send_message(db: Session, user: User, payload: MessageIn) -> dict:
    """发送消息；接收会话、发件人和消息字段，返回新消息。"""
    if db.get(User, payload.receiver_id) is None:
        raise NotFound("收件人不存在")
    if payload.receiver_id == user.id:
        raise BusinessError("不能给自己发送消息")
    if payload.goods_id and db.get(Goods, payload.goods_id) is None:
        raise NotFound("商品不存在")
    if not payload.content.strip():
        raise BusinessError("消息内容不能为空")
    message = Message(sender_id=user.id, receiver_id=payload.receiver_id,
                      goods_id=payload.goods_id, content=payload.content.strip())
    db.add(message)
    db.commit()
    db.refresh(message)
    return message_data(message)


def list_messages(db: Session, user: User, peer_id: int | None, page: int, size: int) -> dict:
    """读取本人会话或全部消息；返回统一分页列表。"""
    condition = or_(Message.sender_id == user.id, Message.receiver_id == user.id)
    if peer_id:
        condition = or_(and_(Message.sender_id == user.id, Message.receiver_id == peer_id),
                        and_(Message.sender_id == peer_id, Message.receiver_id == user.id))
    stmt = select(Message).where(condition)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Message.created_at.desc(), Message.id.desc())
                      .offset((page - 1) * size).limit(size)).all()
    return page_result([message_data(row) for row in rows], total, page, size)


def mark_read(db: Session, user: User, peer_id: int) -> dict:
    """把指定发件人给本人的消息标为已读；返回修改条数。"""
    result = db.execute(update(Message).where(Message.sender_id == peer_id,
                                              Message.receiver_id == user.id,
                                              Message.is_read.is_(False)).values(is_read=True))
    db.commit()
    return {"updated": result.rowcount}


def unread_count(db: Session, user: User) -> dict:
    """统计本人未读消息；返回 count 字段。"""
    count = db.scalar(select(func.count()).select_from(Message).where(
        Message.receiver_id == user.id, Message.is_read.is_(False))) or 0
    return {"count": count}
