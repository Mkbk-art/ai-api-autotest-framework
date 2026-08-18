# AI 辅助接口自动化测试框架

> 当前版本：V3.2.6 / Stage 6 CI/CD + 外部私有环境覆盖

这是一个面向测试开发场景的**可复用接口自动化测试框架**。项目以 MIT 许可的
`zed123214/api-autotest-framework` 为学习与改造基线，围绕 Pytest + Requests + YAML
重新设计请求执行、运行时变量、统一断言、MySQL/Redis 数据校验、分层执行和后续 AI 能力。

**短链接 SaaS 只是当前接入的真实被测系统（SUT）**，用于证明框架能在真实微服务、Gateway、
ShardingSphere、MySQL、Redis、302 跳转和异步统计场景中工作；框架核心不会写死短链接表名、
Redis Key、gid、短域名或业务接口。

当前关系：

```text
真实被测系统（当前：Short-link SaaS；未来可换 Order/Payment/User 等）
                              ↑
                              │ 项目级 YAML + 少量 Adapter/Workflow
                              │
                    AI 辅助接口自动化测试框架
                              ↑
             Pytest + Requests + YAML + Allure
             VariableContext + AssertionEngine
                  MySQL / Redis + CI/CD + AI
```

## 1. 框架设计原则

### 1.1 YAML 是普通接口测试的主要声明源

可声明内容优先放 YAML：

- `method / url / header / params / json`；
- `extract`；
- `validation`；
- `request_options`；
- `poll`；
- `level`：`smoke/core/regression`；
- `tags`：业务模块 marker；
- `workflow`：只用于告诉少量 Python 编排代码当前 Case 属于哪个多步骤流程。

Python 测试入口主要负责：

```text
读取 YAML
→ pytest 参数化
→ 准备必要 fixture
→ ApiRunner.run()
```

只有 Create -> Recycle -> Redirect -> Remove、Redirect -> Async Stats 这类多步骤流程才保留少量
Python orchestration；接口请求字段、SQL、Redis Key 期望和断言规则仍尽量留在 YAML。

### 1.2 框架核心与被测项目隔离

```text
conftest.py              # 所有项目共享的 collection / fixture glue

core/
├── api_runner.py
├── request_client.py
├── variable_context.py
├── assertion_engine.py
├── extractor.py
└── case_loader.py

# 通用数据源能力
db/
├── mysql_client.py
└── redis_client.py

# 通用动态函数/工具
utils/

# 当前真实 SUT 适配层
testcases/shortlink/
├── conftest.py
├── support.py
├── test_auth.py
├── test_link.py
├── test_redirect.py
├── test_statistics.py
└── yaml/
    ├── auth.yaml
    ├── link.yaml
    ├── redirect.yaml
    └── statistics.yaml
```

`core/`、`db/`、通用 `utils/` 不包含 `t_link_*`、`short-link:*`、`gid`、`short_uri` 等短链接业务知识。

如果以后接入订单项目，目标结构是：

```text
config/env.order-local.yaml
testcases/order/
├── conftest.py
├── support.py            # 仅当订单项目确实需要项目级适配
├── test_order.py
├── test_payment.py
└── yaml/
    ├── order.yaml
    └── payment.yaml
```

原则上**不修改 `core/`、`db/`、根 `conftest.py` 和 `pytest.ini`**。

环境 YAML 负责选择当前 suite，例如：

```yaml
test_selection:
  include_suites:
    - order
```

公共 `conftest.py` 不判断 `order-local`、`shortlink-local` 这类环境名称；它只读取
`include_suites`。与此同时，YAML 中声明的 `tags` 会在 collection 前自动注册，
所以新项目增加 `order/payment/refund` 等业务标签也不需要编辑公共 `pytest.ini`。

## 2. 当前通用框架能力

- Pytest 参数化执行；
- Requests 请求封装；
- YAML 数据驱动；
- 多环境 `ConfigManager`；
- `${config(section,key)}` 读取当前环境 YAML；
- `${variable}` 运行时动态替换；
- DebugTalk 动态函数，例如随机值、时间、Hash；
- `VariableContext` 的 `session / scenario / case` 逻辑作用域；
- JsonPath 响应提取；
- 相对 URL 与绝对 URL；
- `allow_redirects=false` 等受控 Requests 选项；
- YAML `level/tags` 自动转为 Pytest marker，并在 collection 前动态注册业务标签；
- 环境 YAML `test_selection.include_suites` 决定本次收集哪个项目 suite；
- YAML `poll` 有界最终一致性查询；
- JUnit XML / Allure 兼容；
- 日志敏感 Header 脱敏；
- 框架自身 Unit / Integration / Mock regression；
- GitHub Actions 公共框架 CI；
- Jenkins 参数化真实环境 Pipeline；
- JUnit / Allure Results / run.json / logs 报告归档。

## 3. 统一 YAML 断言引擎

普通响应断言包括：

```text
status_code
exists / not_exists
eq / ne
contains
in / not_in
gt / gte / lt / lte
header_eq / header_contains
response_time_lt
```

Stage 5 把 MySQL / Redis 校验正式做成了**框架级 YAML 断言能力**，而不是短链接专用 Probe。

### 3.1 通用 MySQL 断言

```yaml
validation:
  - db_exists:
      source: default
      sql: "SELECT id FROM demo_order WHERE order_no=%s LIMIT 1"
      params: ["${order_no}"]

  - db_eq:
      source: default
      sql: "SELECT status FROM demo_order WHERE order_no=%s LIMIT 1"
      params: ["${order_no}"]
      expected: PAID

  - db_gte:
      source: default
      sql: "SELECT COUNT(*) FROM demo_order_item WHERE order_no=%s"
      params: ["${order_no}"]
      expected: 1
```

`db/mysql_client.py`：

- 从 `data_sources.mysql.<source>` 加载命名数据源；
- 使用参数化 SQL；
- 只允许 `SELECT / WITH`；
- 不提供业务数据库写接口；
- 不知道任何具体业务表名。

### 3.2 通用 Redis 断言

Redis 连接的 RESP 协议属于**环境级数据源配置**，不会由 redis-py 的主版本默认值决定：

```yaml
data_sources:
  redis:
    default:
      host: 127.0.0.1
      port: 6379
      db: 0
      password: null
      protocol: 2
```

框架默认使用 RESP2，以兼容 Redis 5.x 和不支持 `HELLO` 的 Redis 兼容代理；如果某个新项目明确要求 RESP3，可以只在自己的 `env.<project>.yaml` 中改为 `protocol: 3`，无需修改 `db/redis_client.py`。


```yaml
validation:
  - redis_exists:
      source: default
      key: ${cache_key}
      expected: true

  - redis_eq:
      source: default
      key: ${cache_key}
      expected: ${expected_value}

  - redis_hfield_exists:
      source: default
      key: ${session_key}
      field: ${session_id}

  - redis_ttl_between:
      source: default
      key: ${session_key}
      min: 1
      max: 1800

  - redis_scard_gte:
      source: default
      key: ${unique_set_key}
      expected: 1
```

`db/redis_client.py` 只提供通用只读 String/Hash/Set/TTL 操作，不知道登录态、短链接、UV/UIP 等业务概念。

## 4. 通用命名数据源配置

每个环境可以声明自己的命名数据源：

```yaml
data_sources:
  mysql:
    default:
      host: 127.0.0.1
      port: 3306
      database: your_database
      username: your_user
      password: your_password
      charset: utf8mb4
      connect_timeout: 5

  redis:
    default:
      host: 127.0.0.1
      port: 6379
      db: 0
      password: null
      socket_timeout: 5
```

更换项目时修改环境 YAML 即可；AssertionEngine 按 `source` 懒加载对应 Client。

## 5. 当前真实验证项目：Short-link SaaS

短链接项目只作为框架真实接入案例。当前 18 个逻辑 Case 被归并到 **4 个 Python 业务域入口 + 4 个 YAML**：

```text
Auth          → test_auth.py       + yaml/auth.yaml
Link          → test_link.py       + yaml/link.yaml
Redirect      → test_redirect.py   + yaml/redirect.yaml
Statistics    → test_statistics.py + yaml/statistics.yaml
```

不再采用“一条异常用例一个 Python/YAML 文件”的碎片化结构。

当前分层：

```text
Smoke 6
├── Login
├── Group
├── Create
├── Page
├── Redirect
└── Statistics

Core 6
├── 错误密码 Login
├── Group 缺 token
├── Create 缺 token
├── Create 非法 originUrl
├── 不存在 shortUri
└── 回收后再次访问

Regression 6
├── Login Redis Hash + TTL
├── Create MySQL 持久化
├── Recycle MySQL 状态迁移
├── Create/Recycle Redis goto cache
├── Redirect Redis UV/UIP
└── Statistics MySQL 最终持久化
```

这些 Case 的 `smoke/core/regression` 以及业务 marker 不再主要写在 Python 装饰器/`pytest.ini` 里，而由 YAML：

```yaml
level: regression
tags: [real, shortlink, statistics, database]
```

自动转换，并由公共 Pytest glue 在 collection 前动态注册。

## 6. 短链接项目自己的适配边界

短链接项目确实存在特殊规则，例如：

- Gateway 使用 `username + token` Header；
- ShardingSphere `HASH_MOD`；
- `t_link_*` 物理表；
- 登录、goto、UV/UIP Redis Key 前缀；
- `recycle-bin/save -> remove`；
- Create 的 Sentinel 临时限流；
- `nurl.ink` 本地域名映射。

这些内容只允许存在于：

```text
config/env.shortlink-local.yaml
testcases/shortlink/support.py
testcases/shortlink/yaml/*.yaml
```

其中 Java `String.hashCode()` / HASH_MOD 数学计算抽成无表名的通用 `utils/sharding.py`，其他使用同类算法的 Java 项目也能复用。

## 7. 本地短链接环境配置

编辑：

```text
config/env.shortlink-local.yaml
```

登录账号直接从 YAML 读取，不需要再执行：

```text
export SHORTLINK_TEST_USERNAME=...
export SHORTLINK_TEST_PASSWORD=...
```

当前配置分成四类：

```text
api.*
→ 通用 API 环境

test_selection.include_suites
→ 当前环境要收集的项目 suite

shortlink.*
→ 当前 SUT 项目适配参数

data_sources.mysql / data_sources.redis
→ 通用命名数据源
```

交付包保留密码占位符，使用时在本机 YAML 修改即可。

## 8. Stage 4.5 Sentinel 小修

用户真实 Core 上一次得到 `5 passed, 1 failed`。唯一失败发生在 E6 真正执行回收流程之前：
前置 Create 被当前 SUT 的 Sentinel QPS 限流，返回 `B100000`。

当前处理保持在**短链接项目适配层**：

```text
正式 Create 测试
→ 单次严格请求，不重试

用于 fixture/多步骤流程准备数据的 Create
→ 仅识别当前 SUT 已确认的 B100000
→ 按 shortlink.create_retry 有界重试
→ 其他错误立即失败
```

通用 `RequestClient`/`ApiRunner` 不认识 `B100000`，所以换项目不会继承短链接业务码。

## 9. 安装

推荐 Python 3.11：

```bash
conda create -n autotest python=3.11 pip -y
conda activate autotest
python -m pip install -r requirements-dev.txt -c constraints.txt
```

Stage 5 通用数据源能力增加：

```text
PyMySQL>=1.1
redis>=5.0
```

## 10. 执行

框架 / Mock：

```bash
python run.py --env test --level smoke
python run.py --env test --level core
python run.py --env test --level regression
python -m pytest tests -q
```

当前真实短链接 SUT：

```bash
python run.py --env shortlink-local --level smoke --collect-only
python run.py --env shortlink-local --level smoke

python run.py --env shortlink-local --level core --collect-only
python run.py --env shortlink-local --level core

python run.py --env shortlink-local --level regression --collect-only
python run.py --env shortlink-local --level regression
```

Collection 设计保持：

```text
shortlink-local 总计 18
Smoke       6 / 18
Core        6 / 18
Regression  6 / 18
```

## 11. CI/CD、真实项目接入与私有配置边界

项目主体始终是 **AI 辅助接口自动化测试框架**。短链接 SaaS 位于 Project Adapter/Test Cases 层，是一个可公开参考的真实 SUT 接入示例，不进入框架核心。

Stage 6 的 CI 职责：

```text
GitHub Actions
→ 云端验证公共框架 + Mock/Demo
→ 不依赖开发者本机真实 SUT

Jenkins
→ 部署在能访问目标测试环境的 Agent
→ ENV_NAME 选择公开命名环境
→ LEVEL 选择 smoke/core/regression
→ ENV_FILE 可选指向仓库外私有覆盖 YAML
→ 始终调用统一 run.py
```

公共真实项目配置可以继续上传 GitHub：

```text
config/env.<project>.yaml        # 敏感值使用 CHANGE_ME
testcases/<project>/            # 真实项目适配与 YAML 用例
```

真实账号、数据库密码等只保存在仓库外覆盖 YAML。该文件可以只写需要覆盖的字段；ConfigManager 以：

```text
CLI > env vars > external env YAML > env.<name>.yaml > config.yaml
```

递归合并。统一 Runner 同时支持：

```bash
python run.py --env <project> --env-file "<external-yaml>" --level smoke
```

Jenkins 参数为：

```text
ENV_NAME = config/env.<name>.yaml 对应环境名
LEVEL    = smoke / core / regression
ENV_FILE = 可选的 Jenkins Agent 仓库外覆盖 YAML 路径
```

`ENV_FILE` 留空时保持现有 Mock/公共配置行为；有值时 Jenkins 仅把路径临时注入 `API_TEST_ENV_FILE`，不复制私有 YAML 到 Workspace，也不归档其内容。因此以后接入其他 SUT，不需要修改公共 CI 调度逻辑。详细说明见 `docs/10_CI-CD接入说明.md`。

## 12. 证据边界

- Stage 4 Smoke：用户 Windows 真实环境 `6/6`；
- Stage 4.5 Core：用户 Windows 真实环境 `6/6`；
- Stage 5 Regression：用户已确认 Redis 协议修复后的完整回归测试通过，因此通用 MySQL/Redis YAML 数据断言已完成真实 SUT 验收；
- Stage 6：GitHub Actions 已真实绿色；Jenkins `ENV_NAME=test, LEVEL=smoke` 已真实完成 2/2 Mock smoke、JUnit 与 Artifact 归档；外部私有环境 YAML 机制已实现并通过离线契约验证，真实 SUT Jenkins smoke 待本机最终执行。

## 13. 后续路线

项目定位始终保持“AI 辅助接口自动化测试框架”，后续继续按照最初路线增强框架，而不是继续无限扩张短链接脚本：

```text
Stage 5 ✅
通用 MySQL / Redis YAML 数据断言 + 真实 SUT 验证
        ↓
当前 Stage 6
GitHub Actions / Jenkins / 报告归档
        ↓
Stage 7
AI：接口文档 → YAML 用例草稿
AI：失败日志 → 原因与排查建议
        ↓
Stage 8
工程质量、README、架构图、简历与面试材料
```

## 14. 开源来源与个人工作边界

上游来源和 MIT 许可：

- `LICENSE`
- `BASELINE_SOURCE.md`
- `THIRD_PARTY_NOTICES.md`

当前个人改造重点包括：基线缺陷审查、框架目录重构、VariableContext、统一断言、YAML marker/poll、
通用 MySQL/Redis 数据源断言、真实 SUT 接入、最终一致性、测试数据清理，以及后续 CI/CD 与 AI 增强。
