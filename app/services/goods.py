# Author: 杨云凇
"""商品发布、搜索、详情、上下架和软删除。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, Forbidden, NotFound
from app.models import Category, Goods, User
from app.schemas import GoodsIn
from app.services.presenters import category_data, goods_data, page_result


def categories(db: Session) -> dict:
    """查询全部分类；接收会话，返回统一列表结构。"""
    rows = db.scalars(select(Category).order_by(Category.id)).all()
    return page_result([category_data(row) for row in rows], len(rows))


def validate_category(db: Session, category_id: int) -> None:
    """确认分类存在；接收会话及 ID，不返回值。"""
    if db.get(Category, category_id) is None:
        raise BusinessError("分类不存在")


def create_goods(db: Session, user: User, payload: GoodsIn) -> dict:
    """发布商品；接收会话、卖家和表单，返回新商品。"""
    validate_category(db, payload.category_id)
    goods = Goods(seller_id=user.id, **payload.model_dump(), status="在售")
    db.add(goods)
    db.commit()
    db.refresh(goods)
    return goods_data(goods, user, db.get(Category, goods.category_id))


def owned_goods(db: Session, goods_id: int, user_id: int) -> Goods:
    """验证商品所有权；返回商品，缺失或越权时抛异常。"""
    goods = db.get(Goods, goods_id)
    if goods is None:
        raise NotFound("商品不存在")
    if goods.seller_id != user_id:
        raise Forbidden()
    return goods


def update_goods(db: Session, goods_id: int, user: User, payload: GoodsIn) -> dict:
    """编辑本人在售或下架商品；返回更新结果。"""
    goods = owned_goods(db, goods_id, user.id)
    if goods.status == "已售":
        raise BusinessError("已售商品不可编辑", 409)
    validate_category(db, payload.category_id)
    for key, value in payload.model_dump().items():
        setattr(goods, key, value)
    db.commit()
    db.refresh(goods)
    # 发布接口返回的是带 seller_name / category_name 的完整出参，编辑接口原来只返回
    # goods_data(goods)，少了这几个字段：前端编辑完若直接用返回值刷新页面，
    # 卖家名与分类名会变成 undefined。两个接口返回同一形状，前端才能一套代码复用。
    return goods_data(goods, user, db.get(Category, goods.category_id))


def change_status(db: Session, goods_id: int, user: User, status: str) -> dict:
    """切换本人商品在售或下架状态；返回更新结果。"""
    goods = owned_goods(db, goods_id, user.id)
    if goods.status == "已售":
        raise BusinessError("已售商品不可更改状态", 409)
    if status not in {"在售", "已下架"}:
        raise BusinessError("商品状态不合法")
    goods.status = status
    db.commit()
    # 与 update_goods 同理：上下架后前端要就地刷新卡片，不能少卖家与分类字段。
    return goods_data(goods, user, db.get(Category, goods.category_id))


def delete_goods(db: Session, goods_id: int, user: User) -> dict:
    """软删除本人商品；返回下架后的商品。"""
    return change_status(db, goods_id, user, "已下架")


def detail(db: Session, goods_id: int) -> dict:
    """查询详情并增加浏览量；返回商品与卖家信息。"""
    goods = db.get(Goods, goods_id)
    if goods is None or goods.status == "已下架":
        raise NotFound("商品不存在或已下架")
    goods.view_count += 1
    db.commit()
    return goods_data(goods, db.get(User, goods.seller_id), db.get(Category, goods.category_id))


def search(db: Session, keyword: str, category_id: int | None, sort: str,
           page: int, size: int) -> dict:
    """过滤并分页在售商品；接收查询条件，返回统一列表结构。"""
    query = select(Goods, User).join(User, Goods.seller_id == User.id).where(Goods.status == "在售")
    if keyword.strip():
        term = f"%{keyword.strip()}%"
        query = query.where(Goods.title.like(term) | Goods.description.like(term))
    if category_id:
        children = select(Category.id).where(Category.parent_id == category_id)
        query = query.where((Goods.category_id == category_id) | Goods.category_id.in_(children))
    # 同一过滤条件用于计数和分页，避免页码与结果总数不一致。
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    ordering = {"newest": (Goods.created_at.desc(), Goods.id.desc()),
                "price_asc": (Goods.price.asc(), Goods.id.desc()),
                "price_desc": (Goods.price.desc(), Goods.id.desc()),
                "hot": (Goods.view_count.desc(), Goods.id.desc())}
    if sort not in ordering:
        raise BusinessError("排序方式不支持")
    rows = db.execute(query.order_by(*ordering[sort]).offset((page - 1) * size).limit(size)).all()
    return page_result([goods_data(goods, seller) for goods, seller in rows], total, page, size)
