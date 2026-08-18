# Stage 4 V2.8 Redirect YAML 主链纠正证据

## 纠正目标

上一版 Redirect 的 YAML 虽然声明了 URL/method，但测试实际通过 `request_shortlink_redirect()` helper 自行拼 URL 并发请求，导致 YAML 只承担断言配置，不符合框架“YAML 驱动请求”的主线设计。

## 本版纠正

```text
redirect.yaml
  -> absolute URL: http://nurl.ink:8001/${short_uri}
  -> method: GET
  -> request_options.allow_redirects=false
  -> validation: 302 + Location
        ↓
ApiRunner
  -> VariableContext 替换 short_uri
  -> 识别绝对 URL，不拼 Gateway host
  -> 受控透传 allow_redirects
        ↓
RequestClient
        ↓
Requests
        ↓
Assertions
```

`request_shortlink_redirect()` 已删除。Statistics 触发访问也复用 `redirect.yaml + ApiRunner.run()`。

## TDD 证据

修改前新增的绝对 URL/request_options 单元测试按预期失败：旧 `ApiRunner` 把 Gateway host 与绝对 URL 直接拼接，并且无法透传 `allow_redirects`。

修改后相关 3 条定向测试通过：

```text
3 passed
```

完整离线验证：

```text
framework tests: 83 passed
default offline full suite: 89 passed
shortlink-local collect-only: 6 tests
compileall: PASS
```

真实 Redirect/Statistics/Cleanup 仍等待用户 Windows 本机 smoke 验收，不以沙箱结果冒充真实环境通过。
