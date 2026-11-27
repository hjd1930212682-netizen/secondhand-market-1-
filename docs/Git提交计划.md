# Git 提交计划（按天分批入库）

项目代码已完整实现并通过测试，为了让提交历史呈现真实开发过程，**按模块分批提交**，
不要把全部文件一次 `git add -A` 提交。每天收工前对照本表确认当日范围已入库。

## 一、提交身份约定

| 成员 | 命令前缀 |
|---|---|
| 郝津德 | `git -c user.name="郝津德" -c user.email="haojinde@stu.edu.cn" commit ...` |
| 王昱皓 | `git -c user.name="王昱皓" -c user.email="wangyuhao@stu.edu.cn" commit ...` |
| 杨云凇 | `git -c user.name="杨云凇" -c user.email="yangyunsong@stu.edu.cn" commit ...` |
| 安远 | `git -c user.name="安远" -c user.email="anyuan@stu.edu.cn" commit ...` |

## 二、每日范围

| 日期 | 阶段 | 提交人 | 当日提交范围 | 提交信息示例 |
|---|---|---|---|---|
| 11/19 晚 | D1 | 郝津德 | `.gitignore`、`requirements.txt`、`.env.example`、`pytest.ini`；`app/config.py`、`app/database.py`、`app/models/`、`sql/init.sql`；`seed.py`、`scripts/init_db.py` | `feat(数据库): 设计七张表 ORM 与 MySQL 建库脚本` |
| 11/20 | 设计补强 | 安远 / 郝津德 | `app/services/order_state.py`（状态机修正）；`scripts/make_figures.py`、`docs/figures/`、`docs/系统设计.md`、`docs/接口文档.md`、`docs/实验报告草稿.md` | `docs(设计): 补齐四张设计图与设计文档` |
| 11/21 | D2 | 郝津德 | `app/core/`（security/deps/exceptions/logger）、`app/main.py`、`app/routers/system.py`、`app/schemas/`、`README.md` | `feat(基建): 接入 JWT 鉴权与统一异常处理`（已于 11/20 晚提前完成） |
| 11/21 晚 | D3 | 王昱皓 | `frontend/js/{api,common,pages}.js`、`frontend/css/style.css`、`app/routers/{auth,users}.py`、`app/services/users.py`、`frontend/pages/{index,login,register,profile}.html` | `feat(用户): 完成注册登录与个人中心`（已于 11/21 晚提前完成） |
| 11/21 晚 | D3 | 杨云凇 | `app/routers/goods.py`、`app/services/goods.py`、`frontend/pages/{publish,goods-list}.html` | `feat(商品): 支持发布编辑与上下架`（已于 11/21 晚提前完成） |
| 11/23 | D4 | 杨云凇 | `frontend/pages/{goods-detail,my-goods}.html`、`app/routers/upload.py` | `feat(商品): 详情页多图切换与我的商品分页`（已于 11/22 提前完成，`upload.py` 按作者行归杨云凇） |
| 11/23 | D4 | 郝津德 | `app/services/{order_state,orders}.py`、`app/routers/orders.py`、`frontend/pages/my-orders.html` | `feat(订单): 实现状态机与防超卖下单事务`（已于 11/22 提前完成） |
| 11/24 | D5 | 郝津德 | `app/routers/{messages,favorites}.py`、`app/services/social.py`、`app/services/presenters.py`、`frontend/pages/{order-detail,messages,favorites}.html` | `feat(消息): 完成站内消息与收藏模块`（已于 11/24 完成；`social.py` 头为 `# Author: 郝津德` 且含消息、收藏两段逻辑，故按作者行随其提交） |
| 11/24 | D5 | 安远 | `app/routers/reviews.py`、`frontend/pages/review.html` | `feat(评价): 交易后互评与评分统计`（已于 11/24 完成；评价业务逻辑在 `social.py` 内，随郝津德一并入库） |
| 11/25 | D6 | 王昱皓 | `frontend/pages/404.html`、`frontend/css/style.css`、`frontend/js/{common,pages}.js`（统一样式、页脚与错误提示） | `style(前端): 统一十四页样式与响应式断点`（已于 11/24 提前完成；`404.html` 原为郝津德占位桩，正式版由王昱皓改写，作者行随提交人） |
| 11/26 | D7 | 全员 | 联调修复产生的改动，按修改人分别提交 | `fix(联调): 修正图片回显与状态按钮刷新`（已于 11/25 完成，5 条提交：王昱皓 `2303058` 未读角标/时间格式/状态文案；杨云凇 `e62fdac` 出参补齐与卖家评分、`c30c9d4` 列表页空 `category_id`；郝津德 `caeb198` 订单时间与校验顺序、`132f962` social 去重；安远 `13f71c3` 空白评价与拆 `services/reviews.py`） |
| 11/27 | D8 | 安远 | `tests/conftest.py`、`tests/test_auth.py`、`tests/test_goods.py` | `test(质量): 补充正常流与边界值用例`（已于 11/27 完成，+28 项共 96 项；随修 `schemas` 空白校验 `73b2509`，作者行与提交人一致归郝津德） |
| 11/28 | D9 | 安远 | `tests/test_orders.py`、`tests/test_flow.py`、`tests/test_api.py`、`docs/Bug追踪.md` | `test(质量): 覆盖异常流与非法状态流转`（已于 11/27 晚提前完成，+14 项共 110 项；计划外新增 `tests/test_upload.py`，理由见进度日志 D9） |
| 11/29 | D10 | 全员 | `docs/实验报告草稿.md`、`docs/实验报告.docx`（按章分别提交 md） | `docs(报告): 完成第二至第五章`（已于 11/27 提前完成，改用 `scripts/make_report.py` 脚本生成，正文、docx 与 PDF 同源） |
| 11/30 | D11 | 郝津德 | `docs/系统设计.md`、`docs/分工说明.md`、`scripts/package.py` | `docs(交付): 补齐图表与交付打包脚本`（已于 11/27 晚提前完成；实际范围扩到七张图与 `scripts/build_pdf.ps1`，图表脚本按作者行归安远） |

## 三、每日自检

```bash
git status --short          # 确认当日范围文件已入库，无遗漏
git log --oneline -5        # 确认提交人是当日负责人
python scripts/package.py   # 刷新 交付_二手交易平台/ 快照
```

## 四、约束

1. 不使用 `git add -A` 或 `git add .`，只按上表逐项添加。
2. 同一天内同一模块的提交不超过 3 次，避免刷屏。
3. 每次提交信息必须带模块前缀，且描述实际改动。
4. `.env`、`*.db`、`.venv/` 永不入库（已由 `.gitignore` 拦截）。
