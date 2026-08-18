# Stage 4.5 Complete Negative/Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变 6 条真实 Smoke 的前提下，一次性补齐 6 条 Stage 4.5 Core 异常/边界用例，并形成可由用户 Windows 一次验收的完整版本。

**Architecture:** 继续以 YAML 为请求与断言的唯一业务契约入口；ApiRunner 负责动态变量、绝对 URL、受控 request options 和统一 Assertions。E6 只新增“进入回收站/最终移除”两个可复用业务 helper，E5/E6 通过 `header_contains` 兼容相对/绝对 notfound Location。

**Tech Stack:** Python 3.11+、Pytest、Requests、PyYAML、现有 ApiRunner/VariableContext/DebugTalk、真实 Spring Cloud Gateway/Admin/Project SaaS。

## Global Constraints

- 不提交、打印或重复真实密码、Token、数据库/Redis 凭据。
- 6 条异常用例必须全部使用 `core`，不得污染已真实验证的 6 条 Smoke。
- 新增/修改 Python 和 YAML 必须带高密度中文注释。
- 不直接写 MySQL 来构造或清理业务状态。
- 离线结果与真实 SaaS 结果必须分开描述。

---

### Task 1: E1/E2 鉴权异常基线

**Files:**
- `utils/debugtalk.py`
- `testcases/yaml/shortlink/auth_invalid.yaml`
- `testcases/yaml/shortlink/group_unauthorized.yaml`
- `testcases/shortlink/test_auth_invalid.py`
- `testcases/shortlink/test_group_unauthorized.py`
- `tests/unit/test_debugtalk.py`
- `tests/unit/test_shortlink_support.py`

- [x] 先写错误密码与缺 token 契约测试并观察 RED。
- [x] 新增 `invalid_password()`，确保不读取真实密码。
- [x] 新增 E1/E2 YAML 与真实测试模块。
- [x] 运行定向测试确认 GREEN。

### Task 2: E3 Create 缺 token

**Files:**
- `testcases/yaml/shortlink/create_unauthorized.yaml`
- `testcases/shortlink/test_create_unauthorized.py`
- `tests/unit/test_shortlink_support.py`

- [x] 先写 YAML/ApiRunner 契约测试。
- [x] 请求体保持合法，Header 只有 username，没有 token。
- [x] 断言 Gateway HTTP 401、status=401、固定 message。
- [x] 定向回归通过。

### Task 3: E4 非法 originUrl

**Files:**
- `testcases/yaml/shortlink/create_invalid_origin.yaml`
- `testcases/shortlink/test_create_invalid_origin.py`
- `tests/unit/test_shortlink_support.py`

- [x] 先写正常 auth/gid + 单一非法 originUrl 契约测试。
- [x] 使用 `not-a-valid-url`，其他 Create 字段保持正常。
- [x] 断言 HTTP 200、业务 code != 0、无 `data.fullShortUrl`。
- [x] 定向回归通过。

### Task 4: E5/E6 notfound 与回收状态

**Files:**
- `core/assertion_engine.py`
- `testcases/shortlink/support.py`
- `testcases/yaml/shortlink/redirect_notfound.yaml`
- `testcases/yaml/shortlink/redirect_recycled.yaml`
- `testcases/shortlink/test_redirect_notfound.py`
- `testcases/shortlink/test_redirect_recycled.py`
- `tests/unit/test_assertion_engine.py`
- `tests/unit/test_shortlink_support.py`

- [x] 先写 `header_contains` 失败测试和 Redirect 契约测试。
- [x] Assertions 支持响应头包含片段。
- [x] 拆分 `save_shortlink_to_recycle_bin()` 与 `remove_shortlink_from_recycle_bin()`。
- [x] E5 使用随机 shortUri + `allow_redirects=false`。
- [x] E6 创建 -> save -> Redirect -> finally remove。
- [x] 定向回归通过。

### Task 5: Collection、文档与完整验证

**Files:**
- `pytest.ini`
- `tests/integration/test_collection_count.py`
- `tests/unit/test_yaml_loader.py`
- `README.md`
- `docs/00_项目计划书_Latest.md`
- `docs/08_阶段4真实SaaS接入.md`
- `docs/evidence/36_stage45_v211_complete_offline_verification.md`

- [x] 注册新增业务 marker。
- [x] 更新 collection 守护为真实业务 12 条、Smoke 6、Core 6。
- [x] YAML loader 覆盖全部 12 个真实测试模块。
- [x] 更新 README/计划书/Stage 4 文档到完整 Stage 4.5。
- [x] 运行 framework、默认离线全量、Smoke/Core collect、compileall 和静态凭据扫描。
- [x] 清理缓存/报告临时产物，打最终 ZIP，并从最终 ZIP 全新解压重复验证。
