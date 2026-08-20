# AI 辅助接口自动化测试框架项目计划书

> **版本**：V4.1（Stage 5 代码与离线验收版）
> **更新日期**：2026-08-20
> **当前阶段**：Stage 5 — Contract & Coverage Intelligence（代码与离线验收完成，待用户本机复验后正式封板）
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
| Stage 5 | Contract & Coverage Intelligence | 🟡 代码与离线验收完成 / 待用户本机复验 |
| Stage 6 | Change-aware Smart Regression | ⏳ 未开始 |
| Stage 7 | AI Risk-based Test Design | ⏳ 未开始 |
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
Stage 5 专项测试：✅ 34 passed
框架全量：✅ 211 passed
Mock smoke/core/regression：✅ 各 2 passed / 4 deselected
Shortlink 离线 Coverage：✅ 8/27 = 29.63%，unknown bindings = 0
用户本机复验：⏳ 待执行
```

**阶段状态：🟡 代码与离线验收完成，待用户本机复验后正式标记完成。**

---

# Stage 6：Change-aware Smart Regression

## 6.1 阶段目的

当 API Contract 发生变化时，不盲目全量回归，也不让 AI 猜测必跑用例，而是确定性计算受影响集合。

## 6.2 当前问题 / 为什么需要该阶段

传统做法：

```text
代码变了
→ 不确定影响
→ 全量回归
```

大型接口项目会浪费大量时间；但“只凭代码文件名”选择测试又有漏测风险。

## 6.3 设计思路

```text
Old Contract
+
New Contract
↓
Contract Diff
↓
Changed Operations
↓
Coverage Index
↓
Dependency Graph
↓
Mandatory Cases
↓
Safety Policy
↓
Optional AI Semantic Supplement
```

AI 只能 Add/Escalate，不能删除 Mandatory Set。

## 6.4 使用方式

目标：

```bash
python run.py --env <ENV> --selection auto
```

也允许显式 full regression。

## 6.5 阶段亮点（与传统方式的差异）

不是基于 Git 文件路径粗暴选测试，也不是把全部判断交给 LLM，而是：

> Contract Diff + Coverage + Dependency First，AI Last。

## 6.6 阶段产出与验收

- Contract Snapshot；
- Contract Diff；
- Changed Operations；
- Dependency Graph；
- Selector；
- fallback；
- selection evidence。

## 6.7 阶段产生的问题与解决方式

预期风险：

**Contract/Coverage 不完整导致漏测。**
解决：无法确认影响边界时强制 Full Regression。

**公共 Auth / Shared Schema 变化影响范围过大。**
解决：高风险基础能力变化直接升级回归范围。

## 6.8 阶段总结

目标不是“少跑测试”，而是在有确定证据时安全减少无关回归。

## 6.9 当前进度

**⏳ 未开始，依赖 Stage 5。**

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

Stage 5 代码侧已经完成：

```text
ApiContract
+ StaticManifestProvider
+ OpenAPIProvider
+ Workflow 多 Operation
+ CoverageIndex / CoverageGap
+ Standalone Coverage CLI
+ Shortlink Static Manifest
```

当前只剩用户本机复验：

```bash
python -m pytest tests -q
python -m coverage_engine.cli --env shortlink-local
python run.py --env test --level smoke
```

本机复验通过后，将 Stage 5 状态更新为 ✅ 已完成，再进入 Stage 6 Contract Diff / Smart Regression。
