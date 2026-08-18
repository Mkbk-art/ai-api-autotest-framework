# Stage 4 Redirect / Statistics / Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or equivalent task-by-task execution. Steps use checkbox syntax for tracking.

**Goal:** 在已真实通过的 Auth/Group/Create/Page 链路上增加 hosts 域名 Redirect、Redis Stream 统计轮询、业务回收站清理和 Stage 4 注释质量守护。

**Architecture:** 真实业务前置继续放在 `testcases/shortlink` fixture/helper，保持 function-scope 隔离。Redirect 直接使用用户 hosts 已映射的 `nurl.ink:8001`；Stats 走 Gateway/Admin 有界轮询；测试资源通过 yield Teardown 或 Create finally 调用真实 RecycleBin API 清理。

**Tech Stack:** Python 3.11+, Pytest, Requests, YAML, VariableContext, Java short-link SaaS.

## Global Constraints

- 仓库中不保存真实用户名密码值、Token、数据库或 Redis 密钥。
- 创建原始链接固定为 `https://github.com/`。
- Redirect 使用 `http://nurl.ink:8001/<short_uri>` + `allow_redirects=False`。
- Stats 真实测试轮询间隔 1 秒、最大 15 秒。
- Cleanup 必须走 `recycle-bin/save -> recycle-bin/remove`，不直接 SQL 删除。
- 测试之间不依赖执行顺序。
- Stage 4 Python/YAML 保持高密度中文解释，并有自动化守护。

---

### Task 1: Redirect hosts 契约

**Files:**
- Modify: `testcases/shortlink/support.py`
- Modify: `testcases/shortlink/test_redirect.py`
- Modify: `testcases/yaml/shortlink/redirect.yaml`
- Modify: `tests/unit/test_shortlink_support.py`

- [x] 先写失败测试，要求 Redirect URL 为 `http://nurl.ink:8001/<short_uri>` 且没有手工 Host Header。
- [x] 确认旧实现测试失败。
- [x] 修改 helper 直接使用 hosts 域名并保留 `allow_redirects=False`。
- [x] 更新 YAML/测试模块说明。
- [x] 聚焦单元测试通过。

### Task 2: RecycleBin Cleanup

**Files:**
- Modify: `testcases/shortlink/support.py`
- Modify: `testcases/shortlink/conftest.py`
- Modify: `testcases/shortlink/test_create.py`
- Modify: `tests/unit/test_shortlink_support.py`

- [x] 先写失败测试要求 save -> remove 两次调用及真实鉴权 Header/DTO。
- [x] 确认 helper 缺失导致测试失败。
- [x] 实现 `cleanup_shortlink()`。
- [x] `shortlink_created_context` 改为 yield fixture，Teardown 自动清理。
- [x] Create 测试使用 `try/finally` 清理自身创建数据。
- [x] 聚焦单元测试通过。

### Task 3: Statistics bounded polling

**Files:**
- Modify: `testcases/shortlink/support.py`
- Modify: `testcases/shortlink/test_statistics.py`
- Modify: `testcases/yaml/shortlink/statistics.yaml`
- Modify: `tests/unit/test_shortlink_support.py`

- [x] 保留即时成功、延迟成功、超时三类离线测试。
- [x] Stats 固定携带 `enableStatus=0`。
- [x] 真实测试先触发 Redirect，再进入 1s/15s 有界轮询。
- [x] PV/UV/UIP 均至少为 1 才判定访问统计可见。

### Task 4: GitHub Create 与凭据安全

**Files:**
- Modify: `testcases/yaml/shortlink/create.yaml`
- Modify: `testcases/shortlink/conftest.py`
- Modify: `testcases/shortlink/support.py`
- Modify: `tests/unit/test_shortlink_support.py`

- [x] Create YAML 和 fixture 均固定 `https://github.com/`。
- [x] `ShortlinkCredentials.password` 使用 `repr=False`。
- [x] `authenticate_shortlink()` 不暴露独立 password 形参。

### Task 5: Stage 4 注释规范

**Files:**
- Modify: `testcases/shortlink/*.py`
- Modify: `testcases/yaml/shortlink/*.yaml`
- Create: `tests/unit/test_stage4_comment_quality.py`

- [x] 所有 Stage 4 业务 Python 补充模块说明、fixture/helper/test docstring 和关键逻辑中文注释。
- [x] 所有真实 YAML 对字段来源、业务语义和断言原因补充中文注释。
- [x] 新增模块 docstring + 最低注释密度自动化守护。

### Task 6: Documentation and packaging verification

**Files:**
- Modify: `README.md`
- Modify: `docs/08_阶段4真实SaaS接入.md`
- Modify: `docs/00_项目计划书_Latest.md`
- Modify: `docs/superpowers/specs/2026-08-13-stage4-redirect-stats-design.md`

- [x] 文档解释 TCP 相同但 HTTP Host/serverName 不同的原因。
- [x] 计划书记录用户真实 `4 passed`，不提前声称 Redirect/Stats/Cleanup 已真实通过。
- [x] 完成最终 `tests`、全量、collect-only、Mock markers、compileall、secret scan。
- [x] 生成 UTF-8 ZIP，并从 ZIP 全新解压目录复验。
