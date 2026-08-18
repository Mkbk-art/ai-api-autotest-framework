# Stage 5 Infrastructure Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 完成 Stage 4.5 Sentinel 小修复，并新增 6 条 Stage 5 MySQL/Redis 真实基础设施回归测试，使本地账号与基础设施连接信息全部由 YAML 动态配置。

**Architecture:** 保持 YAML → ApiRunner → RequestClient 的业务执行主线；Stage 5 通过独立 `infrastructure.py` 提供只读 MySQL/Redis 探针。ShardingSphere HASH_MOD 在 Python 中严格复刻 Java String.hashCode 语义，DB/Redis fixture 仅在对应 regression 用例被请求时建立连接。

**Tech Stack:** Python 3.11, Pytest 9, Requests, PyYAML, PyMySQL, redis-py, MySQL 8-compatible protocol, Redis, Apache ShardingSphere 5.3.2 semantics.

## Global Constraints

- 所有新增/修改 Python 与 YAML 文件必须保留高密度中文注释。
- 不直接写 MySQL/Redis 业务状态；测试数据仍通过真实 API 创建与清理。
- 不硬编码真实密码；`env.shortlink-local.yaml` 提供明确的本地可编辑占位值。
- Stage 4 Smoke 6 条和 Stage 4.5 Core 6 条的 marker 数量保持不变。
- Stage 5 新增 6 条 `regression` 测试。
- Sentinel 只对 fixture/前置 Create 的明确 `B100000` 做有界重试，正常 Create Smoke 不重试。

---

### Task 1: YAML 配置账号与 Config DSL

**Files:**
- Modify: `config/env.shortlink-local.yaml`
- Modify: `core/api_runner.py`
- Modify: `utils/debugtalk.py`
- Modify: `testcases/shortlink/conftest.py`
- Modify: `testcases/yaml/shortlink/auth.yaml`
- Modify: `testcases/yaml/shortlink/auth_invalid.yaml`
- Test: `tests/unit/test_debugtalk.py`
- Test: `tests/unit/test_shortlink_support.py`

- [x] 写失败测试：DebugTalk 可读取注入 runtime_config，YAML 登录不再引用 `env(SHORTLINK_TEST_*)`。
- [x] 运行目标测试确认 RED。
- [x] 为 ApiRunner/DebugTalk 注入 runtime_config，并实现 `${config(section,key)}`。
- [x] shortlink fixture 从 runtime_config 构造凭据；更新 YAML 中文注释。
- [x] 运行目标测试确认 GREEN。

### Task 2: Sentinel 前置 Create 有界重试

**Files:**
- Modify: `testcases/shortlink/support.py`
- Test: `tests/unit/test_shortlink_support.py`

- [x] 写失败测试：第一次 Create 返回 B100000、第二次成功时仅重试一次；其他业务码不重试。
- [x] 运行确认 RED。
- [x] 从 create.yaml 读取动态请求体，使用前置 helper 发请求；仅 B100000 按配置等待并重试。
- [x] 运行确认 GREEN。

### Task 3: MySQL/Redis 基础设施探针

**Files:**
- Create: `testcases/shortlink/infrastructure.py`
- Modify: `testcases/shortlink/conftest.py`
- Modify: `requirements.txt`
- Test: `tests/unit/test_shortlink_infrastructure.py`

- [x] 写失败测试：Java String.hashCode/HASH_MOD 路由、配置解析、SQL 参数化、Redis Key 构造。
- [x] 运行确认 RED。
- [x] 实现 MySQLSettings/RedisSettings、ShortlinkDatabaseProbe/ShortlinkRedisProbe 与 lazy connection factory。
- [x] 运行确认 GREEN。

### Task 4: Stage 5 MySQL 3 条真实 Regression

**Files:**
- Create: `testcases/shortlink/test_stage5_mysql.py`
- Modify: `pytest.ini`
- Test: `tests/integration/test_collection_count.py`

- [x] 写 collection/结构失败测试，要求 regression=6。
- [x] 运行确认 RED。
- [x] 实现：物理分片 Create、Recycle 状态迁移、Stats 落库 3 条测试。
- [x] 运行目标 collection 确认 GREEN。

### Task 5: Stage 5 Redis 3 条真实 Regression

**Files:**
- Create: `testcases/shortlink/test_stage5_redis.py`
- Test: `tests/integration/test_collection_count.py`

- [x] 扩展失败测试，要求短链接总 Test Item=18、smoke=6、core=6、regression=6。
- [x] 运行确认 RED。
- [x] 实现：登录 Hash+TTL、Goto Cache 生命周期、UV/UIP Set 3 条测试。
- [x] 运行 collection 确认 GREEN。

### Task 6: 文档、全量回归与最终交付

**Files:**
- Modify: `README.md`
- Modify: `docs/08_阶段4真实SaaS接入.md`
- Create: `docs/09_阶段5MySQL与Redis深层校验.md`
- Modify: `AI_API_Autotest_Framework_Project_Plan_Latest.md`
- Modify: `docs/00_项目计划书_Latest.md`
- Create: `docs/evidence/37_stage5_complete_offline_verification.md`

- [x] 更新唯一项目计划为 Stage 5 编码完成/待真实环境验收。
- [x] 运行 `pytest tests -q`。
- [x] 运行默认离线全量。
- [x] 运行 shortlink-local smoke/core/regression collect-only。
- [x] 运行 compileall、凭据来源扫描、固定域名/旧 env 引用扫描。
- [x] 清理缓存/报告临时产物，打最终 ZIP。
- [x] 从最终 ZIP 全新解压并重复验证。
