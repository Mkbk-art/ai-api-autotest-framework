# Stage 4 V2.9 Create 单一 originUrl 数据源验证

## 纠正目标

此前 `create.yaml` 与 Python `DEFAULT_ORIGIN_URL` 同时维护原始链接，导致修改 YAML 后，Page/Redirect/Statistics 的 fixture 前置 Create 仍可能使用 Python 固定站点。V2.9 将 `testcases/yaml/shortlink/create.yaml` 设为唯一原始 URL 配置源。

## 当前执行链

```text
create.yaml json.originUrl
  -> test_create.py
  -> shortlink_created_context
       -> create_shortlink_from_yaml()
       -> ApiRunner.run(create.yaml)
       -> Create response originUrl
       -> VariableContext origin_url
  -> Page 对比 created_context.origin_url
  -> Redirect header_eq Location == ${origin_url}
  -> Statistics 复用相同 Redirect YAML
```

## TDD 证据

先新增两条失败测试：

1. 前置 Create 必须读取 create.yaml，而不是 Python 固定站点；
2. redirect.yaml 的 Location 必须使用 `${origin_url}`。

修改前两条均失败；完成实现后两条均通过。

## 离线验证

- `pytest -q tests -o log_cli=false`: 83 passed
- `pytest -q -o log_cli=false`: 89 passed
- `python -m compileall -q core utils testcases tests`: PASS
- `shortlink-local --collect-only`: 6 tests collected
- active `testcases/` 中不存在 `DEFAULT_ORIGIN_URL` 或固定 `github.com` 配置。

## 真实环境状态

该版本只纠正测试数据单一来源。之前 `/stats` 返回 `B000001` 的真实业务问题仍需继续定位，不能把它直接归因于本次重复配置问题。
