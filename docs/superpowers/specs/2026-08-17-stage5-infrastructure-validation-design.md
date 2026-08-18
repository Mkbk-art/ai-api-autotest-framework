# Stage 5 Infrastructure Validation Design

## Goal

在不改变 Stage 4/4.5 真实业务主链的前提下，新增 MySQL 与 Redis 的底层状态校验，形成 API → DB/Redis 的完整测试证据，并同时把本地短链接测试账号改为 YAML 配置。

## Scope

Stage 5 新增 6 条 `regression` 真实测试：

1. MySQL：Create 后数据必须落到由 ShardingSphere HASH_MOD 决定的 `t_link_<0..15>` 和 `t_link_goto_<0..15>` 物理分表，并校验关键业务字段。
2. MySQL：Recycle Save/Remove 后验证 `enable_status: 0 -> 1`、`del_flag: 0 -> 1`、`del_time: 0 -> timestamp`。
3. MySQL：Redirect + Stats 最终一致后，验证 `t_link_access_stats` 已持久化 PV/UV/UIP。
4. Redis：Login 后验证 `short-link:login:<username>` Hash 中存在当前 token，且 TTL 在有效范围内。
5. Redis：Create 后验证 `short-link:goto:<fullShortUrl>` 缓存等于 originUrl；移入回收站后该缓存被删除。
6. Redis：Redirect 后验证 `short-link:stats:uv:<fullShortUrl>` 与 `short-link:stats:uip:<fullShortUrl>` Set 均至少有一个成员。

## Stage 4.5 Fix Included

`create_shortlink_from_yaml()` 作为 Page/Redirect/Stats/E6/Stage5 的测试数据准备入口，对源码确认的 Sentinel 临时限流业务码 `B100000` 做有界重试；仅重试该已知瞬时状态，其他 HTTP/业务错误立即失败。正常 `test_create.py` 仍由 YAML → ApiRunner 严格单次执行，不隐藏真实 Create 缺陷。

## Configuration

`config/env.shortlink-local.yaml` 成为本地真实环境单一配置入口，包含：

- `shortlink.username/password`
- `shortlink.create_retry.max_attempts/interval_seconds`
- `mysql.host/port/database/username/password/charset`
- `redis.host/port/db/password`

YAML 用例通过 `${config(shortlink,username)}` / `${config(shortlink,password)}` 读取账号。用户只需修改 YAML，不再需要终端 `export SHORTLINK_TEST_*`。

## Sharding Algorithm

Java 项目使用 Apache ShardingSphere 5.3.2 `HASH_MOD`，分片数量 16。Python 端复制 Java `String.hashCode()` 语义后执行 `abs(hash) % 16`：

- `t_link` 使用 `gid`
- `t_link_goto` 使用 `full_short_url`

只允许函数生成 `t_link_0..15` / `t_link_goto_0..15` 表名，不接受外部任意表名，避免 SQL 标识符注入。

## Isolation and Cleanup

Stage 5 仍通过业务 API 创建/回收测试短链；数据库仅做只读断言，不直接写业务表。任何手工管理生命周期的测试都使用 `try/finally` 完成回收站清理。

## Markers

- Stage 4 Smoke: 6
- Stage 4.5 Core: 6
- Stage 5 Regression: 6

`shortlink-local --level regression` 只选中 Stage 5 的 6 条真实基础设施测试。
