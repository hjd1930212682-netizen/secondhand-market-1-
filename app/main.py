# Author: 郝津德
"""FastAPI 应用入口：路由、统一异常与同源静态页面。"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from app.core.exceptions import BusinessError
from app.core.logger import configure_logging
from app.routers import auth, favorites, goods, messages, orders, reviews, system, upload, users


configure_logging()
app = FastAPI(title="闲置集市 API", version="1.0.0")


@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
    """接收请求和业务异常，返回统一中文 detail。"""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """接收请求字段错误，返回 400 中文提示。"""
    error = exc.errors()[0]
    field = str(error["loc"][-1]) if error.get("loc") else "参数"
    return JSONResponse(status_code=400, content={"detail": f"{field} 参数格式或取值不正确"})


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """接收框架 HTTP 异常，返回统一中文 detail。"""
    message = "接口不存在" if exc.status_code == 404 else str(exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": message})


for router in (auth.router, users.router, goods.router, orders.router, reviews.router,
               favorites.router, messages.router, upload.router, system.router):
    app.include_router(router)

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """根路径直接跳到首页，避免用户访问 / 看到空白。"""
    return RedirectResponse(url="/pages/index.html")


# 前端页面挂根路径：/pages/xxx.html 与 /uploads/xxx.png 都由它服务。
# 必须放在所有 /api 路由之后注册，否则通配挂载会拦截接口请求。
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
