# Stage 3 Architecture Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 将 Stage 2 稳定版本迁移为 `core/ + utils/ + testcases/` 正式架构，并补齐代码说明、开源归属和实时项目计划书。

**Architecture:** 框架主执行链集中到 `core/`，辅助函数集中到 `utils/`，Mock 演示用例集中到 `testcases/demo/`。迁移只改变组织方式和可读性，不改变 Stage 2 已验证行为。

**Tech Stack:** Python 3.11+、Pytest、Requests、PyYAML、Allure、Git。

## Global Constraints

- 不新增 MySQL/Redis/AI/真实短链功能。
- 不保留 `base/`、`common/`、`testcase/` 双路径兼容层。
- 所有正式 Python 模块必须有模块级中文说明。
- 框架公共类、公共函数和 fixture 必须有 docstring。
- 全量回归不能少于 Stage 2 已验证的 56 条测试。
- 计划书必须与最终代码状态同步。

---

### Task 1: 建立 Stage 3 结构与文档规范回归测试

**Files:**
- Create: `tests/unit/test_stage3_structure.py`

**Interfaces:**
- Consumes: 项目根目录。
- Produces: 对目标目录、旧目录移除、模块 docstring 和公共 API docstring 的自动化约束。

- [x] 编写结构测试，要求 `core/`、`utils/`、`testcases/` 存在且旧目录不存在。
- [x] 编写 AST 文档测试，检查正式 Python 模块的模块 docstring 与公共 API docstring。
- [x] 运行该测试并确认在 Stage 2 结构上失败。

### Task 2: 迁移框架核心与辅助模块

**Files:**
- Create/Move: `core/*.py`, `utils/*.py`
- Modify: `run.py`, `mock_server/server.py`, `tests/**/*.py`
- Remove: `base/`, `common/`

**Interfaces:**
- Produces: `ApiRunner`（由 `RequestBase` 重命名）、`Assertions`、`VariableContext`、`RequestClient`、`ConfigManager` 等稳定接口。

- [x] 按设计映射移动模块并更新 import。
- [x] 将 `RequestBase` 重命名为 `ApiRunner`，fixture 名 `request_base` 暂保留以减少业务测试噪音。
- [x] 更新 `run.py` 默认测试路径和项目路径引用。
- [x] 运行结构测试和全量测试。

### Task 3: 迁移 Demo 业务用例并统一代码说明

**Files:**
- Move: `testcase/` -> `testcases/`
- Modify: 所有正式 Python 模块、fixture、Mock Server、Demo 测试模块。

**Interfaces:**
- Produces: `testcases/demo` + `testcases/yaml` 清晰 Demo 边界。

- [x] 更新 Pytest testpaths、YAML 路径工具与测试收集校验。
- [x] 为每个 Python 模块补模块用途 docstring。
- [x] 为公共类、公共函数和 fixture 补 docstring；关键逻辑补解释性行内注释。
- [x] 运行全量测试和三个 marker 分层。

### Task 4: 增加正式项目元数据与开源归属

**Files:**
- Create: `THIRD_PARTY_NOTICES.md`, `.env.example`, `pyproject.toml`, `requirements-dev.txt`, `constraints.txt`
- Modify: `README.md`, `BASELINE_SOURCE.md`, `.gitignore`

**Interfaces:**
- Produces: 可公开仓库的基础工程说明与依赖边界。

- [x] 写明上游基线、MIT License 和个人重构边界。
- [x] README 更新正式目录、执行链、已验证能力和未实现能力。
- [x] 增加开发依赖和当前可复现版本约束，不夸大未验证功能。

### Task 5: 实时更新计划书与最终交付验证

**Files:**
- Modify: `docs/00_项目计划书_Latest.md`
- Generate: `/mnt/data/AI_API_Autotest_Framework_Project_Plan_Latest.md`
- Generate: `/mnt/data/ai-api-autotest-framework-stage3.zip`

**Interfaces:**
- Produces: V2.3 最新计划书和 Stage 3 ZIP。

- [x] 修正 Stage 1、Stage 2 的实际完成状态与证据，不保留旧的“待修 P0”行动清单。
- [x] 将 Stage 3 按实际验证结果更新为完成状态，并将 Stage 4 设为下一步。
- [x] 执行全量 Pytest、coverage、collect-only、三个 marker、compileall、diff check。
- [x] `git archive` 生成 ZIP，并从新目录解压后二次执行全量测试和 compileall。
