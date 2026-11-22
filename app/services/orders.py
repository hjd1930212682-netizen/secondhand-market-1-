# Author: 郝津德
"""订单创建、防超卖事务、状态流转与订单展示。"""

import secrets
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, Forbidden, NotFound
from app.models import Goods, Order, Review, User
from app.services.order_state import ALL_STATUSES, available_actions, validate_transition
from app.services.presenters import page_result


def order_data(db: Session, order: Order, viewer_id: int) -> dict:
    """组装订单及当前用户可用操作；接收会话、订单和用户 ID。"""
    goods = db.get(Goods, order.goods_id)
    buyer = db.get(User, order.buyer_id)
    seller = db.get(User, order.seller_id)
    reviewed = db.scalar(select(Review.id).where(Review.order_id == order.id)) is not None
    return _order_dict(order, goods, buyer, seller, reviewed, viewer_id)


def _order_dict(order: Order, goods: Goods, buyer: User, seller: User,
                reviewed: bool, viewer_id: int) -> dict:
    """用已取到的关联对象拼订单字段；接收订单、商品、买卖双方与评价标记，返回字典。

    与 order_data 分开是为了让列表页能一次性批量取齐关联对象：逐条调用 order_data
    时每张订单都要额外查商品、买家、卖家、评价，12 条一页就是十几次往返。
    """
    role = "buyer" if viewer_id == order.buyer_id else "seller"
    return {"id": order.id, "order_no": order.order_no, "goods_id": order.goods_id,
            "goods_title": goods.title, "goods_images": goods.images, "buyer_id": order.buyer_id,
            "buyer_name": buyer.nickname, "seller_id": order.seller_id, "seller_name": seller.nickname,
            "price": order.price, "status": order.status, "created_at": order.created_at,
            "finished_at": order.finished_at,
            "available_actions": available_actions(order.status, role),
            "reviewed": reviewed}


def get_order(db: Session, order_id: int, user_id: int, lock: bool = False) -> Order:
    """读取当事人的订单；可选行锁，返回 Order。"""
    stmt = select(Order).where(Order.id == order_id)
    if lock:
        stmt = stmt.with_for_update()
    order = db.scalar(stmt)
    if order is None:
        raise NotFound("订单不存在")
    if user_id not in (order.buyer_id, order.seller_id):
        raise Forbidden()
    return order


def create_order(db: Session, goods_id: int, buyer: User) -> dict:
    """行锁下创建订单并售出商品；接收会话、商品 ID 和买家，返回订单。"""
    try:
        # FOR UPDATE 必须与状态检查、插单和改状态处于同一事务。
        # 第二个买家会等待首单提交，再读取最新的“已售”状态。
        goods = db.scalar(select(Goods).where(Goods.id == goods_id).with_for_update())
        if goods is None:
            raise NotFound("商品不存在")
        if goods.status != "在售":
            raise BusinessError("商品已被抢购", 409)
        if goods.seller_id == buyer.id:
            raise BusinessError("不能购买自己发布的商品")
        order_no = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") + secrets.token_hex(4)
        order = Order(order_no=order_no, goods_id=goods.id, buyer_id=buyer.id,
                      seller_id=goods.seller_id, price=goods.price, status="PENDING")
        db.add(order)
        goods.status = "已售"
        db.commit()
        db.refresh(order)
        return order_data(db, order, buyer.id)
    except (BusinessError, IntegrityError) as exc:
        db.rollback()
        if isinstance(exc, IntegrityError):
            raise BusinessError("下单冲突，请重试", 409) from exc
        raise


def change_order_status(db: Session, order_id: int, user: User, target: str) -> dict:
    """按状态表改变订单并联动商品；返回最新订单。"""
    try:
        order = get_order(db, order_id, user.id, lock=True)
        role = "buyer" if order.buyer_id == user.id else "seller"
        validate_transition(order.status, target, role)
        previous = order.status
        order.status = target
        if target in {"COMPLETED", "CANCELLED"}:
            order.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if target == "CANCELLED" and previous != "COMPLETED":
            goods = db.scalar(select(Goods).where(Goods.id == order.goods_id).with_for_update())
            goods.status = "在售"
        db.commit()
        return order_data(db, order, user.id)
    except BusinessError:
        db.rollback()
        raise


def list_orders(db: Session, user: User, role: str, status: str | None,
                page: int, size: int) -> dict:
    """按买卖角色、状态和页码查询本人订单，返回统一列表。"""
    if role not in {"buyer", "seller"}:
        raise BusinessError("订单角色不合法")
    # 状态写错时直接报错，而不是返回空列表——前端筛错只看到「暂无订单」最难排查。
    if status and status not in ALL_STATUSES:
        raise BusinessError("订单状态不合法")
    condition = getattr(Order, role + "_id") == user.id
    if status:
        condition = condition & (Order.status == status)
    total = db.scalar(select(func.count(Order.id)).where(condition)) or 0
    rows = db.scalars(select(Order).where(condition)
                      .order_by(Order.created_at.desc(), Order.id.desc())
                      .offset((page - 1) * size).limit(size)).all()
    if not rows:
        return page_result([], total, page, size)
    # 批量取关联数据：商品、当事人、是否已评各一条 IN 查询，避免逐行回表。
    goods_ids = {row.goods_id for row in rows}
    user_ids = {row.buyer_id for row in rows} | {row.seller_id for row in rows}
    goods_map = {item.id: item for item in db.scalars(select(Goods).where(Goods.id.in_(goods_ids)))}
    user_map = {item.id: item for item in db.scalars(select(User).where(User.id.in_(user_ids)))}
    reviewed_ids = set(db.scalars(select(Review.order_id).where(
        Review.order_id.in_([row.id for row in rows]))))
    return page_result([_order_dict(row, goods_map[row.goods_id], user_map[row.buyer_id],
                                    user_map[row.seller_id], row.id in reviewed_ids, user.id)
                        for row in rows], total, page, size)

