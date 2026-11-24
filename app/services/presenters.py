# Author: 郝津德
"""把 ORM 对象转换为稳定的公开接口字段。"""

from app.models import Category, Goods, Message, Review, User


def page_result(items: list, total: int, page: int = 1, size: int | None = None) -> dict:
    """接收列表和分页数字，返回统一列表结构。"""
    return {"items": items, "total": total, "page": page, "size": size or max(total, 1)}


def user_data(user: User, public: bool = False) -> dict:
    """接收用户对象和公开标记，返回不含密码的个人资料。"""
    data = {"id": user.id, "username": user.username, "nickname": user.nickname,
            "avatar": user.avatar, "credit_score": user.credit_score, "created_at": user.created_at}
    if not public:
        data["phone"] = user.phone
    return data


def category_data(category: Category) -> dict:
    """接收分类对象，返回分类编号、名称和父编号。"""
    return {"id": category.id, "name": category.name, "parent_id": category.parent_id}


def goods_data(goods: Goods, seller: User | None = None, category: Category | None = None) -> dict:
    """接收商品及可选关联对象，返回商品展示字段。"""
    data = {"id": goods.id, "seller_id": goods.seller_id, "category_id": goods.category_id,
            "title": goods.title, "description": goods.description, "price": goods.price,
            "images": goods.images, "status": goods.status, "view_count": goods.view_count,
            "created_at": goods.created_at}
    if seller:
        data.update(seller_name=seller.nickname, seller_avatar=seller.avatar, seller_credit=seller.credit_score)
    if category:
        data["category_name"] = category.name
    return data


def review_data(review: Review, reviewer: User | None = None) -> dict:
    """接收评价及作者，返回评价展示字段。"""
    return {"id": review.id, "order_id": review.order_id, "reviewer_id": review.reviewer_id,
            "reviewer_name": reviewer.nickname if reviewer else None, "target_id": review.target_id,
            "rating": review.rating, "content": review.content, "created_at": review.created_at}


def message_data(message: Message) -> dict:
    """接收消息对象，返回会话展示字段。"""
    return {"id": message.id, "sender_id": message.sender_id, "receiver_id": message.receiver_id,
            "goods_id": message.goods_id, "content": message.content, "is_read": message.is_read,
            "created_at": message.created_at}

