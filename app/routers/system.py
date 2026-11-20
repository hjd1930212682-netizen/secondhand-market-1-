# Author: 郝津德
"""系统级接口：健康检查。

单独成模块而不是写在 main.py 里，原因有两点：
1. 入口文件只负责装配，业务与检查逻辑各自归位，职责更清晰；
2. 部署时 /api/health 常被探针调用，独立文件便于单独调整。
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database import get_engine


router = APIRouter(prefix="/api", tags=["系统"])


@router.get("/health")
def health() -> JSONResponse:
    """检查服务与数据库连通性；数据库不可用时返回 503 与排查提示。"""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return JSONResponse({"status": "ok", "database": "connected"})
    except Exception as exc:  # noqa: BLE001 - 任何连接异常都要转成可读提示
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "database": "unreachable",
                "detail": "数据库连接失败，请检查 .env 的 DATABASE_URL 与 MySQL 是否已启动",
                "error": str(exc),
            },
        )
