# Stage 4 真实短链接 SaaS 接入：Auth / Group / Create / Page / Redirect / Stats / Cleanup

## 1. 模块作用

本文件记录 Stage 4 从 Mock 验证切换到真实短链接 SaaS 的接口契约、fixture 依赖、执行方式、清理策略和证据边界。用户已在 Windows 本机完整执行六条真实 Smoke，最终为 `6 passed in 9.65s`；因此 Login/Group/Create/Page/Redirect/Statistics 以及随测试执行的 Cleanup 均已获得真实环境证据。当前项目进入 Stage 4.5，开始补充异常/边界用例。

## 2. 当前真实主链路

```text
Gateway :8000
  -> Login -> token
  -> Group -> gid
  -> Create(originUrl 由 create.yaml 唯一配置)
  -> Page -> fullShortUrl + enableStatus=0

Project :8001
  -> redirect.yaml 声明 http://nurl.ink:8001/${short_uri}
  -> ApiRunner 从 VariableContext 替换 short_uri
  -> request_options.allow_redirects=false
  -> RequestClient 发 GET
  -> 302 + Location=${origin_url}

Gateway/Admin :8000
  -> GET /api/short-link/admin/v1/stats
  -> fullShortUrl + gid + enableStatus=0
  -> Redis Stream 最终一致性轮询
  -> pv/uv/uip >= 1

Fixture Teardown
  -> POST /api/short-link/admin/v1/recycle-bin/save
  -> POST /api/short-link/admin/v1/recycle-bin/remove
```

## 3. 为什么 `127.0.0.1:8001` 和 `nurl.ink:8001` 不能在 HTTP 业务上简单视为相同

用户 Windows hosts 已配置：

```text
127.0.0.1 nurl.ink
```

因此从 TCP 连接角度：

```text
http://nurl.ink:8001
        ↓ hosts 解析
127.0.0.1:8001
```

和直接访问 `http://127.0.0.1:8001` 最终都会连接同一个本机 Project 端口。但 HTTP 请求仍保留 URL 中的主机名：

```text
GET http://127.0.0.1:8001/abc
Host: 127.0.0.1:8001

GET http://nurl.ink:8001/abc
Host: nurl.ink:8001
```

短链接 Redirect Controller 会使用请求中的 serverName/port 重建 `fullShortUrl`。数据库逻辑身份是：

```text
nurl.ink:8001/abc
```

所以直接访问 IP 可能让后端重建成：

```text
127.0.0.1:8001/abc
```

虽然网络连接到了同一个 Java 服务，但业务字符串身份不同。此前备选方案 A 是“URL 使用 127.0.0.1，同时手工设置 `Host: nurl.ink:8001`”，用于不修改 hosts 的机器。现在用户已经配置 hosts，因此本版本采用更接近真实浏览器访问的方式：

```text
GET http://nurl.ink:8001/<short_uri>
allow_redirects=False
```

不再手工添加 Host Header。

## 4. 创建与 URL 语义

Stage 4 在 V2.9 已删除 Python 固定 `DEFAULT_ORIGIN_URL`，现在 `create.yaml` 是原始 URL 的
唯一配置源。当前本地用例配置为：

```text
originUrl = https://www.doubao.com/
```

后续如果更换测试站点，只修改 `create.yaml`，Page/Redirect/Statistics 的 fixture 前置 Create
会自动同步。创建响应统一保存：

```text
short_url      = http://nurl.ink:8001/<short_uri>
full_short_url = nurl.ink:8001/<short_uri>
short_uri      = <short_uri>
origin_url     = <本次 Create 响应中的 originUrl>
gid            = <group id>
```

其中：

- `short_url`：用户可直接访问的 URL；
- `full_short_url`：Page / Stats / RecycleBin / DB 使用的不带 scheme 逻辑身份；
- `short_uri`：Project 根路由 `/{short-uri}` 使用的短码；
- `origin_url`：本次真实创建回显的原始地址，Redirect 使用它动态断言 Location。

## 5. Redirect 为什么关闭自动跟随，以及为什么现在由 YAML 真正驱动

Requests 默认会自动跟随 302。如果不关闭，短链接服务先返回 `302 + Location=<origin_url>` 后，Requests 会继续访问外部原始站点，测试最终拿到的可能是目标站点的 200，而不是短链接系统第一跳。因此 `redirect.yaml` 现在直接声明：

```yaml
baseInfo:
  url: http://nurl.ink:8001/${short_uri}
  method: GET

testCase:
  - request_options:
      allow_redirects: false
    validation:
      - status_code: 302
      - header_eq: [Location, "${origin_url}"]
```

执行链为：

```text
shortlink_created_context
  -> 创建短链并写入 short_uri
  -> yield 给测试函数

redirect.yaml
  -> ApiRunner._resolve_url()
  -> ${short_uri} 从 VariableContext 替换
  -> 得到 http://nurl.ink:8001/<真实短码>
  -> ApiRunner._request_options() 读取 allow_redirects=false
  -> RequestClient.run()
  -> requests.Session.request(..., allow_redirects=False)
  -> 保留第一跳 302
  -> Assertions 验证 status_code 与 Location
```

这个版本删除了原先 `request_shortlink_redirect()` 专用网络 helper。Redirect 不再“YAML 只写断言、Python 自己拼 URL”，而是重新回到框架设计目标：YAML 描述请求，ApiRunner 统一编排，RequestClient 作为唯一网络层发送请求。

## 6. Stats 为什么使用轮询

Redirect 请求产生访问统计后，Java 服务先写 Redis Stream，再由 Consumer 异步落库。因此“访问后立刻查询一次”存在最终一致性竞争。本版本使用：

```text
poll interval = 1 second
maximum timeout = 15 seconds
```

每次 Stats 查询包含：

```text
fullShortUrl
gid
enableStatus=0
startDate=<当天 00:00:00>
endDate=<当天 23:59:59>
```

只有业务码为 `"0"`、`data` 非空且 `pv/uv/uip >= 1` 才返回成功。HTTP 错误或非零业务码立即失败；只有“统计尚未可见”才继续轮询。超时错误保留最后一次经过脱敏的 payload，便于继续定位 Redis Stream/Consumer 问题。

## 7. Cleanup 为什么走回收站业务接口

真实源码没有简单 DELETE API。回收站状态机要求：

```text
正常短链 enableStatus=0
        ↓ recycle-bin/save
回收站 enableStatus=1
        ↓ recycle-bin/remove
逻辑删除 delFlag=1 + delTime
```

因此自动化清理不直接操作 MySQL，而是依次调用：

```text
POST /api/short-link/admin/v1/recycle-bin/save
POST /api/short-link/admin/v1/recycle-bin/remove
```

请求体均为：

```json
{
  "gid": "<gid>",
  "fullShortUrl": "nurl.ink:8001/<short_uri>"
}
```

Page/Redirect/Statistics 使用 `shortlink_created_context` yield fixture：测试 Setup 创建短链，测试 Call 执行业务断言，Teardown 自动清理。Create 测试由于短链由测试函数本身通过 YAML 创建，因此使用 `try/finally` 保证创建成功后尽量清理。

## 8. Fixture 独立性

真实测试仍不依赖另一个测试函数先运行：

```text
shortlink_credentials
  -> shortlink_authenticated_context
      -> shortlink_group_context
          -> shortlink_created_context
```

`shortlink_created_context` 默认 function scope，所以 Page、Redirect、Statistics 都会得到自己的登录态、gid 和测试短链。fixture 在同一测试中可复用依赖，但不同测试之间不会共享 token 或短码。

## 9. 凭据安全与本地 YAML 配置

从 Stage 5 起，真实短链接账号不再要求用户每次在 Git Bash/PowerShell 中导出环境变量。
账号统一从 `config/env.shortlink-local.yaml` 的 `shortlink.username/password` 读取；登录 YAML 使用
`${config(shortlink,username)}` / `${config(shortlink,password)}`，fixture 也读取同一份
`runtime_config`，因此本地修改 YAML 后下一次运行立即生效。

`ShortlinkCredentials.password` 使用 `repr=False`；`authenticate_shortlink()` 接收整个凭据对象，不再把 password 作为独立函数参数。这样 Pytest setup/helper traceback 展示参数时只会看到类似：

```text
ShortlinkCredentials(username='admin')
```

Token 只写入当前测试 VariableContext 和真实请求 Header，不作为 fixture 返回值公开。

## 10. 注释规范

用户要求 Stage 4 后续交付代码必须便于学习和面试复盘。本版本对 `testcases/shortlink/*.py` 和 `testcases/yaml/shortlink/*.yaml` 全面补充高密度中文解释：

- Python 模块顶部说明用途、边界和数据流；
- import、fixture、关键变量、请求构造、循环、断言、清理都解释作用或原因；
- YAML 对 URL、method、header、params/json、extract、validation 字段逐项说明；
- 不使用“给变量赋值”这类纯重复代码文本的无意义注释。

同时新增 `tests/unit/test_stage4_comment_quality.py`，自动检查真实业务 Python 文件存在模块 docstring，并守护 Python/YAML 的最低解释性注释密度，防止后续版本再次遗漏说明。

## 11. Stage 4 真实验收结果

用户 Windows 本机真实执行：

```bash
python run.py --env shortlink-local --level smoke
```

六条 Smoke 全部通过：

```text
Auth        ✅ 真实验证
Group       ✅ 真实验证
Create      ✅ 真实验证
Page        ✅ 真实验证
Redirect    ✅ 真实 302 验证
Statistics  ✅ 真实 Redis Stream 最终一致性轮询验证
Cleanup     ✅ 真实 Teardown save/remove 验证

6 passed in 9.65s
```

Statistics 的真实日志中，Redirect 后先查询一次 `/stats`，约 1 秒后再次查询并满足
PV/UV/UIP 条件，这证明轮询设计确实处理了真实异步链路，而不是固定 sleep 或离线假数据。

## 12. Stage 4.5 完整六条异常 / 边界用例

Stage 4.5 只补 6 条高价值 `core`，不继续扩张已经真实通过的 6 条 Smoke：

1. **错误密码登录**：真实 username + `${invalid_password()}`，期望 HTTP 200、业务 code 非 0、无 token；
2. **Group 缺 token**：不执行登录 fixture，只发送 username，期望 Gateway HTTP 401；
3. **Create 缺 token**：请求体保持合法完整，只删除 token，期望 Gateway HTTP 401；
4. **Create 非法 originUrl**：正常 Login/Group 后只把 URL 改成 `not-a-valid-url`，期望 HTTP 200 + 非零业务 code，且不生成 fullShortUrl；
5. **不存在 shortUri**：直接访问 Project:8001 的随机不存在短码，关闭自动重定向，期望第一跳 302 到 `/page/notfound`；
6. **回收后再次访问**：Create -> `recycle-bin/save` -> 访问同一 shortUri -> 302 notfound -> finally `recycle-bin/remove`。

六条异常仍统一执行：

```text
YAML -> ApiRunner -> RequestClient -> Assertions
```

其中：

- `${invalid_password()}` 只生成测试前缀 + 随机后缀，不读取 `runtime_config` 中的真实密码；
- E2/E3 不使用登录 fixture，避免测试框架把 token 自动补回；
- E4 使用真实 token/gid，只让 originUrl 成为唯一异常变量；
- E5 使用随机 shortUri，不依赖历史数据库数据；
- E6 只调用真实回收站业务接口，不直接写数据库；
- Project 源码使用 `sendRedirect("/page/notfound")`，Servlet 可能返回相对或绝对 Location，因此断言引擎新增 `header_contains`，要求 Location 包含 `/page/notfound`。

真实验收命令：

```bash
python run.py --env shortlink-local --level core --collect-only
python run.py --env shortlink-local --level core
```

预期 collection 为真实业务总计 12 条，其中 6 条 Smoke deselected、6 条 Core selected。在用户本机得到真实结果前，Stage 4.5 六条只能标记为“已编码 + 离线验证”，不能提前写成真实通过。

## 13. Stage 4.5 最新真实结果与 Sentinel 修复

用户最近一次 Windows 真实 `--level core` 结果为：

```text
5 passed, 1 failed, 6 deselected
```

前五条 Core 均真实通过。唯一失败是 E6，但堆栈表明它在 `create_shortlink_from_yaml()` 的
前置 Create 阶段就收到 HTTP 200 + 业务码 `B100000`，还没有进入 `recycle-bin/save`、
Redirect 或 remove。Java 源码中的 Sentinel Create 资源 QPS=1，与 E4 Create 和 E6 前置
Create 在同一秒连续执行的时间关系完全一致。

Stage 5 合并修复采用窄策略：

```text
正常 test_create.py：仍单次严格请求，不自动重试
测试数据准备型 Create：仅 B100000 可以按 YAML 配置有界等待/重试
其他 HTTP / 业务错误：立即失败
```

重试参数位于 `env.shortlink-local.yaml -> shortlink.create_retry`，默认总尝试 3 次、间隔
1.1 秒。这样既跨过 QPS 窗口，又不会把未知业务失败吞掉。

Stage 4.5 仍需用户用本版本再次执行 `--level core` 才能正式记为 6/6 真实通过。
