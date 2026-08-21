# AI 辅助接口自动化测试框架项目计划书

> **版本**：V4.5（Stage 6.5.1 Failure Evidence Ordering & Allure Diagnostics）
> **更新日期**：2026-08-21
> **当前阶段**：Stage 6.5.1 — Failure Evidence Ordering & Allure Diagnostics（真实 Jenkins FULL 暴露“次生缺变量覆盖原始业务失败”的通用诊断问题）
> **项目定位**：Contract-driven, Change-aware, AI-assisted API Test Automation Framework
> **维护规则**：每完成一个阶段或发生架构级决策，必须同步更新本计划书中“当前阶段”“该阶段问题与解决”“完成状态”和“总进度表”。不再在文档顶部持续堆叠长版本日志。

---

# 1. 项目定位

## 1.1 项目目标

构建一个面向测试开发岗位、可以重复接入不同 API 项目的自动化测试框架。

框架最终解决的不是“怎么发 HTTP 请求”这一个问题，而是形成完整闭环：

```text
API Contract
↓
Structured Test Assets
↓
Deterministic Test Runtime
↓
Coverage Intelligence
↓
Contract Change
↓
Change-aware Regression
↓
AI Risk-based Test Design
↓
Evidence-based Failure Triage
↓
Allure / CI Evidence
```

## 1.2 核心边界

```text
Framework Core ≠ Shortlink
Framework Core ≠ Java/Spring Parser
Framework Core ≠ AI Agent that decides PASS/FAIL
```

Shortlink 只是第一真实 SUT，用于验证框架在真实复杂系统上的可用性。

## 1.3 四问功能准入原则

任何新增能力必须回答：

1. 没有 AI，它是否仍有明确工程价值？
2. Pytest/现有工具是否已经很好解决？如果是，为什么还要重做？
3. 第二个完全不同的 SUT 能否不修改 Framework Core 直接复用？
4. 面试时是否能用真实代码、测试或 CI 证据证明？

答不上来，就不进入主框架。

## 1.4 计划执行原则

计划书记录的是“当前最优设计”，不是不可修改的固定施工图。

每进入一个 Stage / 子任务实现前，必须重新检查：

1. 当前问题是否仍真实存在；
2. 原设计是否仍是最简单、通用、可验证的方案；
3. 是否为了某个测试、当前 SUT 或历史计划引入了不必要依赖；
4. 是否出现更好的实现边界；
5. 若真实实施暴露新问题，应先修正设计和计划书，再继续开发。

不得为了“严格按计划完成”而保留已经证明不合理的实现。

---

# 2. 当前总体架构

```text
                 被测项目 A
                     │
       config/env.<project>.yaml
                     │
      testcases/<project>/yaml
      context.py / workflows/
      contract/
                     │
                     ▼
        ┌────────────────────────┐
        │  API Autotest Framework│
        └────────────────────────┘
            │        │        │
            │        │        │
     Test Runtime  Contract   AI
            │        │        │
      Pytest/YAML  Coverage  Design/Triage
            │        │        │
            └────────┼────────┘
                     │
               Allure + CI/CD
```

## 2.1 普通 Case

```text
YAML Test Specification V2
→ CaseRegistry
→ Generic Pytest Runtime
→ CaseExecutor
→ ApiRunner
→ AssertionEngine
→ Allure
```

## 2.2 复杂 Workflow

只有真正需要 branch / loop / multi-state / finally cleanup / compensation 的流程使用 Python。

YAML 不演化为第二门编程语言。

---

# 3. 阶段状态总览

| Stage | 名称 | 当前状态 |
|---|---|---|
| Stage 0 | 项目定位与工程基线 | ✅ 已完成 |
| Stage 1 | 通用 API 执行引擎 | ✅ 已完成 |
| Stage 2 | 数据源与深层一致性 | ✅ 已完成 |
| Stage 3 | 真实 SUT 与 CI/CD 工程验证 | ✅ 已完成 |
| Stage 4 | Declarative Case Runtime | ✅ 已完成 |
| Stage 5 | Contract & Coverage Intelligence | ✅ 已完成并通过用户 Windows 本机复验 |
| Stage 6 | Change-aware Smart Regression | 🟡 真实变更/反向变更/Baseline 生命周期已验证；GitHub Actions 已绿，Jenkins 最终验收进行中 |
| Stage 6.5 | Contract-driven Case Simplification | 🟡 真实 Contract 单一 endpoint 事实源已验证；Stage 6.5.1 诊断修复完成后继续 Jenkins 最终验收 |
| Stage 7 | AI Risk-based Test Design | ⏸ 暂停，Stage 6.5 完成后重新评估 |
| Stage 8 | Failure Triage & Allure Enrichment | 🟡 已有 Evidence/AI 基础，完整阶段未完成 |
| Stage 9 | 第二 SUT 与最终复用性证明 | ⏳ 未开始 |

> Stage 8 中已有历史实现的 FailureEvidence、Sanitizer、Provider Config、严格 Fact 引用和安全降级属于可复用基础；
> 但 Fingerprint / Cluster / Allure Enrichment 尚未完成，因此不提前标记 Stage 8 完成。

---

# Stage 0：项目定位与工程基线

## 0.1 阶段目的

把教学型开源骨架转变为可以持续演进的个人测试开发项目，并明确原创边界、工程边界和验证规则。

## 0.2 当前问题 / 为什么需要该阶段

原始基线仓库具备 Pytest、Requests、YAML、Allure 等元素，但更多是教学/展示骨架：

- 部分能力只是 Demo；
- README 描述不能直接等同于真实能力；
- 缺少稳定的框架自身测试；
- 开源代码与个人贡献边界需要明确；
- 如果不先建立能力声明规则，后续容易把“计划中”误写成“已实现”。

## 0.3 设计思路

- 固定开源基线和许可证来源；
- 所有新能力以真实测试/报告/CI 证据为准；
- 明确 Framework 与 SUT 分层；
- 建立“计划中 / 已编码 / 已验证”三态；
- 不把短链接业务放入 Core。

## 0.4 使用方式

无特殊最终用户使用方式。本阶段主要是工程治理。

## 0.5 阶段亮点（与传统方式的差异）

传统求职项目容易直接 Fork 后包装成自己的项目；本项目保留源码审查、问题发现、架构演进和验证证据，
重点展示“为什么改”和“如何证明改对了”。

## 0.6 阶段产出与验收

- LICENSE / THIRD_PARTY_NOTICES；
- 基线源码审查；
- 项目边界；
- Framework Tests 基线；
- 能力状态规则。

## 0.7 阶段产生的问题与解决方式

**问题：** 原仓库的 Demo/说明容易被误当成熟能力。
**解决：** 逐项验证，只有有代码+测试/运行证据的能力才进入 README/简历。

**问题：** 开源基线与个人贡献可能混淆。
**解决：** 保留 MIT 来源和第三方说明，面试中明确“继承骨架 + 自主重构”。

## 0.8 阶段总结

建立了后续所有阶段共同遵循的工程可信度和边界。

## 0.9 当前进度

**✅ 已完成。**

---

# Stage 1：通用 API 执行引擎

## 1.1 阶段目的

建立稳定、SUT 无关的 API Test Runtime，先把“测试如何可靠执行”解决。

## 1.2 当前问题 / 为什么需要该阶段

原基线存在会导致测试不执行或结果失真的问题：

- YAML 路径处理不可靠；
- JSON 参数可能重复透传；
- Case Header 覆盖语义不完整；
- marker 之间存在隐式依赖；
- 配置优先级不稳定；
- 0 Case 可能误判成功；
- Allure/JUnit 输出边界不清晰；
- 缺少异常路径回归测试。

## 1.3 设计思路

核心职责拆分：

```text
ConfigManager
→ RequestClient
→ ApiRunner
→ VariableContext
→ Extractor
→ AssertionEngine
→ Reporting
```

使用 Mock Server 先证明框架自身行为，再接真实 SUT。

## 1.4 使用方式

统一入口：

```bash
python run.py --env <ENV_NAME> --level smoke
python run.py --env <ENV_NAME> --level core
python run.py --env <ENV_NAME> --level regression
```

## 1.5 阶段亮点（与传统方式的差异）

不是在每个 `test_xxx.py` 中重复 `requests + assert`，而是把请求、上下文、断言、配置和报告变成稳定基础设施。

## 1.6 阶段产出与验收

- RequestClient / ApiRunner；
- VariableContext；
- Extractor；
- AssertionEngine；
- ConfigManager；
- Mock Server；
- 日志和脱敏；
- JUnit / Allure Results；
- timeout / connection error / non-JSON 等框架测试。

## 1.7 阶段产生的问题与解决方式

**问题：** 测试文件之间共享运行状态导致执行顺序依赖。
**解决：** 内存 VariableContext + fixture/context，取消共享 `extract.yaml` 运行态。

**问题：** Header/Token 可能进入日志。
**解决：** Sanitizer 统一遮蔽敏感 Header。

**问题：** 网络异常容易与业务断言混为一谈。
**解决：** RequestClient 保留 Requests 原始异常语义，测试失败忠实暴露，不用“自动重试一切”掩盖真实问题。

## 1.8 阶段总结

形成了后续所有能力的稳定执行底座。

## 1.9 当前进度

**✅ 已完成。**

---

# Stage 2：数据源与深层一致性

## 2.1 阶段目的

让框架不仅验证 HTTP Response，还能验证 API 调用后的数据库、缓存和最终一致性状态。

## 2.2 当前问题 / 为什么需要该阶段

只看接口返回无法发现：

- 返回成功但 DB 未落库；
- Redis 缓存未写入/未删除；
- 异步统计尚未最终持久化；
- 分库分表后查询目标不明确。

## 2.3 设计思路

建立通用 named data source：

```text
data_sources.mysql.<source>
data_sources.redis.<source>
```

AssertionEngine 提供通用只读规则：

```text
db_exists / db_eq / db_gte
redis_exists / redis_eq
redis_hfield_exists / redis_ttl_between / redis_scard_gte
```

Polling 只在 Case 明确声明时生效。

## 2.4 使用方式

项目只在自己的环境 YAML 配置数据源；Case 在 assertions 中引用 `source`。

Framework Core 不知道业务表名和 Redis Key。

## 2.5 阶段亮点（与传统方式的差异）

传统接口自动化常停在 HTTP 200/JSON；本框架把“响应—DB—Redis—最终一致性”放进同一 Test Specification，
但数据库探针保持只读，不通过直接改业务表制造状态。

## 2.6 阶段产出与验收

- MySQLClient；
- RedisClient；
- 参数化 SQL；
- Redis RESP 协议可配置；
- polling；
- 通用 Java hash/sharding utility；
- Shortlink Regression 对真实 MySQL/Redis 完整验证。

## 2.7 阶段产生的问题与解决方式

**问题：** redis-py 新版本默认 RESP3，而真实 Redis/代理不支持 `HELLO 3`。
**解决：** Redis protocol 变成通用配置，默认 RESP2，支持项目显式切换 RESP3。

**问题：** Shortlink 使用 ShardingSphere 16 表。
**解决：** 只保留无业务表名的 Java HashMod 通用算法；业务表前缀仍留在 Shortlink 项目层。

**问题：** Redis Stream 是异步链路，不能固定 sleep 后断言。
**解决：** YAML bounded polling + 最终状态断言。

## 2.8 阶段总结

框架具备了真实业务数据一致性验证能力，同时保持 DB/Redis Core 与具体 SUT 分离。

## 2.9 当前进度

**✅ 已完成，真实 Shortlink Regression 6/6 已验证。**

---

# Stage 3：真实 SUT 与 CI/CD 工程验证

## 3.1 阶段目的

证明框架不仅能在 Mock 中工作，还能在真实复杂后端、GitHub Actions 和 Jenkins 中稳定运行。

## 3.2 当前问题 / 为什么需要该阶段

纯 Mock 无法证明：

- Gateway/鉴权真实可用；
- 302 Redirect 真实行为；
- MySQL/Redis/异步链真实接入；
- CI 环境与开发机差异；
- Windows Jenkins Service 编码和环境隔离；
- 历史报告是否污染当前 Build。

## 3.3 设计思路

三类验证环境分离：

```text
Local Real SUT
→ 验证真实业务与数据一致性

GitHub Actions
→ 公共、可重复、无私人本地服务依赖

Jenkins
→ 参数化 CI / 可接入企业或本地测试环境
```

统一使用 `run.py`，不为 CI 写另一套测试执行器。

## 3.4 使用方式

GitHub Actions：公共 Mock/Framework CI。

Jenkins：
```text
ENV_NAME=<environment>
LEVEL=smoke|core|regression
```

本地仍可直接运行，不要求使用 Git/Jenkins。

## 3.5 阶段亮点（与传统方式的差异）

同一套 Runner 同时服务本地、SCM CI 和 Jenkins；CI 只是调度者，不拥有第二套测试逻辑。

## 3.6 阶段产出与验收

- GitHub Actions 真实绿色；
- Jenkins Smoke/Core/Regression 真实 SUCCESS；
- JUnit/Artifacts；
- Allure Results/HTML；
- Windows Allure CLI 兼容；
- Workspace 独立 `.venv`；
- Build-specific report isolation。

## 3.7 阶段产生的问题与解决方式

**问题：** Jenkins Windows Service 默认编码导致 UTF-8 requirements 读取失败。
**解决：** Pipeline 内启用 UTF-8 Mode，并使用 Workspace `.venv`。

**问题：** Jenkins Workspace 历史 JUnit 污染新 Build。
**解决：** `run_id=jenkins-${BUILD_NUMBER}`，post 只消费当前 Build 报告。

**问题：** npm 安装的 Windows Allure 是 `allure.cmd`，Git Bash 能跑但 Python CreateProcess 找不到。
**解决：** Runner 解析真实 CLI 路径；Windows `.cmd/.bat` 经 COMSPEC 执行。该修复与任何 SUT 无关。

**问题：** Shortlink Create 偶发一次网络/服务超时。
**解决：** 重跑后正常，判定为环境波动；不因此提高全局 timeout、不对 POST 自动重试、不污染 Core。

## 3.8 阶段总结

证明了框架的执行链不仅“代码看起来能用”，而是在真实业务、本地 Allure、GitHub Actions 和 Jenkins 中都跑通。

## 3.9 当前进度

**✅ 已完成。**

---

# Stage 4：Declarative Case Runtime

## 4.1 阶段目的

解决“YAML 已存在，但普通业务仍要写一层 Python wrapper”的重复维护问题。

目标：

> 普通 API Case 只写 YAML；Python 只留给真正复杂 Workflow。

## 4.2 当前问题 / 为什么需要该阶段

旧模式：

```text
YAML
+
每个业务域一个 Python 参数化 wrapper
```

会产生：

- YAML 和 Python 双维护；
- 新项目仍要理解公共测试胶水；
- 前置数据被误认为必须写复杂 Python；
- 普通 Case 难以成为可分析测试资产。

## 4.3 设计思路

建立：

```text
CaseSpec V2
→ CaseRegistry
→ Generic Pytest Runtime
→ CaseExecutor
```

Context Provider 解决可复用前置数据。

Workflow 只保留真实控制流。

## 4.4 使用方式

普通 Case：

```yaml
version: 2
cases:
  - id: order.create.success
    operation_id: createOrder
    level: smoke
    risks: [state_transition]
    request: ...
    assertions: ...
```

无需新增 `test_order.py` wrapper。

复杂 Workflow 才写 Python。

## 4.5 阶段亮点（与传统方式的差异）

传统“YAML 数据驱动”往往只是把参数搬到 YAML，Python wrapper 仍然大量存在。

本框架把 YAML 提升为：

> **Executable + Analyzable Test Specification**

并明确 YAML/Python 边界。

## 4.6 阶段产出与验收

- `core/case_spec.py`
- `core/case_registry.py`
- `core/context_provider.py`
- `core/case_executor.py`
- `testcases/test_yaml_cases.py`
- 16 个 Shortlink Declarative Cases
- 2 个真实 Python Workflows
- 全量 Framework Tests 182 passed
- Shortlink Smoke/Core/Regression 全部 6/6
- GitHub Actions green
- Jenkins test Smoke/Core/Regression SUCCESS
- Allure HTML 完整链路验证

## 4.7 阶段产生的问题与解决方式

**问题：** “有前置数据”不代表“复杂 Workflow”。
**解决：** Context Provider 负责登录、临时资源等可复用前置；只有控制流才保留 Python。

**问题：** YAML 容易继续加入 if/for/while 变成编程语言。
**解决：** CaseSpec 明确拒绝控制流 key。

**问题：** Case 失败时 teardown 可能不执行。
**解决：** CaseExecutor 使用统一 Context/ExitStack 语义保证 teardown。

## 4.8 阶段总结

框架从“YAML + Pytest wrapper”升级为真正的 Declarative Runtime，为 Contract/Coverage 建立稳定测试资产主键。

## 4.9 当前进度

**✅ 已完成并完成真实平台验收。**

---

# Stage 5：Contract & Coverage Intelligence

## 5.1 阶段目的

让框架从：

> “我能执行这些测试”

升级为：

> “我知道系统有哪些 API、每条测试在覆盖哪个 API、哪些 API 还没有测试。”

这是 Stage 6 Change-aware Regression 的数据基础。

## 5.2 当前问题 / 为什么需要该阶段

当前 Case 已经有 `case_id / operation_id / risks`，但框架仍缺少“完整系统 API 清单”。

因此当前不能可靠回答：

- 项目一共有多少 API Operation？
- YAML 中写的 `operation_id` 是否真的存在？
- 哪些 Operation 没有任何 Case？
- Workflow 跨了哪些 Operation？
- API 变化后应该定位到哪些测试资产？

Shortlink 还有一个现实问题：后端没有 OpenAPI，但有完整源码。

## 5.3 设计思路

### 5.3.1 统一 Contract Model

```text
OpenAPIProvider ───────┐
                       ▼
                   ApiContract
                       ▲
StaticManifestProvider ┘
```

后续 Coverage/Diff/Regression 只依赖 `ApiContract`，不关心 Contract 来源。

### 5.3.2 Contract 获取模式

#### 模式 A：项目已有 OpenAPI 3.x

```text
OpenAPI YAML / JSON
→ OpenAPIProvider
→ ApiContract
```

客户配置示例：

```yaml
contract:
  provider: openapi
  source: path/to/openapi.yaml
```

优先使用 OpenAPI `operationId`。

#### 模式 B：没有 OpenAPI，但有后端源码

不在 Framework Core 做 Spring/FastAPI/NestJS/Gin 等源码解析器。

一次性：

```text
Backend Source
→ 人工 / AI 辅助提取接口清单
→ Review
→ Static Contract Manifest
→ StaticManifestProvider
→ ApiContract
```

客户配置：

```yaml
contract:
  provider: static_manifest
  source: testcases/<project>/contract/contract.yaml
```

Shortlink 属于此模式。

#### 模式 C：没有源码，但有接口文档 / Postman / Apifox / Wiki

将可核验接口说明整理为 Static Manifest，再使用同一 `StaticManifestProvider`。

#### 模式 D：已有框架格式 Static Manifest

直接加载，无需任何转换。

### 5.3.3 为什么不做源码解析工具

因为：

```text
Spring Parser
≠
API Test Framework Core
```

如果 Core 理解 `@RequestMapping`，第二个 FastAPI/Node/Go 项目就需要修改 Core。

源码清单提取只是 **Contract Acquisition**，Contract Loader 才是 Framework 能力。

### 5.3.4 Coverage Scope

对于微服务系统，必须区分：

- external API；
- internal service API；
- page/technical route。

否则同一业务 API 在 Gateway/Admin/Project 多层重复出现，会夸大 Coverage Gap。

### 5.3.5 Workflow 多 Operation

普通 Case 通常对应一个 `operation_id`。

复杂 Workflow 可以跨多个 Operation，因此 Stage 5 要把：

```text
Workflow -> Operations[]
```

提升为通用一等关系，不依赖 Shortlink `metadata.operations` 特例。

### 5.3.6 包命名

不使用根目录 `coverage/`，避免与 `pytest-cov` 依赖的 Python `coverage` 包冲突。

建议：

```text
coverage_engine/
```

## 5.4 使用方式

### OpenAPI 项目

只配置 OpenAPI 文件：

```yaml
contract:
  provider: openapi
  source: contracts/openapi.yaml
```

### 无 OpenAPI 项目

项目准备一份静态 Manifest：

```yaml
contract:
  provider: static_manifest
  source: testcases/my-project/contract/contract.yaml
```

测试 YAML 只需要使用稳定 Operation ID：

```yaml
operation_id: createOrder
```

Framework 后续自动建立：

```text
Operation
↔ Case
↔ Risk
↔ Workflow
```

## 5.5 阶段亮点（与传统方式的差异）

传统接口自动化通常关注：

```text
Case 数量
Pass Rate
```

本阶段增加的是：

```text
Contract-defined API Inventory
↔
Structured Test Assets
```

所以能回答“系统有什么、测了什么、缺什么”，为后续变更感知回归提供确定性数据，而不是让 AI 猜。

## 5.6 阶段产出与验收

已新增：

```text
contracts/
  model.py
  provider.py
  openapi_provider.py
  manifest_provider.py

coverage_engine/
  analyzer.py
  cli.py
  index.py
  gap.py
```

项目资产：

```text
testcases/<project>/contract/
```

机器输出：

```text
contract.json
coverage-index.json
coverage-gap.json
```

验收要求：

1. Static Manifest -> ApiContract；
2. OpenAPI YAML -> 同一 ApiContract；
3. OpenAPI JSON -> 同一 ApiContract；
4. operation_id 能绑定普通 Case；
5. Workflow 多 Operation 能进入 Coverage；
6. 未覆盖 Operation 可识别；
7. 错误 operation_id 可识别；
8. Framework Core 无 Shortlink 业务词；
9. 不修改 RequestClient/AssertionEngine 业务语义；
10. Shortlink Source 只作为 Static Manifest 的真实验证样例。

## 5.7 阶段产生的问题与解决方式

**问题 1：Shortlink 没有 OpenAPI。**
**解决：** 已从用户提供的后端源码一次性提取完整 API 清单，生成 Static Contract Manifest 草稿；不建设源码解析器。

**问题 2：微服务内部 API 与外部 API 重复。**
**解决：** Contract 增加 `service + visibility`，默认 Coverage 分母只统计 external surface。

**问题 3：普通 Case 单 `operation_id` 无法完整表达 Workflow。**
**解决：** Stage 5 将 Workflow 多 Operation 关系正式类型化。

**问题 4：`coverage/` 与 Python coverage 包同名。**
**解决：** 使用 `coverage_engine/`。

**问题 5：OpenAPI 文件可能没有 operationId。**
**解决：** 有 `operationId` 时直接使用；缺失时使用确定性的 `method:path` ID（例如 `post:/api/items`），并在 Operation metadata 中记录 `id_source=method_path_fallback`。这样来源可追踪，且不会生成随机/不可复现 ID。

**问题 6：项目新增 `contract/contract.yaml` 后，Pytest marker 注册曾把它误当 Test Specification。**
**解决：** 根 `conftest.py` 的 marker 扫描从 `testcases/**/*.yaml` 收紧为约定目录 `testcases/<suite>/yaml/*.yaml`。这样项目可以安全拥有 `contract/`、fixtures 等其他 YAML 资产，而不会污染测试收集。

**问题 7：为证明 `coverage_engine/` 不与第三方 `coverage` 包重名，最初架构测试直接 `import coverage`，导致没有安装该可选包的正常运行环境在 test collection 阶段失败。**
**解决：** 不新增依赖、不修改 requirements；架构守卫只检查仓库自身不存在根级 `coverage/` 或 `coverage.py`，并确认使用 `coverage_engine/`。原则是“守卫真实架构风险，而不是为了守卫本身强迫最终用户安装无关依赖”。


## 5.8 阶段总结

Stage 5 不负责“智能选择测试”，而是先建立可信的系统 API 清单与测试覆盖关系。

它是：

```text
Stage 4 Structured Cases
→ Stage 5 Contract/Coverage
→ Stage 6 Change-aware Regression
```

中间不可缺少的数据层。

## 5.9 当前进度

```text
设计原则：✅ 已确认
Contract 获取模式：✅ 已确认
Shortlink 后端接口清单：✅ 已提取（43 mappings / 27 external operations）
Static Manifest：✅ 已落地
ApiContract Model：✅ 已实现
StaticManifestProvider：✅ 已实现
OpenAPIProvider（YAML/JSON/local $ref）：✅ 已实现
Workflow 多 Operation：✅ 已正式建模
Coverage Index/Gap：✅ 已实现
独立 Coverage CLI：✅ 已实现
Stage 5 架构专项：✅ 用户 Windows 5 passed
框架全量：✅ 用户 Windows 211 passed in 31.88s
Shortlink Coverage CLI：✅ 8/27 = 29.63%，untested = 19，unknown bindings = 0
原 Mock smoke：✅ 2 passed / 4 deselected
Allure HTML：✅ 本机成功生成
额外第三方 coverage 依赖：✅ 不需要
用户本机复验：✅ 已完成
```

**阶段状态：✅ 已完成。**

### Stage 5 最终结论

Stage 5 已建立统一、来源无关的 Contract/Coverage 数据层：

```text
OpenAPI / Static Manifest
→ ApiContract
→ Case / Workflow Operation Relations
→ CoverageIndex
→ CoverageGap
```

当前 Shortlink 的 `8/27 = 29.63%` 是“现有代表性测试资产对 External Operation 的真实覆盖关系”，不是质量评分，也不要求为了提高数字而在本阶段继续扩张 Shortlink 用例。未覆盖的 19 个 Operation 将作为后续 Coverage Gap / Risk-based Test Design 的真实输入。

本阶段没有新增 Spring/Java 源码解析器，没有让 Framework Core 依赖当前 SUT，也没有改变原有 API Test Runtime 的 PASS/FAIL 语义。

---

# Stage 6：Change-aware Smart Regression

## 6.1 阶段目的

在 API Contract 发生变化时，以**可解释、可审计、用户可控且安全优先**的方式计算受影响测试范围。

Stage 6 的目标不是“每次都尽量少跑测试”，而是：

```text
有确定证据时安全缩小回归范围
不确定时诚实回退 FULL
用户始终保留 FULL 的最终执行权
```

Stage 6 V1 聚焦 **Contract-change-aware regression**，不冒充任意语言源码级影响分析系统。

## 6.2 当前问题 / 为什么需要该阶段

Stage 5 已经建立：

```text
ApiContract
+
Case / Workflow -> Operation
+
Coverage Index / Gap
```

但框架仍不能回答：

- 上一个被接受的 Contract 版本是什么；
- 当前 Contract 与基线相比改了什么；
- 哪些变化属于 Breaking / Risky / Non-breaking；
- 一个 Operation 变化后，除了直接 Case，还有哪些 Workflow / Context 依赖 Case 应该运行；
- Case 自己声明的 method/path 是否已经与 Contract 漂移；
- AUTO 无法安全判断时应该怎么办；
- 用户想全量、只预览、或额外强制加入 Case 时如何控制；
- 选择结果在哪里看、如何交给 Pytest 执行。

## 6.3 设计思路

### 6.3.1 总体流程

```text
Accepted Baseline Snapshot
+
Current Normalized ApiContract
↓
Contract Diff
↓
Changed Operations
↓
Direct Case / Workflow Mapping
↓
Context Dependency Expansion
↓
Case-Contract Drift Check
↓
User Includes
↓
Safety Check
↓
SelectionPlan
├── safe impacted set
└── unsafe -> FULL fallback
↓
selection.json / selection.md / Console
↓
Pytest collection filter
↓
Existing Runtime / JUnit / Allure
```

V1 **不接 AI**。只有确定性 Contract Diff + Dependency + Safety 证明稳定后，才重新评估 AI Semantic Supplement 是否确有必要。

### 6.3.2 用户控制模型

现有命令语义保持不变：

```text
--level smoke      -> 全部 smoke
--level core       -> 全部 core
--level regression -> 全部 regression
```

新增：

```text
--level all
```

表示当前项目全部结构化 Case。

`level` 与 `selection` 是两个独立维度：

```text
All Project Cases
↓
LEVEL = 候选全集
↓
SELECTION = 是否在候选全集中继续缩小
↓
Final Selected Cases
```

Selection 模式：

```text
--selection full   # 默认；保持现有行为
--selection auto   # 显式启用变更感知选择
--selection-only   # 只生成 SelectionPlan，不执行 Pytest
```

用户可以在 AUTO 中**做加法**：

```text
--include-case <case_id>
--include-tag <tag>
```

但 include 不能越过 `level` 候选边界；越界必须明确报错。

AUTO V1 不提供 `--exclude-case` 删除 Mandatory Case。AUTO 的可信语义为：

```text
Final = Mandatory ∪ User Includes
```

如果客户就是想全部测试，直接使用 `--selection full`；整个项目全量使用 `--level all --selection full`。

### 6.3.3 Baseline Snapshot 生命周期

Baseline 定义：

> **一个已被用户/团队明确接受的 Normalized ApiContract 历史版本。**

Baseline 不是上一次执行结果，也不自动绑定 Git 上一个 commit。

持久 Baseline 属于项目 Contract 资产：

```text
testcases/<project>/contract/baseline.json
```

允许通过环境 `contract.baseline` 显式指定其他路径；未配置时可从 Contract source 目录推导 `baseline.json`。

Baseline 只允许显式更新：

```text
baseline init   # 第一次建立
baseline accept # 明确接受当前 Contract 为新基线
```

普通：

```text
PASS / FAIL / FULL / AUTO / PREVIEW
```

均**不得修改 Baseline**。

Baseline 保存的是 Normalized Snapshot，而不是原始 OpenAPI / Static Manifest。Snapshot 可以保存 schema version、project、created_at、provider/source digest 等审计元数据，但 Diff 只比较 Contract Semantic Content。

缺失、损坏、项目不匹配、schema 不兼容的 Baseline 均视为 AUTO 不安全：

```text
AUTO requested
↓
Baseline unsafe/missing
↓
FULL fallback
```

而不是自动创建/覆盖 Baseline。

每次 AUTO Run 只把实际使用的 baseline/current/diff 复制到本次 Run Artifact，作为只读证据。

### 6.3.4 Contract Diff V1

Diff 比较统一 `ApiContract`，不直接比较原始 OpenAPI 文本，也不解析 Git Diff / Java 源码。

逻辑身份：

```text
operation_id
```

Operation 属性：

```text
method
path
parameters
request body
responses
```

V1 比较：

- Operation added / removed；
- method / path；
- parameter added / removed / required / type / format；
- request body required / content type；
- request field added / removed / required / type / format / nullable；
- response status added / removed；
- response field added / removed / required / type / format / nullable。

V1 忽略：

```text
summary
description
examples
doc tags
纯文档元数据
```

Severity：

```text
BREAKING
RISKY
NON_BREAKING
```

但 Severity 与“是否选择测试”分离：只要 Operation 有语义变化，它就是 Changed Operation，其已绑定 Case 进入 Direct Mandatory Set；Severity 只说明风险等级。

典型 Breaking：

- Operation removed；
- method/path changed；
- required parameter/field added；
- optional -> required；
- parameter/request/response field removed；
- type changed；
- success response status removed。

典型 Non-breaking：

- Operation added；
- optional request/response field added。

当前模型没有完整 constraints/enum 时不提前伪造比较能力；后续只有 Contract Model 真实支持这些字段时再扩展 Risky 规则。

### 6.3.5 Added / Removed Operation 特殊处理

Added Operation：

```text
OPERATION_ADDED
+
0 existing cases
↓
NEW_OPERATION_WITHOUT_TEST Coverage Gap
```

这不是“0 selected = everything is fine”，而是明确未覆盖变化，供后续 Stage 7 使用。

Removed Operation 必须利用 Baseline + CaseRegistry 中旧 operation_id 关系选择原有 Case，避免因为 Current Contract 已无该 Operation 而漏掉失效测试资产。

### 6.3.6 Endpoint Ownership（Stage 6.5 修正）

Stage 6 初版曾通过 `CASE_CONTRACT_DRIFT` 比较 Case 与 Contract 的 method/path。真实 Shortlink `/stats -> /stats-v2` 验证证明该机制能发现不一致，但同时暴露了更根本的问题：普通 Case 与 Contract 不应长期维护两份 endpoint。

Stage 6.5 后当前规则改为：

```text
Contract-bound Case
operation_id -> Current ApiContract -> method/path
```

普通 Case 不再保存相对 `method/path`，因此不再需要在主路径制造并检测 endpoint drift。跨服务绝对 URL 作为明确 override；standalone/unbound Case 自己维护 endpoint。

### 6.3.7 Dependency Expansion V1

只使用能够由测试资产明确证明的依赖：

```text
Case -> Operation
Workflow -> Operations
Case -> Context Provider
Context Provider -> Context Provider
Context Provider -> Operations
```

Context Provider 注册时显式声明：

```text
requires=(...)
operations=(...)
```

即使没有依赖，也明确写空 tuple，区分“已确认没有依赖”和“忘记声明”。

依赖关系全部传递展开，不提供任意 `dependency-depth` 截断。

Dependency Graph 必须检测：

- unknown Provider；
- unknown Operation；
- Provider dependency cycle。

Graph 无效：

```text
AUTO unsafe -> FULL fallback
```

V1 暂时**不做**：

- 独立 Operation -> Operation sidecar；
- Java/Python/Node/Go 源码调用图；
- DB Table / Redis Key lineage；
- tag 推断依赖；
- risk 推断依赖；
- AI dependency guessing。

如果第二 SUT / 真实 Stage 6 验证证明 Context/Workflow 关系不足，再重新评估显式 Operation Dependency。

### 6.3.8 Selection Reason

第一版标准 Reason Code：

```text
DIRECT_OPERATION_CHANGE
WORKFLOW_OPERATION_CHANGE
CONTEXT_OPERATION_DEPENDENCY
USER_INCLUDE
SMOKE_SAFETY_SET
FULL_MODE
AUTO_FALLBACK_FULL
```

同一个 Case 可以同时拥有多个 Reason，不丢失证据链。

### 6.3.9 Smoke Safety Set

只有：

```text
--level all --selection auto
```

默认把全部 Smoke 加入 Safety Set。

`--level regression/core/smoke` 时不越界加入其他 level，保持原有 level 语义。

### 6.3.10 AUTO 与 Pytest 集成

Stage 6 不重写测试执行器。

Selector 只生成稳定 `case_id` 集合和 SelectionPlan：

```text
SelectionEngine
↓
selection.json
↓
Pytest normal collection
↓
generic collection filter by stable case_id
↓
Existing Declarative Runtime / Python Workflow
```

不使用巨大 `pytest -k`；不修改 YAML；不临时删除 Case；不直接调用 CaseExecutor 绕过 Pytest。

Pytest collection filter 只消费 SelectionPlan，不理解 Contract Diff、Dependency 或具体 SUT。

### 6.3.11 结果呈现

执行前 Console 直接展示摘要：

```text
Mode
Baseline / Current
Changed Operations
Eligible Cases
Selected Cases
Direct / Workflow / Context / Drift / Safety counts
Fallback reason（若有）
Artifact location
```

人类详细查看：

```text
reports/runs/<run_id>/selection/selection.md
```

机器/CI 消费：

```text
reports/runs/<run_id>/selection/selection.json
```

本次 Contract 证据：

```text
reports/runs/<run_id>/contract/
├── baseline.json
├── current.json
└── diff.json
```

执行后的 Allure 可显示每条已执行 Case 的 Selection Evidence；但 Allure 不是 Selection 全局主入口，因为未执行的 Case 天然没有 Test Result。

### 6.3.12 Local-first / Thin CI

Stage 6 先完成 Local 完整闭环：

```text
Baseline init/accept
→ Diff
→ Preview
→ AUTO execution
→ FULL fallback
→ Selection Artifacts
→ Existing Allure/JUnit
```

Local 真实验收通过后，CI 只做薄接入：

- GitHub Actions / Jenkins 继续调用同一个 `run.py`；
- 可选暴露 `SELECTION=full|auto` / Preview 参数；
- 归档既有 `reports/runs/<run_id>/` 即可自然带上 selection/contract artifacts；
- CI 不重新实现 Selector；
- Baseline 不由普通 CI Run 自动 accept。

## 6.4 使用方式

### 保持原行为

```bash
python run.py --env test --level smoke
python run.py --env test --level core
python run.py --env test --level regression
```

等价于 `selection=full`。

### 整个项目全量

```bash
python run.py --env <env> --level all --selection full
```

### 整个项目 AUTO

```bash
python run.py --env <env> --level all --selection auto
```

### AUTO Preview

```bash
python run.py --env <env> --level all --selection auto --selection-only
```

### 在 AUTO 中额外加入测试

```bash
python run.py --env <env> --level all --selection auto \
  --include-case order.refund.boundary \
  --include-tag security
```

### Baseline 生命周期

```bash
python -m regression_engine.cli baseline init --env <env>
python -m regression_engine.cli baseline accept --env <env>
```

## 6.5 阶段亮点（与传统方式的差异）

传统方式常见：

```text
Git 文件变更 -> 粗暴映射测试
或
每次 Full Regression
或
让 AI 直接猜受影响测试
```

本阶段采用：

> **Accepted Contract Baseline + Deterministic Diff + Explicit Test Dependencies + Safe Fallback + User Control。**

它不是为了“少跑而少跑”，而是把“为什么跑 / 为什么没跑 / 为什么回退全量”都保存为机器和人可读证据。

## 6.6 阶段产出与验收

计划产出：

```text
regression_engine/
├── snapshot.py
├── diff.py
├── dependency.py
├── selection.py
├── analyzer.py
└── cli.py
```

必要的通用扩展：

- `ContextProviderRegistry` dependency metadata；
- `run.py` 增加 `level=all / selection / preview / user include`；
- Pytest 通用 SelectionPlan collection filter；
- Shortlink Provider 显式 dependency metadata；
- Shortlink initial accepted baseline；
- Stage 6 fixtures / unit / integration tests。

Local 验收必须覆盖：

1. baseline init/accept 都是显式动作；
2. 普通 run 永不修改 baseline；
3. missing/invalid baseline -> FULL fallback；
4. Normalized Contract Diff 能发现 operation/method/path/parameter/request/response 变化；
5. description 等纯文档变化不触发 Changed Operation；
6. Added Operation 无 Case 形成明确 gap；
7. Removed Operation 仍能选择旧绑定 Case；
8. Workflow 多 Operation 正确扩展；
9. Context dependency 传递展开；
10. unknown/cycle dependency -> FULL fallback；
11. Contract-bound Case 不重复保存 method/path，endpoint 由 Current Contract 解析；
12. `level` 先限定候选范围；
13. `level=all` 收集当前项目全部 Case；
14. AUTO selection 通过稳定 case_id 交给 Pytest；
15. AUTO 不使用巨大 `-k`、不改 YAML、不绕过 Pytest；
16. User Include 只能加、不越过 level；
17. `level=all + auto` 包含 Smoke Safety Set；
18. selection-only 不执行 Pytest；
19. selection.json/md + contract diff artifacts 生成；
20. 原 smoke/core/regression FULL 行为和 Allure/JUnit 不回归；
21. Framework Core / regression_engine 不出现 Shortlink 业务硬编码。

## 6.7 阶段产生的问题与解决方式

### 已在设计期解决的问题

**问题 1：AUTO 会不会夺走用户全量测试控制权？**
解决：默认 FULL；AUTO 必须显式开启；用户随时可 `--selection full`，整个项目使用 `--level all --selection full`。

**问题 2：选择结果在哪里看？**
解决：Console 摘要 + `selection.md` 人读 + `selection.json` 机器读；执行后的 Allure 只展示已执行 Case 的 Selection Evidence。

**问题 3：Baseline 是否自动更新？**
解决：绝不自动更新；只有显式 `baseline init/accept` 才能写持久 Baseline。

**问题 4：AUTO 如何不破坏现有 level？**
解决：Level 是外层候选范围，Selection 只在范围内缩小；新增 `all`，不修改 smoke/core/regression 原语义。

**问题 5：Dependency Graph 会不会变成另一个维护平台？**
解决：V1 只复用已有 Case/Workflow/Context 资产，并给 Context Provider 增加最小显式 metadata；不引入独立业务依赖 sidecar。

**问题 6：Service 内部实现改了但 Contract 没变怎么办？**
解决：V1 明确不做任意源码影响分析；用户/CI 可选择 FULL。不能把“Contract 没变”伪装成“业务一定没影响”。

**问题 7：AI 是否现在进入 Selector？**
解决：V1 不接 AI。先证明确定性选择闭环有价值，再决定是否存在必须由 AI 补充的真实语义缺口。

### 实施期新增问题与解决

**问题 8：`run_tests()` 在同一 Python 进程多次执行时会残留 `API_HOST/API_TIMEOUT/...`，新增 Stage 6 Runner 测试后暴露出配置串扰。**
解决：把 API 运行态改为上下文管理；一次 run 结束后恢复调用前环境。该修复属于通用 Runner 稳定性，不依赖 Stage 6 或 Shortlink。

**问题 9：Baseline Snapshot 曾可能带入 Contract metadata 中的本机绝对 `source_path`。**
解决：持久 Baseline 只保存可移植的 Normalized Semantic Contract 和必要审计元数据；运行时本机路径在 Snapshot 前剥离，避免跨机器无意义 Diff 和目录泄露。

**问题 10：Stage 6 新测试文件与已有 Coverage 测试同名，Pytest 默认 import mode 下发生 `test_analyzer/test_cli` 顶层模块冲突。**
解决：使用唯一测试模块名 `test_regression_analyzer.py / test_regression_cli.py`，不修改全局 Pytest import mode 去掩盖命名问题。

**问题 11：Thin CI 应如何接入而不产生第二套 Selector？**
解决：Jenkins 只增加 `LEVEL=all`、`SELECTION=full|auto`、`SELECTION_ONLY` 参数并传给 `run.py`；GitHub Actions 只新增受控 Demo AUTO Preview。两者都不执行 `baseline init/accept`，也不复制 Diff/Dependency/Selector 逻辑。

## 6.8 阶段总结

Stage 6 的核心不是一个“智能算法”，而是一套受控回归决策协议：

```text
Accepted Baseline
→ Explainable Diff
→ Explicit Dependencies
→ Mandatory Selection
→ Safe Full Fallback
→ User-controlled Execution
→ Auditable Evidence
```

## 6.9 当前进度

```text
Stage 5 前置：✅ 已完成
用户控制模型：✅ 已实现
Baseline init / accept：✅ 已实现
Normalized Contract Diff：✅ 已实现
Dependency Expansion：✅ 已实现
Case–Contract Drift：♻️ 已由 Stage 6.5 的单一 endpoint 事实源取代
SelectionPlan / FULL fallback：✅ 已实现
level=all / FULL / AUTO / Preview：✅ 已实现
User Include（只加不减）：✅ 已实现
Pytest stable case_id filter：✅ 已实现
Selection JSON / Markdown：✅ 已实现
Allure Selection Evidence：✅ 已实现
Demo Contract + Baseline：✅ 已接入
Shortlink Accepted Baseline：✅ 已接入
Stage 6 Architecture Guard：✅ 已实现
Thin GitHub Actions Preview：✅ 配置与离线契约验证
Thin Jenkins parameters：✅ 配置与离线契约验证
Stage 6 专项/契约测试：✅ 73+ passed
Framework 全量：✅ 269 passed, 2 skipped
原 Demo smoke/core/regression：✅ 各 2 passed, 4 deselected
Demo level=all FULL：✅ 6 passed
Demo AUTO Preview：✅ 2 / 6 selected
Demo AUTO 真执行：✅ 2 passed, 4 deselected
Shortlink AUTO Preview：✅ 6 / 18 selected（无 HTTP 请求）
compileall：✅ PASS
用户 Windows Shortlink AUTO Preview：✅ 真实 `/stats -> /stats-v2` 识别 1 changed operation，18 eligible -> 7 selected
用户 Windows Shortlink Drift 实执行：✅ 5 个无关 Smoke 通过，2 个旧 `/stats` Statistics Case 真实返回 404
用户 Windows Shortlink Case 修复后实执行：✅ `/stats-v2` 真实返回 200，7 passed / 11 deselected
GitHub Actions 真实平台：✅ main 最新提交已真实运行并绿灯
Jenkins 真实平台：🟡 SCM/代理已打通；FULL 连续两次 17/18，通过 CI 暴露 `shortlink.link.create.db_persistence` 的稳定诊断顺序问题
```

**阶段状态：🟡 核心 Change-aware Regression 已在真实 Shortlink 后端完成一次“变更 -> 选中 -> 旧 Case 失败 -> Case 修复 -> 通过”的 Local 闭环；最终 CI 平台验收与 Stage 6.5 一并完成后关闭。**

---

# Stage 6.5：Contract-driven Case Simplification

## 6.5.1 阶段目的

真实 Shortlink `/stats -> /stats-v2` 验证暴露出当前测试资产存在重复事实源：

```text
Contract: operation_id + method + path
Case YAML: operation_id + method + path + test data + assertions
```

接口路径改变后需要同时修改 Contract 与 Case path。Stage 6 的 `CASE_CONTRACT_DRIFT` 能发现这种不一致，但更好的设计不是长期维护重复数据再检测漂移，而是从模型上消除普通 Case 的 endpoint 重复。

本阶段目标：

> **让 Contract 成为普通 API Operation 的 method/path 单一事实源；Case YAML 只维护测试输入、断言、提取、依赖与动态 path 参数；普通 Contract-bound Case 不再保存任何 method/path/url endpoint 信息。**

## 6.5.2 设计原则

1. Contract-bound Declarative Case 通过 `operation_id` 解析当前 `ApiContract.Operation`。
2. 普通 Case 不再声明 `request.method` / `request.path`。
3. Contract-bound Case 禁止直属 `request.url`。多服务/跨网关路由由 `Operation.service` 与环境 `api.service_hosts` 共同解析；Case 只提供 `path_params` 等运行时数据。
4. 无 `operation_id` 的 standalone/ad-hoc Case 仍允许显式 `method + path/url`，但 Coverage 会继续把它视为 unbound asset；这样不强迫所有临时测试先建 Contract。
5. Workflow Case 不依赖自身 dummy endpoint；复杂 Python 只负责 branch/loop/try/finally/状态编排，原子 HTTP 步骤优先通过稳定 `case_id` 调用已有 YAML Case。
6. 不为了保留 `CASE_CONTRACT_DRIFT` 而故意保存重复 endpoint。Contract-bound Case 不再产生 endpoint drift；Standalone asset 仍自行负责显式 endpoint。
7. V1 不实现完整 OpenAPI path-parameter DSL。若 Contract path 包含 `{id}`，本阶段只加入最小 `request.path_params` 显式替换能力；值仍支持现有 `${...}` 动态变量。
8. RequestClient 网络职责不变；CaseExecutor/CaseSpec 解析 Contract method/path/service，ApiRunner 只根据通用 `api.host + api.service_hosts` 选择环境 base URL 并发送请求。

## 6.5.3 目标数据流

```text
Case YAML
  operation_id: shortlinkStats
  request:
    headers / params / json / data / request_options
        +
Current ApiContract
  shortlinkStats -> GET /api/short-link/admin/v1/stats-v2
        ↓
CaseExecutor endpoint resolution
        ↓
ApiRunner
        ↓
RequestClient
```

多服务 / 动态路径：

```text
Current Contract
  operation_id: shortlinkRedirect
  service: project
  method: GET
  path: /{short-uri}
        +
Environment
  api.host: http://127.0.0.1:8000
  api.service_hosts.project: http://nurl.ink:8001
        +
Case YAML
  operation_id: shortlinkRedirect
  request.path_params.short-uri: ${short_uri}
        ↓
GET http://nurl.ink:8001/<resolved-short-uri>
```

## 6.5.4 兼容边界

支持两种 Case：

```text
A. Contract-bound（推荐）
operation_id required
request 不写 method/path

B. Standalone（兼容/临时）
operation_id absent
request 必须显式 method + path/url
```

Contract-bound Case 若仍同时声明 `request.method` 或相对 `request.path`，collection 阶段直接报清晰错误，避免新项目继续制造重复事实源。

## 6.5.5 实施任务

### Task 1 — CaseSpec 契约收缩

- Contract-bound Declarative Case 不再要求 path/url；
- 禁止其重复声明 method/relative path；
- Contract-bound Case 同时禁止直属 `request.url`；
- Standalone Case 保持显式 endpoint；
- Workflow Case 允许没有 dummy request endpoint；
- 增加 `path_params` 结构校验。

### Task 2 — Contract-aware CaseExecutor

- `CaseExecutor` 可注入当前 `ApiContract`；
- `operation_id -> Operation.method/path`；
- Contract-bound Case 未注入 Contract、unknown operation 均在发 HTTP 前失败；
- 合并 `path_params` 到 Contract path；
- 将 `Operation.service` 传递给 ApiRunner，由环境 `api.service_hosts` 选择 base URL；未配置 service host 时回退 `api.host`。

### Task 3 — Pytest Runtime 注入 Contract

- 新增/复用 session `api_contract` fixture；
- 当前环境存在 Contract 时加载一次并注入 CaseExecutor；
- Framework tests / standalone Case 不被强制依赖 Contract。

### Task 4 — Demo / Shortlink 资产迁移

- Demo 6 条普通 Case 删除重复 method/path；
- Shortlink 管理类普通 Case 删除重复 method/path；
- Redirect Case 删除 absolute `url`，改用 `path_params`；目标 host 由 Contract `service` 与环境 `api.service_hosts` 解析；
- Workflow Case 删除 dummy request endpoint；
- 不修改业务输入、断言、requires、operation_id、level、tags、risks。

### Task 5 — Stage 6 Drift 语义收缩

- Contract-bound 无 endpoint override 的 Case 不再做 method/path drift 比较；
- Standalone 不参与 operation drift；
- Contract-bound Case 不再存在 endpoint override；Standalone absolute URL 与 Contract drift 无关；
- 更新 Stage 6 tests，删除“重复事实源必须长期存在”的假设。

### Task 6 — 真实回归与 CI

- Framework 全量；
- Demo smoke/core/regression/all FULL；
- Demo AUTO Preview + AUTO 真执行；
- Shortlink Preview（本地无真实凭据也可执行）；
- 用户 Windows 真实 Shortlink `/stats-v2` 场景重新验证：Contract 改后 Case 不改 endpoint 也能直接调用新路径；
- GitHub Actions / Jenkins 最终验收后再关闭 Stage 6/6.5。


### Task 7 — Multi-service Endpoint Resolution（用户全资产审计后补充）

- `Operation.service` 进入执行时 `base_info`；
- 环境新增通用 `api.service_hosts` 映射，key 只与 Contract service 标识对应；
- `ApiRunner` 对相对 Contract path 先按 service 查 `service_hosts`，未命中再回退兼容的 `api.host`；
- Contract-bound `request.url` collection 阶段直接拒绝；Standalone 仍允许 absolute URL；
- Shortlink Redirect 4 条 Case 全部迁移为 `path_params`，不再保存 `nurl.ink:8001` 或 `/{short-uri}`；
- `env_template.yaml` 提供通用多服务示例；Shortlink 本地环境仅作为一个项目适配样例，不进入 Core 分支；
- 架构守卫动态扫描 `testcases/*/yaml/*.yaml`，禁止任何 Contract-bound Case 直属 `method/path/url`，但允许 `request.json` 等业务 payload 中出现同名字段。

## 6.5.6 验收标准

1. 普通 Contract-bound YAML 中不存在重复 `method/path`；
2. 修改 Contract path 后，不修改该 Case endpoint 即能调用新路径；
3. Case 测试数据/断言仍由 YAML 管理；
4. 复杂 Workflow 仍通过 `CaseExecutor.execute(case_id)` 复用原子 Case，不把 YAML 扩展成控制流语言；
5. 多服务 Contract Operation 可通过 `api.service_hosts` 工作，Case 不保存绝对 URL；
6. Standalone Case 仍可用于临时/未建 Contract 的接口；
7. Coverage / Smart Regression 仍以稳定 `operation_id` 工作；
8. 无 Shortlink 业务逻辑进入 Core；
9. 原 FULL/AUTO/Allure/JUnit 行为不回归。

## 6.5.7 当前进度

**🟡 Endpoint Ownership 已完成第二轮通用化收敛与离线回归，等待用户 Windows 多服务真实 Shortlink 验证及最终 CI 验收。**

当前已完成：

- `CaseSpec`：Contract-bound Declarative Case 不再保存 `request.method/path`；Standalone 保留显式 endpoint；Workflow 可省略 dummy endpoint；最小 `path_params` 已支持；本轮继续收敛 Contract-bound absolute URL；
- `CaseExecutor`：新增统一 `build_runner_parts(case_id)`，通过 `operation_id -> ApiContract.Operation` 解析 method/path，普通执行与项目 helper 共用同一入口；
- Pytest Runtime：当前环境 Contract 以 session fixture 注入 `CaseExecutor`；
- Demo / Shortlink YAML：所有 Contract-bound Case 直属 `request.method/path/url` 已清零；Shortlink Redirect 4 条 Case 已由 absolute URL 迁移为 `path_params`；
- Stage 6：主路径 `CASE_CONTRACT_DRIFT` 已移除，不再通过保存重复 endpoint 来证明一致性；
- 架构守卫：动态扫描全部 `testcases/*/yaml/*.yaml`；任何带 `operation_ids` 的 Contract-bound Case（Declarative/Workflow）若重新出现直属 `request.method/path` 都会失败，不硬编码任何 SUT 名称；守卫已升级为动态扫描所有 suite，Contract-bound `request.method/path/url` 全部禁止；Standalone endpoint 仍保持兼容；
- Framework 全量：**281 passed, 2 skipped**；
- Multi-service Runtime：`Operation.service` 已进入执行边界；`ApiRunner` 支持通用 `api.service_hosts`，未映射 service 自动回退 `api.host`；
- 全资产扫描：**7 个项目测试 YAML / 24 条 Case / 24 条 operation-bound asset（含 2 Workflow）**，直属 `request.method/path/url` 残留 **0**；
- Demo `publish_api.yaml` 中仅保留 `request.json.method/path` 业务 payload 字段，架构守卫不会把嵌套业务数据误判为 endpoint。
- Demo smoke/core/regression：各 **2 passed, 4 deselected**；
- Demo `level=all --selection full`：**6 passed**；
- Demo AUTO Preview：**2 / 6 selected**；Demo AUTO 真执行：**2 passed, 4 deselected**；
- Shortlink AUTO Preview（当前 Contract 无变化）：**6 / 18 selected**；
- Shortlink Coverage：**8 / 27 (29.63%)，untested=19，unknown_bindings=0**；
- `compileall`：PASS；生产路径中已无 `CASE_CONTRACT_DRIFT`；Demo/Shortlink Contract-bound endpoint duplication=0。
- V4.4 完整 overlay 从上一版 Stage 6 基线重建后包级验证：**281 passed, 2 skipped**，Demo AUTO Preview **2 / 6 selected**；
- V4.4 correction overlay 从上一版 Stage 6.5 基线重建后包级验证：**281 passed, 2 skipped**，Demo AUTO Preview **2 / 6 selected**；
- 两个用户覆盖包均主动排除 `config/env.shortlink-local.yaml`，避免覆盖本机真实凭据；真实 Shortlink 验证只需在现有 `api:` 下合并通用 `service_hosts.project` 路由。
- 用户反馈后补做全资产审计：共发现 **7 个项目测试 YAML / 24 条 Case / 22 条 Contract-bound Declarative Case / 2 条 Workflow Case**；Contract-bound `request.method/path` 残留为 **0**；仅 Shortlink Redirect 的 **4 条 Case** 保留 absolute `request.url` override。守卫已从硬编码 `demo/shortlink` 改为动态扫描所有项目 suite，并覆盖 Workflow 的 `operation_ids`。

下一条关键真实验收不是再次手工修改 Case path，而是：

```text
真实 Backend      = /stats-v2
Current Contract   = /stats-v2
Accepted Baseline  = /stats
statistics.yaml    = 不包含 method/path
        ↓
AUTO 识别 1 个 PATH_CHANGED
        ↓
只通过 operation_id 从 Current Contract 解析 /stats-v2
        ↓
预计 7 selected / 11 deselected，且 Stats Case 真实请求 /stats-v2 并通过
```

用户 Windows 真实 SUT 已进一步完成：

```text
/stats -> /stats-v2
Baseline /stats vs Current /stats-v2 -> 1 changed / 7 selected -> 真实执行通过
accept baseline -> 0 changed / 6 Smoke Safety -> Preview + 真实执行通过
/stats-v2 -> /stats（Case YAML 不改 endpoint）
Baseline /stats-v2 vs Current /stats -> 1 changed / 7 selected -> 真实执行通过
最终 Baseline 恢复 /stats -> unchanged 状态通过
```

GitHub Actions 在最新 `main` 上已绿。Jenkins SCM 代理问题也已解决，能够正常 fetch/checkout 最新 Jenkinsfile。Jenkins FULL 连续两次得到 **17 passed / 1 failed**，唯一失败均为 `shortlink.link.create.db_persistence`：创建接口 HTTP 200 后，后置 DB 断言中的 `${short_url}` 在整组 validation 预解析阶段抛 `VariableNotFoundError`，遮住更早的业务响应断言。

## 6.5.8 Stage 6.5.1 — Failure Evidence Ordering & Allure Diagnostics

### 问题

旧执行顺序：

```text
HTTP Response
↓
extract
↓
一次性解析整组 validation 的所有 ${...}
↓
Assertions.assert_all(...)
```

当响应为 HTTP 200 但业务失败、`extract` 未得到 `short_url` 时，后置 DB 规则 `${short_url}` 会在真正执行 `$.code == "0"` 前抛错，导致次生 `VariableNotFoundError` 覆盖原始 API 业务失败。该问题与 Shortlink 无关，任何“响应断言 + extract + DB/Redis 动态变量断言”的第二 SUT 都可能遇到。

### 修复原则

1. 不加 POST 自动重试，不为了 Jenkins 绿而弱化真实失败；
2. YAML 断言按声明顺序逐条做动态变量解析；
3. AssertionEngine 仍是唯一断言解释器；
4. 无缺变量时继续聚合多条断言失败；
5. 后置规则缺变量时，如果前面已有确定的 Assertion Failure，优先报告原始断言；
6. RequestClient 原有 Allure `响应结果` 保留，不重复造 Response Body 附件；
7. 新增 Allure `响应元数据`（当前至少 status_code）；
8. 有 `extract` 时新增脱敏的 `响应提取结果`，包含 rules / extracted / missing。

### TDD 证据

回归用例构造：HTTP 200、`code=B001`、`data=null`、声明 `short_url=$.data.fullShortUrl`，后置 `db_exists.params` 引用 `${short_url}`。

RED：旧代码稳定抛 `VariableNotFoundError: short_url not found`，与 Jenkins #31/#32 一致。

GREEN：修改后优先得到 `eq $.code expected='0' actual='B001'`，且 `short_url` 次生错误不再遮蔽原始失败。新增 Allure Extract Evidence 与 Response Metadata 两条测试也完成红 -> 绿。

### 当前状态

- 新增专项回归：3 passed；
- Runner/Assertion/Context/Request/Shortlink Support 相关回归：51 passed；
- Framework 全量 fresh verification：**284 passed, 2 skipped（286 collected）**；
- 相关 Runner/Assertion/Context/Request/Shortlink Support 回归：**51 passed**；专项 Stage 6.5.1：**3 passed**；
- `compileall`：PASS；Demo FULL：**6 passed**；Demo AUTO Preview：**2 / 6 selected**；Demo AUTO Real：**2 passed, 4 deselected**；
- 用户侧下一步：应用 Stage 6.5.1 correction overlay，先本地验证，再 push；Jenkins FULL 再跑一次以暴露 `/create` 的真实业务 code/message；随后继续 AUTO Preview / AUTO Real。

Stage 7 继续暂停，不在本修复中扩展 AI 功能。

---

# Stage 7：AI Risk-based Test Design

## 7.1 阶段目的

让 AI 真正解决传统自动化较难解决的问题：

> 基于 Contract Change、Coverage Gap 和 Risk Metadata 推理“还应该测试什么”。

## 7.2 当前问题 / 为什么需要该阶段

简单的“接口文档 -> YAML”更多是格式转换，工程价值有限。

真正困难的是：

- 哪些变化引入新风险？
- 已有 Case 是否覆盖关键边界？
- 哪些异常场景值得新增？

## 7.3 设计思路

```text
Changed Operation
+ Contract Diff
+ Existing Coverage
+ Coverage Gap
+ Risk Metadata
↓
LLM
↓
Strict TestIntent
↓
Validator
↓
Deterministic Case Compiler
↓
Candidate YAML
↓
Human Review
```

## 7.4 使用方式

AI 生成的永远是 Candidate，不自动进入正式 Regression。

## 7.5 阶段亮点（与传统方式的差异）

AI 不替代断言、不直接写正式测试、不凭空发明接口；它只在确定性数据之上补充风险推理。

## 7.6 阶段产出与验收

- TestIntent；
- Prompt；
- Validator；
- deterministic compiler；
- candidate review flow。

## 7.7 阶段产生的问题与解决方式

**风险：** 模型幻觉字段/Operation。
**解决：** 所有引用必须存在于 ApiContract。

**风险：** AI 候选质量不稳定。
**解决：** Strict Validator + 人工 Review，不自动提交正式 Case。

## 7.8 阶段总结

把 AI 放在“风险设计”这个真正需要语义推理的位置，而不是包装传统参数化。

## 7.9 当前进度

**⏳ 未开始，依赖 Stage 5/6。**

---

# Stage 8：Failure Triage & Allure Enrichment

## 8.1 阶段目的

把“大量失败用例”转换为“少量可以排查的问题簇”，降低 CI 故障排查成本。

## 8.2 当前问题 / 为什么需要该阶段

传统 Allure 能告诉测试人员：

```text
18 failed
```

但实际可能只是：

```text
认证前置故障 -> 12
Redis 连接问题 -> 4
业务行为变化 -> 2
```

逐条点开排查效率很低。

## 8.3 设计思路

```text
Failures
↓
Normalize / Fingerprint
↓
Cluster
↓
Known Deterministic Classifier
↓
Ambiguous Cluster
↓
AI Triage
↓
Allure Enrichment
```

AI 不修改 Pytest PASS/FAIL。

## 8.4 使用方式

原始 run artifact 保留不可修改。

Triage 读取 artifact，生成增强证据，再进入 Allure 展示。

## 8.5 阶段亮点（与传统方式的差异）

不是让 LLM 把 traceback 换一种说法，而是先用确定性 fingerprint/cluster 降维，
AI 只处理无法稳定分类的少数问题。

## 8.6 阶段产出与验收

已存在基础：

- FailureEvidence；
- Facts；
- Sanitizer；
- Provider/Protocol Config；
- Fact 引用 Validator；
- safe degradation。

待完成：

- Fingerprint；
- Cluster；
- Known Failure Classifier；
- Allure Enricher；
- CI 自动 Triage。

## 8.7 阶段产生的问题与解决方式

**问题：** AI 可能把猜测写成事实。
**解决：** 假设必须引用真实 Fact ID。

**问题：** 模型不可用可能污染测试结果。
**解决：** AI 子系统独立降级，不改变原始 run/JUnit/Pytest exit code。

## 8.8 阶段总结

已有 AI Evidence Foundation 会在本阶段被真正用于“失败聚类 + 歧义分诊”，而不是提前冒充完成。

## 8.9 当前进度

**🟡 基础已具备，完整阶段未开始实施。**

---

# Stage 9：第二 SUT 与最终复用性证明

## 9.1 阶段目的

最后证明：

> Shortlink 不是框架成立的前提。

## 9.2 当前问题 / 为什么需要该阶段

即使 Core 中没有明显 Shortlink 字样，如果只有一个真实 SUT，面试官仍可以质疑框架只是围绕当前业务自然长出来的。

## 9.3 设计思路

选择业务与 Shortlink 明显不同、最好自带 OpenAPI 的第二 SUT。

目标：

```text
New SUT
→ new env config
→ new contract
→ new YAML cases
→ optional context/workflow
→ Core zero business change
```

## 9.4 使用方式

新项目只新增项目资产和配置，不修改：

```text
core/
db/
contracts/
coverage_engine/
ai/
Generic Runtime
```

## 9.5 阶段亮点（与传统方式的差异）

复用性不靠口头宣称，而靠“第二 SUT 接入 Git diff”证明。

## 9.6 阶段产出与验收

- 第二 SUT；
- OpenAPI Provider 真实使用；
- Coverage；
- Smart Regression；
- zero-core-business-change proof；
- 最终 README/架构/简历材料。

## 9.7 阶段产生的问题与解决方式

若第二 SUT 需要修改 Core 才能接入，优先判断：

1. 真的是通用能力缺口？
2. 还是项目特有逻辑应该留在 Adapter/Context/Workflow？

只有第一类才能进入 Core。

## 9.8 阶段总结

这是框架“可复用”从设计原则变成可验证事实的最后一道门。

## 9.9 当前进度

**⏳ 未开始。**

---

# 4. Stage 5 Contract 配置规范（当前设计稿）

## 4.1 配置位置

第一版不新增额外 `project.yaml` 强迫用户维护第二份项目配置。

继续复用：

```text
config/env.<project>.yaml
```

加入：

```yaml
contract:
  provider: static_manifest
  source: testcases/my-project/contract/contract.yaml
```

或：

```yaml
contract:
  provider: openapi
  source: contracts/openapi.yaml
```

## 4.2 Static Manifest 最小字段

```yaml
version: 1
project: my-project

operations:
  - id: createOrder
    service: order
    visibility: external
    method: POST
    path: /api/orders
```

Request/Response Schema 可以渐进补充。

## 4.3 为什么使用显式配置而不是自动猜路径

隐藏自动发现对单一项目看起来方便，但多项目/多 Contract 时会变得不可控。

显式 `provider + source` 更容易：

- CI；
- 多环境；
- Snapshot；
- Debug；
- 第二 SUT；
- 面试讲解。

---

# 5. 计划书长期维护规则

每个阶段推进时，不再追加大段“V3.x.x 更新日志”。

必须更新四个位置：

1. 顶部 `版本 / 日期 / 当前阶段`；
2. 当前 Stage 的：
   - 问题与解决；
   - 产出与验收；
   - 当前进度；
3. `阶段状态总览`；
4. 若发生跨阶段架构决策，再更新“总体架构/边界”。

阶段关闭前必须有真实证据：

```text
Code
+
Automated Tests
+
Real Run / CI / Artifact（适用时）
```

---

# 6. 当前下一步

Stage 5 已正式关闭。Stage 6 已在真实 Shortlink `/stats -> /stats-v2` 变更上证明 AUTO 18 -> 7、旧 Case 真实 404、修复后 7/7 通过；该真实验证同时暴露 Contract 与 Case endpoint 重复维护问题。因此当前唯一执行路线调整为 Stage 6.5 Contract-driven Case Simplification，Stage 7 暂停。
