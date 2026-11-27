# Bug 追踪记录

| 编号 | 发现方式 | 问题 | 处理 | 验证 |
|---|---|---|---|---|
| BUG-01 | 首轮 pytest | 测试夹具中 `import app.models` 覆盖了 FastAPI `app` 变量，所有请求夹具报 `dependency_overrides` 属性错误 | 去除同名包导入；模型已由 `from app.models import Category` 完整加载 | 再运行接口测试，夹具可创建 |
| BUG-02 | 接口清单核对 | 缺少部署探针常用的健康检查接口 | 新增 `/api/health`，独立成 `routers/system.py` 便于单独维护 | `curl /api/health` 返回 200 与 connected |
| BUG-03 | 状态机测试 | 早期状态表以「当前状态 + 目标状态」为键，无法表达同一跳转的不同操作角色 | 改为「当前状态 + 目标状态 + 角色」三元键，补充买家在 `PENDING` 撤销，共六条合法转移 | 订单流转与 `available_actions` 用例全绿 |
| BUG-04 | 全量 pytest | 新增测试缺少 `make_user`、`seed_context.category_id` 夹具字段 | 补齐共享夹具并让样例商品描述含搜索关键词 | 全量 pytest 重跑 |
| BUG-05 | 接入 MySQL 后运行并发用例 | `tests/test_mysql_concurrency.py` 用 `os.getenv("TEST_DATABASE_URL")` 取测试库地址，而配置由 pydantic 从 `.env` 读入配置对象、不写回环境变量，导致该用例长期被 skip | 改为 `os.getenv(...) or get_settings().test_database_url`，并补充注释说明原因 | 用例由 skip 转为 pass：五个并发请求仅 1 单成功，其余 4 单 409 |
| BUG-06 | D8 补边界用例 | 昵称传三个空格能注册成功并存成空昵称：`min_length=1` 校验原字符串，长度 3 过闸，服务层再 `strip()` 才变空 | 在 `schemas` 增加 `strip_text`，`RegisterIn.nickname` 改用 `mode="before"` 校验器，先归一化再走长度约束 | `test_register_blank_nickname_by_spaces` 由 201 变 400 |
| BUG-07 | D8 补边界用例 | `PUT /api/users/me` 同样能把昵称改成一片空白，个人主页显示无名 | `ProfileIn.nickname` 复用同一校验器；顺带给 `phone` 去掉首尾空格 | `test_update_profile_blank_nickname_rejected` 由 200 变 400 |
| BUG-08 | D8 补边界用例 | 反向问题：1 字昵称、160 字标题只要带首尾空格就被判超长，提示「长度不合法」但用户数不出哪里超 | 校验顺序由「先长度后 strip」改为「先 strip 后长度」，`GoodsIn.title` 与两个昵称字段统一 | `test_title_boundary_length`、`test_register_nickname_near_max_length` 通过（160/80 可用、161/81 被拒） |

记录只包含实际发现和处理的问题。MySQL 并发用例已在本机 MySQL 8.0.46 的 `secondhand_market_test` 库跑通：五个并发请求仅 1 单成功，其余 4 单返回 409「商品已被抢购」。
