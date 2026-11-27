# Author: 安远
"""上传接口的异常流用例：鉴权、类型白名单、体积、魔术字节与文件名安全。

此前 `/api/upload` 是全项目唯一零用例覆盖的写接口，而它同时承担三件危险的事：
接收任意客户端文件、决定落盘文件名、把本地路径回给前端。这里逐项钉住。
"""

from pathlib import Path

import pytest

from app.config import PROJECT_ROOT, get_settings

PNG_HEAD = b"\x89PNG\r\n\x1a\n"
JPG_HEAD = b"\xff\xd8\xff\xe0"
WEBP_HEAD = b"RIFF\x00\x00\x00\x00WEBP"
UPLOAD_DIR: Path = (PROJECT_ROOT / get_settings().upload_dir).resolve()


@pytest.fixture
def clean_uploads():
    """记录用例开始前已有的文件，结束后删掉本用例新增的，避免污染仓库。"""
    before = set(UPLOAD_DIR.iterdir()) if UPLOAD_DIR.exists() else set()
    yield
    if not UPLOAD_DIR.exists():
        return
    for path in set(UPLOAD_DIR.iterdir()) - before:
        path.unlink(missing_ok=True)


def test_upload_requires_login(client):
    """未登录上传返回 401，不能匿名往服务器写文件。"""
    response = client.post("/api/upload", files={"file": ("a.png", PNG_HEAD, "image/png")})
    assert response.status_code == 401


@pytest.mark.parametrize("content_type,head,suffix", [
    ("image/png", PNG_HEAD, ".png"),
    ("image/jpeg", JPG_HEAD, ".jpg"),
    ("image/webp", WEBP_HEAD, ".webp"),
])
def test_upload_supported_types(client, make_user, clean_uploads, content_type, head, suffix):
    """三种白名单类型都能上传，返回 /uploads/ 前缀且后缀由服务端决定。"""
    headers, _ = make_user("uploader_ok")
    response = client.post(
        "/api/upload", headers=headers,
        files={"file": ("随意命名.bin", head + b"body-bytes", content_type)},
    )
    assert response.status_code == 201
    url = response.json()["url"]
    assert url.startswith("/uploads/") and url.endswith(suffix)
    name = url.rsplit("/", 1)[-1]
    assert len(name) == 32 + len(suffix)  # uuid4 的 32 位十六进制 + 后缀
    assert (UPLOAD_DIR / name).exists()


@pytest.mark.parametrize("content_type", ["image/gif", "text/plain", "application/pdf", "image/svg+xml"])
def test_upload_rejects_unsupported_type(client, make_user, content_type):
    """白名单之外的类型一律 400；SVG 也拒，因为它能内嵌脚本。"""
    headers, _ = make_user("uploader_type")
    response = client.post(
        "/api/upload", headers=headers,
        files={"file": ("a.gif", b"GIF89a", content_type)},
    )
    assert response.status_code == 400


def test_upload_rejects_empty_file(client, make_user):
    """空文件返回 400，不留下 0 字节垃圾文件。"""
    headers, _ = make_user("uploader_empty")
    response = client.post(
        "/api/upload", headers=headers, files={"file": ("a.png", b"", "image/png")},
    )
    assert response.status_code == 400


def test_upload_rejects_oversize(client, make_user, clean_uploads):
    """超过 5 MB 返回 400，且不得落盘。"""
    headers, _ = make_user("uploader_big")
    oversize = PNG_HEAD + b"\x00" * (5 * 1024 * 1024)
    response = client.post(
        "/api/upload", headers=headers, files={"file": ("big.png", oversize, "image/png")},
    )
    assert response.status_code == 400


@pytest.mark.parametrize("fake", [
    b"<?php system($_GET[0]); ?>",
    b"<svg onload=alert(1)>",
    b"plain text pretending to be png",
])
def test_upload_rejects_spoofed_content(client, make_user, fake):
    """Content-Type 声明 image/png 但内容是文本或脚本，必须被魔术字节校验拦住。

    只信任 Content-Type 就等于把服务器当网盘：攻击者把 webshell 命名成 .png
    即可落盘，再通过静态目录访问执行。
    """
    headers, _ = make_user("uploader_spoof")
    response = client.post(
        "/api/upload", headers=headers, files={"file": ("fake.png", fake, "image/png")},
    )
    assert response.status_code == 400
    assert "格式与文件内容不符" in response.json()["detail"]


def test_upload_ignores_client_filename(client, make_user, clean_uploads):
    """客户端文件名带路径穿越时被丢弃，落盘名与 URL 都不含路径片段。"""
    headers, _ = make_user("uploader_path")
    response = client.post(
        "/api/upload", headers=headers,
        files={"file": ("../../evil.png", PNG_HEAD + b"x", "image/png")},
    )
    assert response.status_code == 201
    name = response.json()["url"].rsplit("/", 1)[-1]
    assert ".." not in name and "/" not in name and "\\" not in name
    assert not (PROJECT_ROOT / "evil.png").exists()
    assert not (PROJECT_ROOT / "frontend" / "evil.png").exists()
