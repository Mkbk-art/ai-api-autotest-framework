# Stage 3 Architecture Refactor Design

## Goal

将已经通过 Stage 2 验证的接口自动化框架，从开源基线遗留的 `base/ + common/ + testcase/` 过渡结构，迁移为职责清晰的 `core/ + utils/ + testcases/` 正式结构，同时保持已有运行行为不变，并补全代码说明与开源归属文档。

## Architecture

- `core/`：测试框架主执行链。包含配置、用例加载、HTTP 客户端、API 用例编排、变量上下文、响应提取和断言引擎。
- `utils/`：被核心模块复用的辅助能力。包含 DebugTalk、日志、脱敏、JsonPath、项目路径和 Allure 兼容层。
- `testcases/demo/`：受控 Mock 服务的演示业务用例，仅用于证明框架能力，不冒充真实短链接业务。
- `tests/`：继续验证框架自身行为，并新增 Stage 3 结构与文档规范测试。

## Migration Mapping

| Stage 2 | Stage 3 |
|---|---|
| `base/apiutil.py` | `core/api_runner.py` |
| `base/debugtalk.py` | `utils/debugtalk.py` |
| `common/config_manager.py` | `core/config_manager.py` |
| `common/request_client.py` | `core/request_client.py` |
| `common/variable_context.py` | `core/variable_context.py` |
| `common/extractor.py` | `core/extractor.py` |
| `common/assertion.py` | `core/assertion_engine.py` |
| `common/yaml_loader.py` | `core/case_loader.py` |
| `common/logger.py` | `utils/logger.py` |
| `common/sanitizer.py` | `utils/sanitizer.py` |
| `common/jsonpath_util.py` | `utils/jsonpath_util.py` |
| `common/project_paths.py` | `utils/project_paths.py` |
| `common/allure_compat.py` | `utils/allure_compat.py` |
| `testcase/` | `testcases/` |

## Compatibility and Behavior Rules

1. Stage 2 已验证行为保持不变：Mock、VariableContext、断言、异常处理、marker 分层、JUnit/Allure Results 均继续可用。
2. `run.py` 默认测试目录改为 `testcases`，命令行接口保持不变。
3. `smoke/core/regression` 的语义和现有 6 条 Demo 用例数量保持不变。
4. 不在本阶段新增 MySQL、Redis、AI、真实短链接接口或重试策略，避免把目录迁移和新功能混在一个变更里。
5. `base/`、`common/`、`testcase/` 在完成迁移后从正式源码树移除，不保留双路径兼容层，避免以后继续产生两套入口。

## Documentation Standard

1. 每个 Python 模块顶部必须有模块级 docstring，说明模块用途和边界。
2. 正式框架代码中的公共类、公共函数和 Pytest fixture 必须有 docstring；复杂私有函数也应说明关键目的。
3. 行内注释解释“为什么这样设计”，不重复代码字面含义。
4. 中文注释用于学习和面试理解；标识符继续采用英文命名。
5. 测试模块必须有模块用途说明；测试函数名本身应清楚表达行为，不强制为每条简单测试重复长注释。

## Open-source Attribution

- 保留 MIT `LICENSE`。
- 保留 `BASELINE_SOURCE.md`。
- 新增 `THIRD_PARTY_NOTICES.md`，明确上游来源、许可证，以及本项目已完成的重构/新增边界。
- README 将“基线能力”和“当前已验证能力”分开说明。

## Verification

完成后必须满足：

- Stage 3 结构测试通过；
- 所有正式 Python 模块具备模块说明；
- 所有框架公共类/函数具备 docstring；
- 全量测试不少于 Stage 2 的 56 条且全部通过；
- `smoke/core/regression` 均可独立执行；
- `collect-only` 收集 6 条 Demo 业务用例；
- `compileall`、`git diff --check` 通过；
- 从最终 ZIP 解压到全新目录后再次执行全量测试和编译检查；
- 项目计划书同步为 Stage 3 实际状态，不保留与代码矛盾的旧进度。
