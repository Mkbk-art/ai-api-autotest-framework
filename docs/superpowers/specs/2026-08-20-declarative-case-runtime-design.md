# Declarative Case Runtime Design

## Goal

让普通 API 测试场景成为可直接执行的 YAML Test Specification，不再要求项目为每个业务域维护 Python 参数化 wrapper；只有存在复杂控制流和状态生命周期的场景保留 Python Workflow。

## Boundaries

- Framework Core 不识别任何 Shortlink 业务词。
- YAML 不引入 if/for/while/try/finally 等控制流。
- 普通 Case 使用 YAML；复杂业务生命周期使用 Python Workflow。
- Python Workflow 必须通过 CaseRegistry/CaseExecutor 复用 YAML Case，不重新实现普通 HTTP 请求。
- Pytest、Allure、smoke/core/regression marker、VariableContext、DB/Redis 断言保持可用。
- 真实凭据、API Key、`config/ai.local.yaml`、`.env`、运行日志和报告不得进入公开交付包。

## CaseSpec V2

一份 YAML 文件使用：

```yaml
version: 2
cases:
  - id: auth.login.success
    name: 登录成功
    operation_id: userLogin
    level: smoke
    tags: [auth]
    risks: [authentication]
    requires: [project.static]
    execution: declarative
    request:
      api_name: 用户登录
      method: POST
      path: /api/login
      headers:
        Content-Type: application/json
      json: {}
    extract: {}
    assertions: []
```

`execution: workflow` 表示该 Case 仅由 Python Workflow 显式调用/编排，不由普通 YAML Runtime 自动收集。

## Core Components

### CaseSpec

负责验证单条 YAML Case 的稳定机器身份、请求、断言和元数据。

### CaseRegistry

负责扫描当前项目 YAML，建立：

- case_id -> CaseSpec
- operation_id -> CaseSpec[]
- level/tags/risks 索引

### ContextProviderRegistry

项目通过字符串名称注册 setup/cleanup 上下文。Core 只理解 Provider 协议，不理解业务。

### CaseExecutor

执行链：

```text
CaseSpec
-> requires Context Providers
-> project before_case hook
-> ApiRunner
-> project after_response hook
-> optional project cleanup
```

Workflow 也复用同一 CaseExecutor。

### Generic Pytest Runtime

框架统一提供一个 generic test function，由 collection hook 按当前项目 YAML 参数化；用户新增普通 YAML Case 不需要新增 `test_xx.py`。

## Project Model

项目目录继续暂时保留在 `testcases/<project>/`，避免本轮同时引入目录迁移风险；本轮只整改执行模型。下一阶段再独立评估是否迁移到 `projects/<project>/`。

每个项目允许：

- `cases/*.yaml`
- `context.py`
- `adapter.py`
- `workflows/*.py`

项目 Python 只允许实现项目上下文和复杂 Workflow。

## Shortlink Migration Rule

普通 Case 转为 declarative；复杂生命周期保留 Workflow。

迁移后的边界以“测试主体是否存在控制流”为准，而不是“是否需要前置资源”为准。
Page、普通 Redirect、回收态 Redirect、Statistics 仍是单接口 Case，它们通过 Context Provider
准备已创建/已回收/已访问资源，因此继续 declarative。当前仅两条 Recycle Storage Regression
保留 Python Workflow：Create -> Save -> 中间 DB/Redis 断言 -> Remove -> 终态断言/异常清理。

普通登录、鉴权失败、Group、Create、Page、Redirect、Statistics 等不再保留项目 test wrapper。

## Security

- `config/ai.local.yaml` 永不进入公开包。
- env 示例只保留 `CHANGE_ME` / null 等占位值。
- 最终打包前扫描常见 Secret 模式和本地 Artifact。
