# Declarative Case Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让普通 YAML API Case 由框架统一 Pytest Runtime 直接执行，并将项目 Python 限制为 Context Provider 和复杂 Workflow。

**Architecture:** 新增 CaseSpec、CaseRegistry、ContextProviderRegistry 和 CaseExecutor；现有 ApiRunner 继续作为 HTTP/Extract/Assertion 执行核心。根 Pytest glue 根据环境选择项目、扫描 declarative Case 并参数化一个框架级 generic test；复杂 workflow 从 registry 按 case_id 复用相同 YAML Case。

**Tech Stack:** Python 3.11+、Pytest、PyYAML、Requests、Allure、现有 VariableContext/AssertionEngine。

**Spec:** `docs/superpowers/specs/2026-08-20-declarative-case-runtime-design.md`

## Global Constraints

- 不修改 AI Provider 配置优先级和 Provider/Protocol 边界。
- 不将 Shortlink 业务词写入 `core/`。
- 不将复杂控制流塞进 YAML。
- 公开交付包不得包含 `config/ai.local.yaml`、`.env`、真实 Secret、logs/reports 运行产物。
- 保留 Pytest exit code、Allure、smoke/core/regression 分层语义。

---

### Task 1: CaseSpec V2 与 Registry

**Files:**
- Create: `core/case_spec.py`
- Create: `core/case_registry.py`
- Test: `tests/unit/test_case_spec_v2.py`

**Interfaces:**
- Produces: `CaseSpec`, `load_case_specs(path)`, `CaseRegistry.from_paths(paths)`, `registry.get(case_id)`。

- [x] 写 CaseSpec/Registry RED tests：合法 V2、重复 ID、字段错误、workflow 不自动收集。
- [x] 运行目标测试确认因模块不存在失败。
- [x] 最小实现 CaseSpec/Registry。
- [x] 运行目标测试变绿。

### Task 2: Context Provider 与 CaseExecutor

**Files:**
- Create: `core/context_provider.py`
- Create: `core/case_executor.py`
- Test: `tests/unit/test_case_executor.py`

**Interfaces:**
- Produces: `ContextProviderRegistry.register(name, provider)`；`CaseExecutor.execute(case_id|CaseSpec, overrides=None)`。

- [x] 写 Provider 生命周期、循环依赖、CaseExecutor 调用 ApiRunner 的 RED tests。
- [x] 运行确认失败。
- [x] 最小实现。
- [x] 运行确认变绿。

### Task 3: Framework-owned Generic Pytest Runtime

**Files:**
- Create: `testcases/test_yaml_cases.py`
- Modify: `conftest.py`
- Test: `tests/integration/test_declarative_collection.py`

**Interfaces:**
- `yaml_case` fixture/param 由 collection hook 提供。
- Generic function 只调用 `case_executor.execute(yaml_case)`。

- [x] 写 Demo 无业务 wrapper 仍能收集 6 Case 的 RED integration test。
- [x] 运行确认失败。
- [x] 实现动态 Case 参数化、marker 注册和项目选择。
- [x] 运行确认变绿。

### Task 4: Demo 迁移

**Files:**
- Migrate: `testcases/yaml/*.yaml` -> V2
- Create: `testcases/demo/context.py`
- Remove: `testcases/demo/test_login.py`
- Remove: `testcases/demo/test_publish_api.py`
- Remove: `testcases/demo/test_call_api.py`
- Remove: `testcases/demo/conftest.py`
- Test: existing collection/marker tests + new declarative tests

- [x] 先修改测试，要求 Demo 目录无 `test_*.py` 且仍收集 smoke/core/regression 各 2 条。
- [x] 确认 RED。
- [x] 迁移 Demo YAML 与 context providers。
- [x] GREEN。

### Task 5: Shortlink 普通 Case 迁移

**Files:**
- Migrate: `testcases/shortlink/yaml/*.yaml` -> V2
- Create: `testcases/shortlink/context.py`
- Modify: `testcases/shortlink/support.py`
- Test: `tests/unit/test_shortlink_support.py`, collection tests

- [x] 先写 RED tests：普通 Case 不依赖业务 test wrapper；case_id 稳定且 18 条不丢失。
- [x] 迁移普通 Case requires/context/cleanup 语义。
- [x] GREEN。

### Task 6: Shortlink 复杂 Workflow 迁移

**Files:**
- Create: `testcases/shortlink/workflows/test_storage_lifecycle.py`
- Remove: `testcases/shortlink/test_auth.py`
- Remove: `testcases/shortlink/test_link.py`
- Remove: `testcases/shortlink/test_redirect.py`
- Remove: `testcases/shortlink/test_statistics.py`
- Remove: `testcases/shortlink/conftest.py`

- [x] 写 RED architecture test，要求 shortlink 顶层无普通 `test_*.py` wrapper。
- [x] Workflow 改为通过 CaseExecutor + case_id 复用 YAML。
- [x] 保持 smoke/core/regression 各 6 条。
- [x] GREEN。

### Task 7: 文档、安全与全量回归

**Files:**
- Modify: `README.md`
- Modify: `docs/04_执行流程.md`
- Create: `docs/12_声明式Case与Workflow边界.md`
- Modify: `AI_API_Autotest_Framework_Project_Plan_Latest.md`
- Test: repository hygiene / architecture guards

- [x] 更新文档和架构守门测试。
- [x] `python -m pytest tests -q` 全绿。
- [x] Mock smoke/core/regression 验证。
- [x] Shortlink `--collect-only` 验证 18 条分层不变。
- [x] `python -m compileall core testcases tests` 通过。
- [x] 打包前 Secret/Artifact 扫描。
