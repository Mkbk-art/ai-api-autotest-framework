# Stage 4.5 V2.10 第一批异常用例离线验证

## 版本范围

本证据对应 Stage 4.5 第一批两条真实异常用例代码：

1. 错误密码登录；
2. Group 缺少 token。

沙箱无法访问用户 Windows 本地 Gateway/Admin/Redis，因此本文件只证明框架、YAML 契约、
请求展开、collection 分层和代码质量，不把 Fake Response 结果描述为真实 SaaS 通过。

## TDD 红绿证据

### 错误密码生成

RED：新增单元测试后，`DebugTalk` 尚不存在 `invalid_password()`，定向测试以
`AttributeError` 失败。

GREEN：新增 `invalid_password()` 后，`tests/unit/test_debugtalk.py` 通过；测试证明该函数
生成 `__api_autotest_invalid__...` 值，并且不读取/拼接测试环境中的真实密码值。

### 异常 YAML

RED：在两份 YAML 创建前，契约测试分别以 `FileNotFoundError` 失败：

```text
auth_invalid.yaml
group_unauthorized.yaml
```

GREEN：创建高密度中文注释 YAML 和对应真实测试模块后，契约/注释测试通过。

### Collection 分层

加入两条 core 后，旧“shortlink-local 总共 6 条”的集成测试按预期变红，因为真实环境现在
共有 8 条业务 Test Item。随后将守护规则改为：

```text
全部真实业务：8
Smoke：6
Core：2
```

并新增 smoke/core 分层 collection 回归。

## Framework Tests

命令：

```bash
pytest tests -q
```

结果：

```text
92 passed
```

## 默认离线全量

命令：

```bash
pytest -q
```

结果：

```text
98 passed
```

默认 `test` 环境仍只真正执行 Stage 3 Mock Demo；真实 shortlink 用例通过 collection isolation
不会向用户 SaaS 发请求。

## 真实环境 Collection

Smoke：

```bash
python run.py --env shortlink-local --level smoke --collect-only
```

结果：

```text
collected 8 items / 2 deselected / 6 selected
6/8 tests collected
```

选中的仍是 Stage 4 已真实验证的 Login/Create/Group/Page/Redirect/Statistics 六条 Happy Path。

Core：

```bash
python run.py --env shortlink-local --level core --collect-only
```

结果：

```text
collected 8 items / 6 deselected / 2 selected
2/8 tests collected
```

只选中：

```text
test_auth_invalid.py
test_group_unauthorized.py
```

## Compile / 凭据隔离契约

```text
compileall: PASS
stage45 credential-isolation contract: PASS
```

离线守护确认：

- `auth_invalid.yaml` 的 password 只能是 `${invalid_password()}`；
- 错误登录 YAML 不读取 `SHORTLINK_TEST_PASSWORD`；
- `group_unauthorized.yaml` 最终 Header 只有 username，没有 token；
- `DebugTalk.invalid_password()` 的可执行函数体不调用 env/getenv；
- 新增 Python/YAML 均继续通过 Stage 4 高密度中文注释质量测试。

## 真实环境下一验收点

用户 Windows 本机：

```bash
python run.py --env shortlink-local --level core --collect-only
python run.py --env shortlink-local --level core
```

只有真实 `core` 两条通过后，E1/E2 才能标记为“真实环境已验证”。

## 候选交付包全新解压复验

在工作目录验证通过后，V2.10 候选 ZIP 被解压到新的独立目录，并从解压后的文件重新执行同一组检查。结果为：

```text
framework tests: 92 passed
default offline full: 98 passed
smoke collect: 6/8 tests collected (2 deselected)
core collect: 2/8 tests collected (6 deselected)
compileall: PASS
credential isolation: PASS
```

该步骤用于排除“工作目录测试通过但 ZIP 漏文件或打包内容不一致”的交付风险。最终交付 ZIP 在文档状态固化后还会再次从最终字节包独立解压复验。
