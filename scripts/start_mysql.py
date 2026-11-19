# Author: 郝津德
"""确保本机 MySQL 8.0 已启动，供每日开发任务与本地调试使用。

用法：
    python scripts/start_mysql.py

行为：
1. 检测 127.0.0.1:3306 是否可连接；已就绪直接返回 0。
2. 未就绪则用 my.ini 以独立进程启动 mysqld，轮询等待端口可用（最长 40 秒）。
3. 启动失败时打印排查提示并返回 1，调用方可据此决定是否回退。

路径可用环境变量覆盖：MYSQLD_PATH、MYSQL_MY_INI。
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_MYSQLD = r"C:\Users\13230\mysql8\mysql-8.0.46-winx64\bin\mysqld.exe"
DEFAULT_MY_INI = r"C:\Users\13230\mysql8\my.ini"
HOST = "127.0.0.1"
PORT = 3306


def is_ready(timeout: float = 1.5) -> bool:
    """尝试建立 TCP 连接判断端口是否可用。"""
    try:
        with socket.create_connection((HOST, PORT), timeout=timeout):
            return True
    except OSError:
        return False


def start(mysqld: Path, my_ini: Path) -> None:
    """以独立进程启动 mysqld，标准输出丢弃，避免阻塞调用方。"""
    flags = 0
    if os.name == "nt":
        # 新进程组 + 脱离会话，父进程退出后数据库继续运行
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    subprocess.Popen(
        [str(mysqld), f"--defaults-file={my_ini}", "--console"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=flags,
        close_fds=True,
    )


def main() -> int:
    """检测并按需启动，返回进程退出码。"""
    if is_ready():
        print(f"MySQL 已在 {HOST}:{PORT} 运行")
        return 0

    mysqld = Path(os.getenv("MYSQLD_PATH", DEFAULT_MYSQLD))
    my_ini = Path(os.getenv("MYSQL_MY_INI", DEFAULT_MY_INI))
    if not mysqld.exists():
        print(f"找不到 mysqld：{mysqld}")
        print("请用环境变量 MYSQLD_PATH 指定可执行文件路径")
        return 1
    if not my_ini.exists():
        print(f"找不到配置文件：{my_ini}")
        print("请用环境变量 MYSQL_MY_INI 指定 my.ini 路径")
        return 1

    print(f"正在启动 MySQL：{mysqld}")
    start(mysqld, my_ini)

    for second in range(1, 41):
        if is_ready():
            print(f"MySQL 启动成功，耗时 {second} 秒")
            return 0
        time.sleep(1)

    print("MySQL 40 秒内未就绪，请检查：")
    print("  1. 端口 3306 是否被其他实例占用")
    print(f"  2. 数据目录与 {my_ini.name} 中的 datadir 是否一致")
    print("  3. 手动执行 mysqld --console 查看报错输出")
    return 1


if __name__ == "__main__":
    sys.exit(main())
