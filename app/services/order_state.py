# Author: 郝津德
"""订单唯一状态转移表，供权限校验和前端按钮生成共用。

转移以「当前状态 + 目标状态 + 操作角色」三元组为键。这样同一跳转
（例如 PENDING → CANCELLED）可以区分是卖家拒绝还是买家撤销；
权限校验与按钮渲染都只读这一张表，不会两处各写一遍导致前后端不一致。
"""

from app.core.exceptions import Forbidden, InvalidStateTransition


# 六条合法转移：覆盖卖家确认/拒绝、买家撤销/收货/取消/退款。
TRANSITIONS = {
    ("PENDING", "PAID_PENDING", "seller"): {"label": "确认出售", "style": "primary"},
    ("PENDING", "CANCELLED", "seller"): {"label": "拒绝", "style": "danger"},
    ("PENDING", "CANCELLED", "buyer"): {"label": "撤销订单", "style": "danger"},
    ("PAID_PENDING", "COMPLETED", "buyer"): {"label": "确认收货", "style": "primary"},
    ("PAID_PENDING", "CANCELLED", "buyer"): {"label": "取消订单", "style": "danger"},
    ("COMPLETED", "CANCELLED", "buyer"): {"label": "申请退款", "style": "danger"},
}


# 状态全集，顺序即正常生命周期；与 models/order.py 的 CheckConstraint 保持一致。
# 列表接口用它拒掉拼错的状态值，否则筛错只会得到空列表，最难排查。
ALL_STATUSES = ("PENDING", "PAID_PENDING", "COMPLETED", "CANCELLED")


def available_actions(status: str, role: str) -> list[dict]:
    """接收当前状态和当事人角色，返回该角色此刻可点的按钮字段。"""
    return [{"label": rule["label"], "to_status": target, "style": rule["style"]}
            for (source, target, actor), rule in TRANSITIONS.items()
            if source == status and actor == role]


def validate_transition(current: str, target: str, role: str) -> None:
    """校验状态与角色；合法时返回，越权抛 403，非法流转抛 409。"""
    if (current, target, role) in TRANSITIONS:
        return
    if any((current, target, actor) in TRANSITIONS for actor in ("buyer", "seller")):
        raise Forbidden("该订单操作不属于你的角色")
    raise InvalidStateTransition()
