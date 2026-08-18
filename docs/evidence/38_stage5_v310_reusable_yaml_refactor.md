# V3.1 Stage 5 可复用 YAML 数据源断言重构证据

## 1. 本次纠偏目标

项目主体始终是 **AI 辅助接口自动化测试框架**。当前短链接 SaaS 只作为真实 SUT，
因此 V3.1 正式替代 V3.0 中逐渐业务专用化的 Stage 5 结构。

当前边界：

```text
框架通用层
conftest.py
core/
db/
utils/

项目适配层
testcases/shortlink/
config/env.shortlink-local.yaml
```

架构守护测试会扫描公共 `core/db/utils/conftest.py/pytest.ini`，如果出现当前 SUT 的
表名、Redis Key 前缀、gid、short_uri 或 suite 名等业务 token，则测试失败。

## 2. 通用 Stage 5 能力

- `db/mysql_client.py`：命名 MySQL 数据源、懒加载、参数绑定、只读 SELECT/WITH；
- `db/redis_client.py`：命名 Redis 数据源、String/Hash/TTL/Set 只读操作；
- `core/assertion_engine.py`：`db_exists/db_eq/db_gte`；
- `core/assertion_engine.py`：`redis_exists/redis_eq/redis_hfield_exists/redis_ttl_between/redis_scard_gte`；
- `core/api_runner.py`：响应 extract 后再解析 validation，支持本次响应变量驱动数据层断言；
- `core/api_runner.py`：YAML `poll` 显式、有界最终一致性等待；
- `core/case_loader.py`：YAML `level/tags/workflow` 元数据；
- 根 `conftest.py`：从全部 YAML 自动注册业务 marker，并按环境 YAML `test_selection.include_suites` 选择项目 suite；
- `utils/sharding.py`：无业务表名的 Java String.hashCode/HASH_MOD 通用数学工具。

## 3. 当前真实 SUT 接入结构

短链接 18 个逻辑 Case 收敛为 4 个 Python 业务域入口 + 4 份 YAML：

```text
testcases/shortlink/
├── test_auth.py        + yaml/auth.yaml
├── test_link.py        + yaml/link.yaml
├── test_redirect.py    + yaml/redirect.yaml
└── test_statistics.py  + yaml/statistics.yaml
```

Smoke/Core/Regression 与业务 tags 来自 YAML，而不是“一 Case 一个 Python 文件”。
短链接专有的表名前缀、Redis Key、Gateway Header、Recycle 路径、Sentinel B100000
只存在于项目适配层，不进入公共框架。

## 4. TDD/回归证据

本次新增守护先观察到 RED，再实现 GREEN：

- 通用 Stage 5 修改文件的高密度中文注释检查初始失败，补充解释性注释后通过；
- `get_testcase_marker_names()` 缺失与公共 conftest 写死 suite 名的两条测试初始失败；
- 实现 YAML marker 自动发现、环境 YAML suite 选择后，两条测试转绿。

最终交付 ZIP 全新解压后的离线验证：

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests -q
100 passed

PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q
106 passed

shortlink-local smoke --collect-only
6/18 selected

shortlink-local core --collect-only
6/18 selected

shortlink-local regression --collect-only
6/18 selected

test env --collect-only
6 Demo tests

compileall
PASS
```

这里设置 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 只用于当前沙箱在最终 ZIP 全新解压验证时隔离全局安装的无关 Pytest 插件；
项目正常使用命令仍是 `python run.py ...`，没有把该环境变量写进框架运行逻辑。

## 5. 真实证据边界

- Stage 4 Smoke：用户 Windows 真实环境已有 `6 passed in 9.65s`；
- Stage 4.5 Core：用户上次为 5/6，唯一失败是前置 Create 的 Sentinel QPS；窄范围适配层修复待重跑；
- Stage 5 通用数据源能力：上述离线单元/集成测试已验证；
- 当前短链接 6 条 Regression：仍需用户 Windows 本机连接真实 MySQL/Redis 后验收，不使用 Fake Client 冒充真实通过。
