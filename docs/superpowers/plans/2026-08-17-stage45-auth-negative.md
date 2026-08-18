# Stage 4.5 Authentication Negative Cases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不破坏现有 6 条真实 Smoke 的前提下，新增“错误密码登录”和“Group 缺 token”两条 YAML 驱动真实异常用例，并固化 Stage 4 的 6 passed 证据。

**Architecture:** 两条异常用例继续走 `YAML -> ApiRunner -> RequestClient -> Assertions`。错误密码使用 `DebugTalk.invalid_password()` 生成与真实凭据无关的动态值；缺 token Group 用例不依赖登录 fixture，直接验证 Gateway 401。异常用例标记为 `core`，保持 smoke 集合不变。

**Tech Stack:** Python 3.11、Pytest 9、Requests、PyYAML、现有 ApiRunner/VariableContext/Assertions、真实 Spring Cloud Gateway/Admin 短链接 SaaS。

## Global Constraints

- 不把真实用户名密码、token、数据库密钥写入仓库或验证证据。
- 新增/修改 Python 与 YAML 必须保持高密度中文注释。
- 所有真实业务网络入口优先使用 YAML -> ApiRunner 主链。
- 不改变现有 6 条 Smoke 的业务语义和数量。
- 真实环境状态只根据用户本机实际运行结果更新，不用离线 Mock 冒充。
- 不修改 Java 被测系统，本批次仅扩展 Python 自动化测试项目。

---

### Task 1: 错误密码安全数据生成

**Files:**
- Modify: `utils/debugtalk.py`
- Test: `tests/unit/test_debugtalk.py`

**Interfaces:**
- Consumes: `DebugTalk.random_string()` 所使用的 Python 随机能力。
- Produces: `DebugTalk.invalid_password() -> str`，不读取任何真实密码环境变量。

- [x] **Step 1: 写失败测试**

验证生成值非空、带自动化测试前缀，且即使设置 `SHORTLINK_TEST_PASSWORD` 也不包含该真实值。

- [x] **Step 2: 运行定向测试确认 RED**

Run: `pytest tests/unit/test_debugtalk.py -q`

Expected: FAIL，因为 `DebugTalk` 尚无 `invalid_password`。

- [x] **Step 3: 最小实现**

新增 `invalid_password()`，返回 `__api_autotest_invalid__` + 24 位随机字母数字，不读取环境变量。

- [x] **Step 4: 运行测试确认 GREEN**

Run: `pytest tests/unit/test_debugtalk.py -q`

Expected: PASS。

### Task 2: 错误密码登录 YAML 主链

**Files:**
- Create: `testcases/yaml/shortlink/auth_invalid.yaml`
- Create: `testcases/shortlink/test_auth_invalid.py`
- Modify: `pytest.ini`
- Test: `tests/unit/test_shortlink_support.py`

**Interfaces:**
- Consumes: `${env(SHORTLINK_TEST_USERNAME)}`、`${invalid_password()}`、ApiRunner `ne` / `not_exists` 断言。
- Produces: `test_shortlink_login_rejects_invalid_password`，marker=`real, shortlink, core, auth, negative`。

- [x] **Step 1: 写失败契约测试**

离线测试加载 YAML 并断言 method/path、动态错误密码、HTTP 200、业务 code 非 0、token 不存在。

- [x] **Step 2: 运行确认 RED**

Run: `pytest tests/unit/test_shortlink_support.py -q`

Expected: FAIL，因为 YAML/测试模块尚不存在。

- [x] **Step 3: 创建 YAML 和真实测试模块**

测试函数只调用 `request_base.run(base_info, test_case)`，不登录、不提取 token、不读取真实密码。

- [x] **Step 4: 定向回归确认 GREEN**

Run: `pytest tests/unit/test_shortlink_support.py tests/unit/test_stage4_comment_quality.py -q`

Expected: PASS。

### Task 3: Group 缺 token Gateway 401 主链

**Files:**
- Create: `testcases/yaml/shortlink/group_unauthorized.yaml`
- Create: `testcases/shortlink/test_group_unauthorized.py`
- Modify: `pytest.ini`
- Test: `tests/unit/test_shortlink_support.py`

**Interfaces:**
- Consumes: `${env(SHORTLINK_TEST_USERNAME)}`，不消费 token/登录 fixture。
- Produces: `test_shortlink_group_rejects_missing_token`，marker=`real, shortlink, core, group, unauthorized, negative`。

- [x] **Step 1: 写失败契约测试**

验证 YAML Header 只有 username、没有 token，断言 401/status/message。

- [x] **Step 2: 运行确认 RED**

Run: `pytest tests/unit/test_shortlink_support.py -q`

Expected: FAIL，因为 Group unauthorized YAML 尚不存在。

- [x] **Step 3: 创建 YAML 和真实测试模块**

不注入 `shortlink_authenticated_context`，确保请求在 Gateway 层直接失败。

- [x] **Step 4: 定向回归确认 GREEN**

Run: `pytest tests/unit/test_shortlink_support.py tests/unit/test_stage4_comment_quality.py -q`

Expected: PASS。

### Task 4: Stage 4 真实证据与文档状态固化

**Files:**
- Create: `docs/evidence/34_stage4_real_smoke_6_passed.md`
- Modify: `README.md`
- Modify: `docs/00_项目计划书_Latest.md`
- Modify: `docs/08_阶段4真实SaaS接入.md`

**Interfaces:**
- Consumes: 用户 2026-08-14 本机 `6 passed in 9.65s` 日志。
- Produces: V2.10 状态：Stage 4 完成；Stage 4.5 第一批异常用例已编码待真实验收。

- [x] **Step 1: 写入真实 6 passed 证据**

只记录非敏感的命令、6 条用例名称、Redirect 302、Stats 两次轮询和最终结果；不复制账号密码/token。

- [x] **Step 2: 更新 README/计划书/Stage4 文档**

把旧的“4 passed/待 6 smoke”状态统一替换成“6 条真实 Smoke 已通过”。

- [x] **Step 3: 搜索旧状态**

Run: `grep -R "4 passed\|待用户本机 6 条\|Redirect / Statistics / Cleanup.*待" README.md docs/00_项目计划书_Latest.md docs/08_阶段4真实SaaS接入.md`

Expected: 不再出现把当前阶段误标为“待 6 条验收”的活动状态文字；历史版本说明可保留并明确为历史。

### Task 5: 全量验证、证据与打包

**Files:**
- Create: `docs/evidence/35_stage45_v210_offline_verification.md`
- Create: `/mnt/data/ai-api-autotest-framework-stage45-auth-negative-v210.zip`
- Create: `/mnt/data/stage45_auth_negative_v210_sha256.txt`
- Create: `/mnt/data/AI_API_Autotest_Framework_Project_Plan_Latest.md`

**Interfaces:**
- Consumes: Tasks 1-4 全部产物。
- Produces: 可供用户 Windows 真实验收的 V2.10 ZIP。

- [x] **Step 1: framework tests**

Run: `pytest tests -q`

Expected: 0 failed。

- [x] **Step 2: 默认离线全量**

Run: `pytest -q`

Expected: 0 failed，真实 shortlink 用例按 test 环境 collection 隔离。

- [x] **Step 3: Smoke/Core collection**

Run: `python run.py --env shortlink-local --level smoke --collect-only`
Expected: 原 6 条 Smoke。

Run: `python run.py --env shortlink-local --level core --collect-only`
Expected: 本批次 2 条异常 Core。

- [x] **Step 4: compileall 与敏感字面值扫描**

Run: `python -m compileall -q core utils testcases tests run.py`
Expected: exit 0。

扫描业务文件不得出现真实密码/token 值；仅允许环境变量名和脱敏占位符。

- [x] **Step 5: 打包并全新解压复验**

新 ZIP 解压到独立目录，重复 framework/full/collect/compileall 核验后计算 SHA256。
