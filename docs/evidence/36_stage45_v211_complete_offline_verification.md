# Stage 4.5 V2.11 六条异常/边界完整离线验证

## 版本边界

本证据对应 Stage 4.5 完整候选版。Stage 4 的 6 条 Happy Path Smoke 已由用户 Windows 真实验证为 `6 passed in 9.65s`；本文件只记录六条新增 Core 的代码、契约和离线回归，不把沙箱 Fake Response 描述成真实 SaaS 通过。

Stage 4.5 固定为：

```text
E1 错误密码登录
E2 Group 缺 token
E3 Create 缺 token
E4 Create 非法 originUrl
E5 不存在 shortUri
E6 回收后再次访问
```

## TDD / 契约验证

- E1：先以缺失 `DebugTalk.invalid_password()` 得到 RED，再实现与真实密码完全解耦的动态错误密码生成。
- E1/E2：先以缺失 `auth_invalid.yaml` / `group_unauthorized.yaml` 得到 RED，再建立 YAML + ApiRunner 异常链路。
- E3～E6：先增加 YAML/业务行为契约和 `header_contains` 断言测试，再实现 Create 缺 token、非法 URL、不存在短码、回收状态 Redirect 以及回收站 save/remove 独立 helper。
- Collection：新增四条后，旧“真实业务 8 条 / Core 2 条”守护按预期失效，随后更新为总 12 条、Smoke 6、Core 6。

## Framework Tests

命令：

```bash
python -m pytest tests -q
```

结果：

```text
107 passed
```

## 默认离线全量

命令：

```bash
python -m pytest -q
```

结果：

```text
113 passed
```

默认 `test` 环境只执行受控 Mock Demo；`testcases/conftest.py` 会排除真实 shortlink 目录，因此该结果不会向用户本地 SaaS 发请求。

## 真实环境 Collection 分层

Smoke：

```bash
python run.py --env shortlink-local --level smoke --collect-only
```

结果：

```text
collected 12 items / 6 deselected / 6 selected
6/12 tests collected
```

Core：

```bash
python run.py --env shortlink-local --level core --collect-only
```

结果：

```text
collected 12 items / 6 deselected / 6 selected
6/12 tests collected
```

Core 只包含：

```text
test_auth_invalid.py
test_group_unauthorized.py
test_create_unauthorized.py
test_create_invalid_origin.py
test_redirect_notfound.py
test_redirect_recycled.py
```

## Compile / 静态守护

```text
compileall: PASS
Stage 4 Python/YAML 中文注释质量: PASS
真实项目目录不存在 .env / 私钥文件: PASS
已知明文测试密码未写入源码或文档: PASS
runtime testcases/core/utils/config 不存在固定 https://github.com/: PASS
DEFAULT_ORIGIN_URL 不存在: PASS
```

`SHORTLINK_TEST_USERNAME` / `SHORTLINK_TEST_PASSWORD` 只作为环境变量名出现，不保存真实值。

## 六条业务契约为什么有区分度

- E1 是 **Admin 业务层失败**：HTTP 200 不等于业务成功。
- E2/E3 是 **Gateway 鉴权失败**：缺 token 在业务 Controller 前返回 HTTP 401。
- E4 是 **业务输入异常**：鉴权与 gid 都正常，只改变 originUrl，失败响应不能生成 short link。
- E5 是 **资源不存在**：不依赖登录和历史数据，验证 Project 的 notfound 第一跳。
- E6 是 **状态迁移边界**：真实创建后进入回收站，再验证同一资源不可访问，并在 finally 中完成最终清理。

## 真实环境下一验收点

用户 Windows 本机只需要一次运行完整 Core：

```bash
python run.py --env shortlink-local --level core --collect-only
python run.py --env shortlink-local --level core
```

只有得到六条真实 Core 全部 PASS 后，Stage 4.5 才能标记为“真实环境完成”。随后项目直接进入 Stage 5 ShardingSphere MySQL 物理分表和 Redis 深层一致性校验，不再继续扩张短链接业务用例数量。
