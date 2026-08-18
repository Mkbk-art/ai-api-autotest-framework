# Stage 4.5 完整异常/边界真实用例设计

## 目标

在 Stage 4 已由用户 Windows 真实验证的 6 条 Happy Path Smoke 之外，一次性补齐 6 条高价值 Core 异常/边界用例，并保持所有网络请求继续经过 `YAML -> ApiRunner -> RequestClient -> Assertions` 主链。Stage 4.5 不扩张为全量业务测试，只覆盖能代表鉴权、业务输入、资源不存在和状态迁移四类测试能力的场景。

## 用例范围

1. E1 错误密码登录：真实 username + 动态错误密码，HTTP 200 但业务 code 非 0，且不能返回 token。
2. E2 Group 缺 token：不执行登录 fixture，只发 username，由 Gateway 返回 HTTP 401。
3. E3 Create 缺 token：请求体保持完整合法，只删除 token，验证 Create 路由同样被 Gateway 401 拦截。
4. E4 Create 非法 originUrl：正常 Login/Group 后只把 `originUrl` 改成 `not-a-valid-url`，验证业务失败且不能生成 `fullShortUrl`。
5. E5 不存在 shortUri：直接访问 Project 的随机不存在短码，关闭自动重定向，验证第一跳 302 到 `/page/notfound`。
6. E6 回收后再次访问：创建真实短链 -> `recycle-bin/save` -> 再访问同一 shortUri -> 302 到 `/page/notfound` -> finally `recycle-bin/remove`。

## 架构约束

- 6 条异常用例统一标记 `core`，原 6 条成功主链继续只属于 `smoke`。
- 真实 shortlink 总 Test Item 固定为 12：Smoke 6 + Core 6。
- E1 错误密码不能读取、修改或拼接真实 `SHORTLINK_TEST_PASSWORD`。
- E2/E3 不使用登录 fixture，保证缺 token 是唯一鉴权变量。
- E4 使用正常登录与真实 gid，只改变 originUrl；当前 Project 会在创建过程把非法 URL 作为未捕获异常转换为非零业务失败 Result，因此不把具体错误码写死。
- E5 不创建测试数据；随机长 shortUri 降低与真实数据碰撞概率。
- E6 必须用真实 `recycle-bin/save/remove`，不直接修改 MySQL；save 与 remove 拆成两个 helper，以便在回收站中间态执行 Redirect。
- Servlet `sendRedirect("/page/notfound")` 可能以相对或绝对 `Location` 返回，因此新增 `header_contains`，只要求 Location 包含 `/page/notfound`。
- 所有新增/修改 Python、YAML 继续满足高密度中文注释规范。

## 数据流

```text
E1: auth_invalid.yaml -> invalid_password() -> Login -> HTTP 200 + code != 0
E2: group_unauthorized.yaml -> Gateway -> HTTP 401
E3: create_unauthorized.yaml -> Gateway -> HTTP 401
E4: Login -> Group -> create_invalid_origin.yaml -> Project -> HTTP 200 + code != 0
E5: redirect_notfound.yaml -> Project:8001/random shortUri -> 302 /page/notfound
E6: Login -> Group -> create.yaml -> recycle-bin/save -> redirect_recycled.yaml
    -> 302 /page/notfound -> finally recycle-bin/remove
```

## 验收边界

离线沙箱只证明 DSL、请求展开、断言、fixture/helper、collection 分层、注释质量和回归未破坏；不能把 Fake Response 测试写成真实 SaaS 通过。最终真实验收必须由用户 Windows 本机执行：

```bash
python run.py --env shortlink-local --level core --collect-only
python run.py --env shortlink-local --level core
```

只有真实得到 6 条 Core 全部通过后，Stage 4.5 才升级为“真实环境已完成”，随后进入 Stage 5 MySQL + Redis 深层一致性校验。
