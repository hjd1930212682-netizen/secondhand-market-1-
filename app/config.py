# Author: 郝津德
"""从项目根目录的 .env 读取数据库、JWT 和上传配置。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """保存应用配置；优先读环境变量，其次读项目根目录的 .env。"""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # 默认值指向本机 MySQL 8.0；没有 MySQL 时可改为 sqlite:///./local_dev.db 快速验证
    database_url: str = (
        "mysql+pymysql://root:root123@127.0.0.1:3306/secondhand_market?charset=utf8mb4"
    )
    test_database_url: str | None = None
    jwt_secret: str = "dev-only-secret-please-change"
    jwt_expire_minutes: int = 1440
    upload_dir: str = "frontend/uploads"

    @property
    def upload_path(self) -> Path:
        """返回上传目录的绝对路径，避免受启动目录影响。"""
        path = Path(self.upload_dir)
        return path if path.is_absolute() else PROJECT_ROOT / path


@lru_cache
def get_settings() -> Settings:
    """返回缓存配置；无参数，返回已校验的 Settings。"""
    return Settings()

