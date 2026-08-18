# Stage 4.5 鉴权异常真实用例设计

## 目标

在 Stage 4 已真实验证的 6 条 Happy Path Smoke 基础上，新增第一批两条真实异常用例：

1. 登录密码错误：请求能够到达 Admin，但业务层返回失败；
2. Group 缺少 token：请求在 Gateway 鉴权层被拒绝并返回 HTTP 401。

本批次只覆盖两种不同层级的鉴权失败，不扩展到 Create 参数异常、无效 shortUri 或回收状态回归。

## 设计原则

- 真实业务异常仍通过 `YAML -> ApiRunner -> RequestClient -> Assertions` 主链执行；
- 不修改正常 Smoke 的账号环境变量，不让异常用例污染成功 fixture；
- 错误密码由测试动态生成，绝不读取、拼接、打印真实密码；
- Group 缺 token 用例显式只发送 `username`，不先登录、不创建 token；
- 异常用例使用 `core` marker，不加入 `smoke`，保证现有 6 条 Smoke 数量和语义不变；
- YAML 与 Python 均保持高密度中文注释；
- 离线测试验证请求契约和 YAML 断言，不伪造“真实环境通过”；
- 真实环境验收由用户 Windows 本地执行后再更新状态。

## 用例 1：错误密码登录

请求：

```text
POST /api/short-link/admin/v1/user/login
Content-Type: application/json
username = ${env(SHORTLINK_TEST_USERNAME)}
password = ${invalid_password()}
```

`invalid_password()` 生成带固定测试前缀和随机后缀的错误密码，不读取 `SHORTLINK_TEST_PASSWORD`。

根据 Admin 源码，用户名+密码查询不到用户时抛 `ClientException("用户不存在")`；全局异常处理器返回业务失败结果。因此断言：

- HTTP 200；
- `$.code != "0"`；
- `$.data.token` 不存在。

不把具体错误文案作为强契约，避免测试与展示文案过度耦合。

## 用例 2：Group 缺少 token

请求：

```text
GET /api/short-link/admin/v1/group
username = ${env(SHORTLINK_TEST_USERNAME)}
token = 不发送
```

根据 Gateway `TokenValidateGatewayFilterFactory`，非白名单接口缺少 username/token 或 Redis 登录态时直接返回 HTTP 401：

```json
{
  "status": 401,
  "message": "Token validation error"
}
```

因此断言：

- HTTP 401；
- `$.status == 401`；
- `$.message == "Token validation error"`。

该用例不依赖登录 fixture，证明请求确实被 Gateway 拦截，而不是 Admin 业务层失败。

## 文件边界

新增：

- `testcases/yaml/shortlink/auth_invalid.yaml`：错误密码登录契约；
- `testcases/yaml/shortlink/group_unauthorized.yaml`：缺 token Gateway 契约；
- `testcases/shortlink/test_auth_invalid.py`：错误密码真实 core 用例；
- `testcases/shortlink/test_group_unauthorized.py`：缺 token 真实 core 用例；
- `docs/evidence/34_stage4_real_smoke_6_passed.md`：用户真实 6 passed 证据；
- `docs/evidence/35_stage45_v210_offline_verification.md`：本批次离线验证证据。

修改：

- `utils/debugtalk.py`：新增 `invalid_password()`；
- `pytest.ini`：增加 `negative` / `unauthorized` marker；
- `tests/unit/test_debugtalk.py`：错误密码生成安全回归；
- `tests/unit/test_shortlink_support.py`：新增异常 YAML 契约/请求主链离线回归；
- `tests/unit/test_stage4_comment_quality.py`：确保新增业务文件继续满足注释规范；
- `README.md`、`docs/00_项目计划书_Latest.md`、`docs/08_阶段4真实SaaS接入.md`：更新 Stage 4 完成和 Stage 4.5 状态。

## 验收

离线：

- 新增测试先 RED 再 GREEN；
- framework tests 全绿；
- 默认离线全量全绿；
- `shortlink-local --level smoke --collect-only` 仍只收集 6 条 Smoke；
- `shortlink-local --level core --collect-only` 能收集新增 2 条异常 core；
- `compileall` 通过；
- 业务源码/YAML 不包含真实密码或 token 字面值。

真实环境：

- 错误密码登录用例通过；
- Group 缺 token 用例通过；
- 原 6 条 Smoke 仍保持 6 passed。
