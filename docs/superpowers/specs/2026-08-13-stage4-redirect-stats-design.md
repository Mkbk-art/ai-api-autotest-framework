# Stage 4 Redirect / Statistics / Cleanup Design

## Goal

在用户已经真实验证 `Login -> Group -> Create -> Page` 为 `4 passed` 的基础上，把 Stage 4 扩展为：

```text
Create(GitHub)
-> Redirect(302)
-> Statistics(Redis Stream 最终一致性)
-> RecycleBin Cleanup
```

同时彻底收紧凭据 traceback 暴露风险，并按用户要求提升 Stage 4 Python/YAML 的中文注释密度。

## Confirmed Baseline

- 用户 Windows 后端系统、Nacos、Gateway、Admin、Project 可正常启动。
- Auth + Group + Create + Page 已在用户本机真实环境验证为 `4 passed`。
- Windows hosts 已配置：

```text
127.0.0.1 nurl.ink
```

- 创建短链接原始地址统一使用：

```text
https://github.com/
```

## Redirect Design

### Why IP and domain are not fully equivalent

`nurl.ink` 通过 hosts 最终解析到 `127.0.0.1`，所以 TCP 连接目标相同；但 HTTP Host/serverName 仍来自 URL 主机名。短链接 Project 会据此重建 `fullShortUrl`，而数据库保存的是 `nurl.ink:8001/<short_uri>`。

因此：

```text
http://127.0.0.1:8001/abc
```

和：

```text
http://nurl.ink:8001/abc
```

虽然都到达本机 8001，但对业务字符串身份并不等价。

### Chosen approach

用户已经配置 hosts，因此直接请求：

```text
GET http://nurl.ink:8001/<short_uri>
allow_redirects=False
```

不再使用旧备选方案：

```text
GET http://127.0.0.1:8001/<short_uri>
Host: nurl.ink:8001
```

真实断言：

```text
status_code == 302
Location == https://github.com/
```

## Statistics Design

Redirect 先触发访问统计事件。Java 侧采用 Redis Stream 异步消费，因此测试不能访问后立即只查一次，也不采用固定长 `sleep`。

采用有界轮询：

```text
interval = 1 second
timeout = 15 seconds
```

每次通过 Gateway/Admin 调用：

```text
GET /api/short-link/admin/v1/stats
```

参数：

```text
fullShortUrl
gid
enableStatus=0
startDate=<当天 00:00:00>
endDate=<当天 23:59:59>
```

成功条件：

```text
code == "0"
data != null
pv >= 1
uv >= 1
uip >= 1
```

HTTP/业务错误立即失败；只有业务成功但统计尚未可见时继续轮询。

## Cleanup Design

真实源码的删除路径是回收站状态机，不直接操作数据库：

```text
recycle-bin/save
-> recycle-bin/remove
```

请求体：

```json
{
  "gid": "<gid>",
  "fullShortUrl": "nurl.ink:8001/<short_uri>"
}
```

- Page / Redirect / Statistics 使用 `shortlink_created_context` yield fixture；Teardown 自动清理。
- Create 测试由测试函数本身创建链接，因此使用 `try/finally` 调用同一 cleanup helper。
- Cleanup 失败应显式报告，不能静默假装测试数据已删除。

## Credential Safety

`ShortlinkCredentials` 使用：

```python
password: str = field(repr=False)
```

`authenticate_shortlink()` 接收整个 credentials 对象，而不是独立 `password` 形参，以减少 Pytest traceback 参数渲染造成的密码泄漏。

## Comment Standard

本批次所有 Stage 4 业务 Python/YAML 必须：

- Python 有模块用途 docstring；
- fixture/helper/test 函数有 docstring；
- import、关键状态、请求构造、循环、断言、Teardown 解释“做什么/为什么”；
- YAML 的 URL/method/header/json/params/extract/validation 逐项解释；
- 避免无意义逐字复述代码。

新增自动化守护：

```text
tests/unit/test_stage4_comment_quality.py
```

## Isolation

所有真实业务测试继续保持 function-scope 独立：

```text
credentials
-> authenticated_context
-> group_context
-> created_context
-> test
-> teardown cleanup
```

任何一条测试都不依赖另一条测试函数先运行。

## Acceptance Criteria

沙箱离线验收：

1. Stage 4 创建 URL 固定为 GitHub。
2. Redirect helper 精确访问 `http://nurl.ink:8001/<short_uri>`，并关闭自动重定向。
3. Stats 单元测试覆盖即时成功、延迟成功和超时。
4. Cleanup 单元测试证明严格执行 save -> remove。
5. 凭据 repr/helper 签名不直接暴露 password。
6. Stage 4 Python/YAML 注释质量守护通过。
7. Mock 和框架全量回归不受影响。
8. `shortlink-local --collect-only` 只收集 6 条真实用例。

用户 Windows 真实验收：

1. 六条 smoke 全部通过。
2. Redirect 返回 302 + GitHub Location。
3. Statistics 在 15 秒内观察到 PV/UV/UIP。
4. Teardown Cleanup 不产生错误，自动化测试短链通过真实回收站流程被清理。
