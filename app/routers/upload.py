# Author: 杨云凇
"""登录用户图片上传接口。"""

from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile

from app.config import PROJECT_ROOT, get_settings
from app.core.deps import current_user
from app.core.exceptions import BusinessError
from app.models import User


router = APIRouter(prefix="/api", tags=["上传"])
MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


@router.post("/upload", status_code=201)
async def upload(file: Annotated[UploadFile, File()],
                 user: Annotated[User, Depends(current_user)]) -> dict:
    """接收图片和已登录用户，保存受限类型文件并返回相对 URL。"""
    if file.content_type not in IMAGE_TYPES:
        raise BusinessError("仅支持 JPG、PNG、WebP 图片")
    data = await file.read(MAX_IMAGE_BYTES + 1)
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise BusinessError("图片不能为空且不能超过 5 MB")
    signatures = {"image/jpeg": data.startswith(b"\xff\xd8\xff"),
                  "image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
                  "image/webp": data.startswith(b"RIFF") and data[8:12] == b"WEBP"}
    if not signatures[file.content_type]:
        raise BusinessError("图片格式与文件内容不符")
    directory = (PROJECT_ROOT / get_settings().upload_dir).resolve()
    frontend = (PROJECT_ROOT / "frontend").resolve()
    if not directory.is_relative_to(frontend):
        raise BusinessError("上传目录配置无效")
    directory.mkdir(parents=True, exist_ok=True)
    filename = uuid4().hex + IMAGE_TYPES[file.content_type]
    (directory / filename).write_bytes(data)
    return {"url": "/uploads/" + filename}

