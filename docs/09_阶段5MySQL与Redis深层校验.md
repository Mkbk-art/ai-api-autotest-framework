# Stage 5：通用 MySQL / Redis YAML 数据源断言与真实项目验证

## 1. 阶段定位

Stage 5 的目标不是给短链接项目增加一组专用数据库脚本，而是补齐 **AI 辅助接口自动化测试框架**
最初计划中的 MySQL / Redis 多维断言能力。

当前短链接 SaaS 只负责回答一个问题：

> 这些通用数据源能力能不能在一个真实存在 Gateway、ShardingSphere、MySQL、Redis、302 跳转和异步消费的系统里工作？

因此本阶段严格保持两条边界：

```text
通用能力
core/assertion_engine.py
db/mysql_client.py
db/redis_client.py
utils/sharding.py

当前 SUT 适配
testcases/shortlink/support.py
testcases/shortlink/yaml/*.yaml
config/env.shortlink-local.yaml
```

`core/`、`db/` 不出现短链接表名、Redis Key 前缀、gid、short_uri 等业务概念。

## 2. 为什么数据库/缓存断言也必须 YAML 驱动

原项目主线是：

```text
YAML
→ ApiRunner
→ RequestClient
→ Extractor
→ AssertionEngine
```

如果到了 Stage 5 又在 Python 中手写：

```python
row = mysql.query(...)
assert row["status"] == 1
```

那么数据库校验会重新退化为脚本式测试，无法体现框架复用性。

因此 Stage 5 使用：

```yaml
validation:
  - db_eq:
      source: default
      sql: "SELECT status FROM demo WHERE id=%s"
      params: ["${resource_id}"]
      expected: 1
```

Python 只负责复杂流程顺序；SQL、参数、预期值继续属于 Case 声明。

## 3. 通用 MySQL Client

`db/mysql_client.py` 负责：

- 从 `data_sources.mysql.<source>` 读取命名连接；
- 懒加载 PyMySQL；
- 参数化查询；
- `fetch_one()`；
- `fetch_scalar()`；
- 只允许 `SELECT / WITH`，不提供业务写操作；
- 密码字段不进入 dataclass repr；
- YAML 中纯数字密码会规范化为字符串。

它不知道任何业务表名。

## 4. 通用 Redis Client

`db/redis_client.py` 负责：

- 从 `data_sources.redis.<source>` 加载命名连接；
- 懒加载 redis-py；
- `exists()`；
- `get()`；
- `hexists()`；
- `ttl()`；
- `scard()`。

它不知道“登录态”“goto cache”“UV/UIP”是什么。

## 5. 统一断言引擎新增规则

### 5.1 MySQL

```text
db_exists
db_eq
db_gte
```

示例：

```yaml
- db_exists:
    source: default
    sql: "SELECT id FROM demo WHERE business_id=%s LIMIT 1"
    params: ["${business_id}"]

- db_eq:
    source: default
    sql: "SELECT status FROM demo WHERE business_id=%s LIMIT 1"
    params: ["${business_id}"]
    expected: ACTIVE
```

### 5.2 Redis

```text
redis_exists
redis_eq
redis_hfield_exists
redis_ttl_between
redis_scard_gte
```

Hash field 的断言失败信息不会回显真实 field 原文，因为 field 可能是 token/session id 等敏感值。

## 6. YAML 元数据也进入框架层

每条 Case 可以声明：

```yaml
level: regression
tags: [real, database]
workflow: create_db
```

`core/case_loader.py` 自动把 `level/tags` 转成 Pytest marker；根 `conftest.py` 会在 collection 前扫描 YAML 并动态注册这些 marker，因此新项目的业务标签不需要手工追加到公共 `pytest.ini`。

因此普通新 Case 不需要再：

1. 新建 Python 文件；
2. 重复写 `@pytest.mark.regression`；
3. 重复写模块 marker；
4. 重复维护同一接口参数。

`workflow` 不代表框架业务逻辑，只用于复杂多步骤场景筛选 Case。

环境隔离也不再通过 Python 判断具体环境名。每份 `env.<name>.yaml` 可以声明：

```yaml
test_selection:
  include_suites:
    - order
```

公共 collection hook 只理解“suite 白名单”，不知道当前项目叫短链接、订单还是支付。

## 7. 当前短链接真实验证如何接入

短链接项目的特殊知识只存在项目适配层，例如：

```text
ShardingSphere HASH_MOD
物理表名前缀
Redis Key 前缀
Gateway username/token Header
回收站 Save -> Remove
Sentinel B100000
```

`support.py` 把这些业务规则转换成普通运行时变量：

```text
gid
↓ 项目 Sharding 规则
link_table

full_short_url
↓ 项目 Key 前缀
login_redis_key / goto_redis_key / uv_redis_key / uip_redis_key
```

然后 YAML 只把最终变量交给通用断言：

```yaml
- db_eq:
    source: default
    sql: "SELECT enable_status FROM `${link_table}` WHERE ..."
    params: ["${gid}", "${full_short_url}"]
    expected: 1
```

AssertionEngine 完全不需要知道 `link_table` 是什么业务。

## 8. 当前 6 条 Regression 的意义

这些不是“6 个 Stage5 Python 脚本”，而是分布在 4 个业务域 YAML 中的 6 个真实 Case：

```text
Auth
└── Login Redis Hash + TTL

Link
├── Create MySQL 持久化
├── Recycle MySQL 状态迁移
└── Create/Recycle Redis goto cache

Redirect
└── Redis UV/UIP Set

Statistics
└── MySQL 最终统计持久化
```

Python 仍然只有认证、链接、跳转、统计 4 个业务域入口。

## 9. ShardingSphere 为什么属于项目 Adapter

Python 直接连接 MySQL 不经过 Java ShardingSphere Driver，因此当前短链接 SUT 必须先根据真实
`HASH_MOD` 规则计算物理表。

框架只保留一个无业务表名的通用算法工具：

```text
utils/sharding.py
java_string_hashcode(value)
java_hash_mod(value, shard_count)
```

而：

```text
link_table_prefix: t_link_
goto_table_prefix: t_link_goto_
shard_count: 16
```

全部位于 `env.shortlink-local.yaml -> shortlink.storage`。

换成一个不分库分表的项目，可以完全不用这个 adapter。

## 10. 如何接入下一个项目

例如未来接入订单系统：

```text
config/env.order-local.yaml   # test_selection.include_suites: [order]

testcases/order/
├── conftest.py
├── support.py              # 只有需要项目适配时才创建
├── test_order.py
└── yaml/
    └── order.yaml
```

订单 YAML 可以直接使用现有：

```text
HTTP Assertions
VariableContext
poll
db_exists/db_eq/db_gte
redis_exists/redis_eq/...
```

若接入订单项目还需要修改 `core/assertion_engine.py`、根 `conftest.py` 或公共 `pytest.ini` 才能完成普通 HTTP/数据库/Redis 校验和业务标签收集，就说明当前 Stage 5 复用边界设计失败；这条规则将作为后续架构守护原则。

## 11. 当前验收边界

框架级数据源能力可以通过 Fake Client 单元测试验证。

短链接 Regression 是否真实通过，仍必须由用户本机：

```bash
python run.py --env shortlink-local --level regression
```

连接真实 MySQL / Redis 后确认。

Mock、Fake Response 和 `--collect-only` 不冒充真实数据层验收证据。
