# Stage 5 可复用 YAML 数据校验设计

## 定位

项目名称始终为 **AI 辅助接口自动化测试框架**。短链接 SaaS 仅作为当前真实被测系统，用于证明框架可接入真实微服务、MySQL、Redis 和异步链路；任何短链接业务知识不得进入 `core/`、`db/` 等通用框架层。

## 架构边界

- `core/`：YAML 加载、请求执行、变量上下文、提取、统一断言；不出现 shortlink/gid/t_link 等业务概念。
- `db/`：通用 `MySQLClient` / `RedisClient`，只根据环境 YAML 建立数据源并执行通用读取操作。
- `utils/`：通用工具，例如 Java HashMod 计算；不包含具体表名或 Redis Key。
- `testcases/shortlink/`：短链接项目适配、复杂业务流程编排和 fixture。
- `testcases/shortlink/yaml/`：短链接接口、请求、提取、断言、level/tags 的唯一主要声明源。

## YAML 驱动原则

YAML 声明 method/url/header/params/json/extract/validation，以及 `level`、`tags`、`workflow` 元数据。根 `conftest.py` 在 collection 前从 YAML 动态注册业务 marker；环境 YAML 通过 `test_selection.include_suites` 选择当前 `testcases/<suite>/`，公共 Python 不判断具体项目名称。Pytest 文件按业务域归类，不再一个 Case 一个 Python 文件。数据库与 Redis 断言也写入 YAML，通过统一断言引擎执行。

复杂多步骤流程（Create -> Recycle -> Redirect -> Remove、Redirect -> 异步 Stats）保留少量 Python orchestration；Python 只负责编排，接口契约和可声明断言仍在 YAML。

## Stage 5 通用断言

- `db_exists`
- `db_eq`
- `db_gte`
- `redis_exists`
- `redis_eq`
- `redis_hfield_exists`
- `redis_ttl_between`
- `redis_scard_gte`

所有规则支持 `${...}` 动态变量；数据源通过 `source` 选择环境 YAML 中的命名连接。

## 短链接文件收敛

Python：`test_auth.py`、`test_link.py`、`test_redirect.py`、`test_statistics.py`。

YAML：`auth.yaml`、`link.yaml`、`redirect.yaml`、`statistics.yaml`。

Stage 4/4.5/5 的 18 个真实 Test Item 仍保留 6 smoke + 6 core + 6 regression，但不再扩散成大量单 Case 文件。
