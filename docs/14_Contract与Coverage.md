# Contract 与 Coverage 使用说明

## 1. 目的

Stage 5 让框架知道“系统有哪些 API、哪些测试覆盖了哪些 API、还有哪些 API 没有测试”。

它不执行 HTTP 请求，也不改变 Pytest PASS/FAIL。

## 2. Contract 来源

### 有 OpenAPI 3.x

```yaml
contract:
  provider: openapi
  source: path/to/openapi.yaml
```

支持 OpenAPI 3.x YAML/JSON、本地 `#/components/...` 引用。存在 `operationId` 时直接使用；缺失时生成稳定的 `method:path` ID，并记录 ID 来源。

### 无 OpenAPI

准备静态 Manifest：

```yaml
contract:
  provider: static_manifest
  source: testcases/my-project/contract/contract.yaml
```

后端源码、接口文档、Postman/Apifox 只是 Manifest 的获取来源；Framework Core 不解析具体编程语言源码。

## 3. Test Specification 绑定

普通 Case：

```yaml
operation_id: createOrder
```

复杂 Workflow：

```yaml
operations:
  - createOrder
  - payOrder
  - refundOrder
```

## 4. 生成 Coverage

```bash
python -m coverage_engine.cli --env <ENV_NAME>
```

可选：

```bash
python -m coverage_engine.cli \
  --env <ENV_NAME> \
  --env-file <PRIVATE_OVERRIDE_YAML> \
  --output <OUTPUT_DIR>
```

默认输出：

```text
reports/coverage/<ENV_NAME>/contract.json
reports/coverage/<ENV_NAME>/coverage-index.json
reports/coverage/<ENV_NAME>/coverage-gap.json
```

## 5. Coverage Gap 的边界

Stage 5 只报告确定事实：

- external scope 中没有任何 Case 的 Operation；
- Case/Workflow 指向不存在 Operation；
- 没有任何 Operation 绑定的 Case；
- 已观察到的 risk/level/case/workflow 关系。

Stage 5 **不会**凭空生成 `missing_risks`。缺什么风险测试需要未来 Risk Policy 或 Stage 7 AI Test Design 提供依据。

## 6. 微服务 Coverage Scope

Contract 可以保留：

```text
external
external_gateway
external_direct
internal_service
page_internal
```

默认 Coverage 分母只包含 external 类 Operation，避免 Gateway/Admin/内部服务镜像 API 被重复计算。

## 7. Shortlink 当前真实样例

Shortlink 后端源码清单共识别 43 个 Mapping，其中默认 External API Surface 为 27 个。

当前 18 条 Test Specification / Workflow 自动映射结果：

```text
covered operations : 8
external operations: 27
coverage           : 29.63%
untested operations: 19
unknown bindings   : 0
unbound cases      : 0
```

这只是当前代表性测试资产的覆盖现状，不把“29.63%”包装成测试质量目标。Stage 5 的价值是让缺口变得可见和可计算。
