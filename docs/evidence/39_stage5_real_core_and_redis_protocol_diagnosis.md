# Stage 5 真实 Core 与 Redis 协议诊断证据

## 用户真实运行

- Core：`6 passed, 12 deselected in 5.58s`，Stage 4.5 正式真实通过。
- Regression：`3 passed, 3 failed, 12 deselected`。
- 三条 MySQL Regression 真实通过。
- 三条 Redis Regression 全部在连接握手阶段失败，统一错误为 `unknown command HELLO ... 3`。

## 根因

V3.1 使用 `redis>=5.0` 且未显式指定 RESP protocol；redis-py 8 将默认线协议改为 RESP3，因此连接时发送 `HELLO 3`。当前本地 Redis/兼容代理不支持该命令，断言尚未真正读取 Redis Key。

## V3.1.1 修复

- `RedisSettings.protocol`：默认 2。
- `data_sources.redis.<source>.protocol`：项目环境 YAML 可覆盖。
- `RedisClient` 创建 Fake/真实 client 时显式透传 protocol。
- `env.shortlink-local.yaml` 显式 `protocol: 2`；环境模板同步说明。
- `redis>=5.0,<9` 并加入 constraints。
- 新增 TDD 回归：默认 RESP2，可由 YAML 显式选择 RESP3。

## 状态边界

V3.1.1 仅证明协议兼容修复和离线回归完成。三条 Redis 业务断言必须由用户再次执行 `--level regression` 后才能标记为真实通过。
