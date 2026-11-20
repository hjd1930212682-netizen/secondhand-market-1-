# Author: 郝津德
"""统一中文业务异常，交由入口处理为 detail 响应。"""


class BusinessError(Exception):
    """携带中文错误消息和 HTTP 状态码的业务异常。"""

    def __init__(self, message: str, status_code: int = 400) -> None:
        """接收消息和状态码，构造异常；无返回值。"""
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class InvalidStateTransition(BusinessError):
    """订单状态不允许变更时的异常。"""

    def __init__(self) -> None:
        """创建非法流转异常；无参数和返回值。"""
        super().__init__("订单当前状态不可执行该操作", 409)


class NotFound(BusinessError):
    """请求对象不存在。"""

    def __init__(self, message: str = "记录不存在") -> None:
        """接收提示并创建 404 异常；无返回值。"""
        super().__init__(message, 404)


class Forbidden(BusinessError):
    """用户无权执行操作。"""

    def __init__(self, message: str = "无权执行此操作") -> None:
        """接收提示并创建 403 异常；无返回值。"""
        super().__init__(message, 403)

