# Stage 4 用户 Windows 真实 Smoke：6 Passed

## 证据边界

本文件记录用户在真实 Windows + 本地短链接 SaaS 环境中的运行结果。为避免泄露凭据，
只保留命令、用例链路、HTTP 状态和最终 Pytest 结果，不复制 username/password/token 值。

## 执行命令

```bash
python run.py --env shortlink-local --level smoke
```

## 实际收集

```text
6 items
```

六条真实 Smoke：

1. Login；
2. Create；
3. Group；
4. Page；
5. Redirect；
6. Statistics。

Cleanup 不单独占 Test Item，而是在 Create 的 `finally` 和 Page/Redirect/Statistics 的
fixture Teardown 中通过真实 `recycle-bin/save -> recycle-bin/remove` 执行。

## 关键真实链路证据

- Login 通过 Gateway 返回 HTTP 200；
- Create 返回 HTTP 200，并在测试结束后成功调用两步回收站清理；
- Group 返回 HTTP 200；
- Page 返回 HTTP 200，并确认本测试刚创建的短链；
- Redirect 直接访问 `http://nurl.ink:8001/<short_uri>`，第一跳返回 HTTP 302；
- Statistics 在 Redirect 后查询 `/stats`：第一次请求返回 HTTP 200，约 1 秒后再次轮询，
  第二次满足 PV/UV/UIP 条件后测试通过，证明有界轮询在真实 Redis Stream 异步链路中生效；
- Page/Redirect/Statistics 的 Teardown 均成功执行回收站 save/remove。

## 最终结果

```text
6 passed in 9.65s
```

因此，从本证据开始，Stage 4 的完整 Happy Path E2E 可以标记为**用户真实环境已验证**。
Stage 4.5 新增的异常/边界用例必须单独获得真实运行结果后才能标记通过。
