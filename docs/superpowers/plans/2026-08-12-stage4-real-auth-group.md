# Stage 4 Real Short-Link Auth + Group Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不破坏 Stage 3 Mock 回归的前提下，让框架具备连接真实短链接 SaaS Gateway、使用测试账号登录、提取 token，并携带 `username + token` 查询当前用户分组和提取 `gid` 的能力。

**Architecture:** 保留 `env.test.yaml -> Mock` 作为框架回归环境，新增 `env.shortlink-local.yaml -> http://127.0.0.1:8000` 作为真实本地 SaaS 环境。通过 Pytest collection hook 在不同环境中隔离 `testcases/demo/` 与 `testcases/shortlink/`；真实凭据只从 OS 环境变量读取，不进入 YAML、日志、Git 或计划书。真实业务用例继续使用 `ApiRunner + YAML + VariableContext`，登录前置 fixture 只用于需要鉴权的后续业务接口。

**Tech Stack:** Python 3.11 target, Pytest, Requests, PyYAML, Allure compatibility layer, existing VariableContext/AssertionEngine.

## Global Constraints

- Stage 3 已验证的 Mock 行为必须保持；默认 `python -m pytest -q` 不访问真实 SaaS。
- 所有新增 Python 模块顶部写明模块作用；fixture、公共函数和关键逻辑必须有中文 docstring/解释性注释。
- 测试账号密码不得写入仓库；使用 `SHORTLINK_TEST_USERNAME`、`SHORTLINK_TEST_PASSWORD` 环境变量。
- Gateway 真实入口使用 `http://127.0.0.1:8000`；真实环境 `use_mock: false`。
- 登录契约：`POST /api/short-link/admin/v1/user/login`，请求 JSON 为 username/password，成功 `code == "0"`，token 位于 `$.data.token`。
- 分组契约：`GET /api/short-link/admin/v1/group`，Gateway 鉴权 Header 为 `username`、`token`，成功响应 `code == "0"`，第一分组 gid 位于 `$.data[0].gid`。
- 当前批次只实现 Auth + Group；创建、跳转、统计和清理在后续 Stage 4 小版本继续。
- 计划书必须与代码状态同步，未在用户 Windows + Python 3.11 环境实际访问 SaaS 前标记为“已编码待本地验证”，不得写成“真实接入已验证”。

---

### Task 1: Real Environment Selection and Collection Isolation

**Files:**
- Create: `config/env.shortlink-local.yaml`
- Modify: `testcases/conftest.py`
- Modify: `pytest.ini`
- Modify: `tests/integration/test_collection_count.py`
- Test: `tests/unit/test_config_and_runner.py`

**Interfaces:**
- Consumes: `API_TEST_ENV` set by `run.py`.
- Produces: test environment collects Demo only; shortlink-local collects ShortLink real cases only.

- [ ] **Step 1:** Add failing tests proving `env.shortlink-local.yaml` resolves Gateway host with Mock disabled and collection isolates demo/real directories.
- [ ] **Step 2:** Run targeted tests and confirm failure because environment file/hook/real directory do not exist yet.
- [ ] **Step 3:** Add named environment, collection hook, and marker declarations.
- [ ] **Step 4:** Re-run targeted tests and confirm green.
- [ ] **Step 5:** Commit environment isolation changes.

### Task 2: Secure Environment-Variable DSL

**Files:**
- Modify: `utils/debugtalk.py`
- Create: `tests/unit/test_debugtalk.py`
- Modify: `.env.example`

**Interfaces:**
- Produces: `DebugTalk.env(name)` returns required OS environment value or raises a clear error.
- YAML usage: `${env(SHORTLINK_TEST_USERNAME)}` and `${env(SHORTLINK_TEST_PASSWORD)}`.

- [ ] **Step 1:** Add tests for present and missing environment variables.
- [ ] **Step 2:** Run tests and confirm missing method failure.
- [ ] **Step 3:** Implement `DebugTalk.env` without logging the retrieved value.
- [ ] **Step 4:** Re-run tests and confirm green.
- [ ] **Step 5:** Update `.env.example` so it accurately states that OS environment variables are read directly.

### Task 3: Real Login YAML Test

**Files:**
- Create: `testcases/shortlink/__init__.py`
- Create: `testcases/shortlink/test_auth.py`
- Create: `testcases/yaml/shortlink/auth.yaml`
- Modify: `tests/unit/test_yaml_loader.py`

**Interfaces:**
- Consumes: real Gateway host from runtime config and credentials via `DebugTalk.env`.
- Produces: successful login assertion and `token` stored in current VariableContext scenario scope.

- [ ] **Step 1:** Add structure/YAML loader tests for the new real login case.
- [ ] **Step 2:** Confirm targeted test fails before files exist.
- [ ] **Step 3:** Add commented real login test/YAML using status code + business code + token existence assertions.
- [ ] **Step 4:** Verify default test environment ignores real case while shortlink-local collect-only sees it.
- [ ] **Step 5:** Commit login test changes.

### Task 4: Authenticated Group Query and gid Extraction

**Files:**
- Create: `testcases/shortlink/conftest.py`
- Create: `testcases/shortlink/test_group.py`
- Create: `testcases/yaml/shortlink/group.yaml`
- Create: `tests/unit/test_shortlink_fixtures.py`

**Interfaces:**
- Produces fixture `shortlink_authenticated_context` storing `username` and `token` in VariableContext scenario scope.
- Group YAML consumes `${username}` / `${token}` and extracts `gid` from `$.data[0].gid`.

- [ ] **Step 1:** Add fixture unit tests with an injected fake response/client, ensuring credentials become headers/context without real network access.
- [ ] **Step 2:** Confirm tests fail because fixture/helper is absent.
- [ ] **Step 3:** Implement credential/auth fixture and group test/YAML with module/function documentation.
- [ ] **Step 4:** Verify default suite stays offline and shortlink-local collect-only sees Auth + Group tests.
- [ ] **Step 5:** Commit group chain changes.

### Task 5: Documentation, Plan Sync, and Delivery Verification

**Files:**
- Modify: `README.md`
- Create: `docs/08_阶段4真实SaaS接入.md`
- Modify: `docs/00_项目计划书_Latest.md`
- Modify external canonical plan copy: `/mnt/data/AI_API_Autotest_Framework_Project_Plan_Latest.md`

**Interfaces:**
- Documents exact Git Bash commands and status boundary: sandbox verifies implementation/offline regression; user Windows run verifies real SaaS connectivity.

- [ ] **Step 1:** Run full offline tests, collect-only, marker regressions, compileall, and documentation checks.
- [ ] **Step 2:** Update README and Stage 4 design/verification document with real endpoint contracts and safe credential setup.
- [ ] **Step 3:** Update plan to next version and record Auth + Group as coded/pending local real-environment verification.
- [ ] **Step 4:** Verify plan copies are byte-identical and no real password/token appears in tracked files.
- [ ] **Step 5:** Create Stage 4 ZIP and re-run offline suite from a fresh extraction.
