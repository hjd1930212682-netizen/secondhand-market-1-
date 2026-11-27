# 闲置集市

《操作系统与工具链》课程项目：校内二手交易平台。后端使用 Python 3.10+、FastAPI、SQLAlchemy 2.0、MySQL 8.0 和 PyMySQL；前端为纯 HTML、CSS、原生 JavaScript 与 Bootstrap 5 CDN，无前端构建步骤。

## 启动

1. 安装 MySQL 8.0，执行 `sql/init.sql`。例如在项目目录运行 `mysql -u root -p < sql/init.sql`。脚本创建 `secondhand_market` 和 `secondhand_market_test` 两个库，并在主库创建七张表。
2. 复制 `.env.example` 为 `.env`，填写 MySQL 用户、密码和长度足够的随机 `JWT_SECRET`。`.env` 已被 Git 忽略。
3. 创建虚拟环境，执行 `pip install -r requirements.txt`，然后运行 `python scripts/init_db.py --demo` 建表并写入六个分类与两个演示账号（脚本幂等，重复执行不会产生重复数据）。
4. 执行 `uvicorn app.main:app --reload`，打开 `http://127.0.0.1:8000/pages/index.html`；接口文档位于 `http://127.0.0.1:8000/docs`。

Windows PowerShell 示例：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# 编辑 .env 后再继续
python scripts/init_db.py --demo
uvicorn app.main:app --reload
```

### 启动 MySQL（绿色版 zip 解压的情况）

若 MySQL 不是用安装包注册为 Windows 服务，每次开机需要先启动它。`scripts/` 下提供两个双击脚本：

- `start-mysql.bat`：临时启动，开发期间保持弹出的窗口不关闭即可
- `install-mysql-service.bat`：右键「以管理员身份运行」，注册为开机自启服务（只需一次）
- `start_mysql.py`：命令行方式，检测端口并在未启动时自动拉起（供自动化任务调用）

手动前台启动的命令：

```powershell
C:\Users\13230\mysql8\mysql-8.0.46-winx64\bin\mysqld.exe --defaults-file=C:\Users\13230\mysql8\my.ini --console
```

注册为开机自启（管理员 PowerShell，只需一次）：

```powershell
sc.exe create MySQL80 binPath= "C:\Users\13230\mysql8\mysql-8.0.46-winx64\bin\mysqld.exe --defaults-file=C:\Users\13230\mysql8\my.ini" start= auto
sc.exe start MySQL80
```

日志中看到 `ready for connections` 即启动完成，可用 `mysql -u root -e "SELECT VERSION();"` 验证。

如果要创建两名演示用户和两件商品，可在执行 `python seed.py` 前临时设置环境变量 `SEED_DEMO_PASSWORD`。账号为 `demo_seller` 与 `demo_buyer`，密码为该变量的值。种子脚本重复运行不会重复插入已有分类或演示商品。

## 测试

`pytest -q` 运行 TestClient 接口测试，本机在 MySQL 8.0.46 上 **96 项全部通过、0 跳过**。用例按模块分五批：认证与用户 27 项、商品与分类 32 项（D8 入库），订单与状态机 20 项、全链路与接口清单 16 项（D9 入库），MySQL 并发 1 项。边界与异常用例占多数：空白输入、长度上下界、价格为 0/负数/超位、页码与 `size` 越界、重复提交、越权与非法状态流转。`tests/test_mysql_concurrency.py` 需要可连接的 `TEST_DATABASE_URL`（库名必须为 `secondhand_market_test`），会清空并重建测试库七张表，再以五个并发请求验证同一商品只能被一人下单。实际结果：**1 单成功，4 单返回 409「商品已被抢购」**。

## 接口与鉴权

- 共 24 条 `/api` 路径、30 个接口，按模块分 6 组，逐条参数与错误码见 `docs/接口文档.md`；服务启动后 `/docs` 可交互调试。
- 受保护接口统一带 `Authorization: Bearer <token>`；令牌由 `POST /api/auth/login` 下发，`app/core/deps.py` 解析后注入当前用户。
- 错误统一返回 `{"detail": "中文提示"}`：400 参数非法、401 未登录或令牌过期、403 越权、404 不存在、409 冲突。
- 前端所有请求经 `frontend/js/api.js`，401 自动跳登录页，不散落在各页面。

## 目录与规则

- `app/models/`：七张表；`app/services/`：业务规则；`app/routers/`：HTTP 参数和服务调用；`app/core/`：鉴权、异常和日志。
- `frontend/pages/`：规格列出的 14 个页面；`frontend/js/api.js` 负责所有请求，`pages.js` 负责页面交互。
- `sql/init.sql`：MySQL 8.0 建库和建表；`seed.py`：种子分类与可选演示账号。
- `docs/`：接口文档、四张设计图（`docs/figures/`）、测试记录和报告草稿。设计图由 `python scripts/make_figures.py` 生成，改代码后重跑即可同步。

订单状态以 `app/services/order_state.py` 的转移表为唯一来源。所有前端订单按钮由接口的 `available_actions` 字段生成。商品删除是状态改为“已下架”，历史订单仍可引用商品。

## 注意

商品交易仅记录订单状态；平台没有真实支付接口。下单并发正确性依赖 MySQL InnoDB 的 `SELECT ... FOR UPDATE` 行锁，内存数据库测试不覆盖这项能力。
