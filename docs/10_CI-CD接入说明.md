# Stage 6：CI/CD、外部私有环境配置与报告归档说明

## 1. 项目边界：框架是主体，真实项目只是接入示例

本项目定位始终是 **AI 辅助接口自动化测试框架**。当前短链接 SaaS 只是第一个完成真实接入、数据库/Redis 深层校验和 Jenkins 验收的 SUT，用于证明框架可以落地到真实系统；它不进入框架核心，也不进入公共 CI 的业务逻辑。

```text
Framework Core
├─ ConfigManager / VariableContext / ApiRunner / AssertionEngine
├─ MySQL / Redis 通用 Client
├─ run.py
└─ CI 调度契约
        ↓
Project Adapter
├─ config/env.<project>.yaml
└─ testcases/<project>/
        ↓
Real SUT
```

以后接入订单、支付、用户中心等项目时，目标是新增环境 YAML 与 `testcases/<project>/`，而不是修改框架核心。

## 2. 为什么同时使用 GitHub Actions 和 Jenkins

两类 CI 的职责分开：

```text
GitHub Actions
→ 验证公共框架、Mock/Demo、语法和架构契约
→ 不依赖开发者本机服务

Jenkins
→ 运行在能够访问目标 SUT 的节点
→ 通过 ENV_NAME + LEVEL 调用统一 run.py
→ 可选 ENV_FILE 读取 Jenkins Agent 仓库外私有 YAML
→ 可执行真实项目 smoke/core/regression
```

GitHub 托管 Runner 中的 `127.0.0.1` 指向 GitHub 的临时虚拟机，而不是开发者 Windows，所以公共 workflow 不直接运行只存在于本机的真实环境。

## 3. 公共环境 YAML 与仓库外私有覆盖 YAML

### 3.1 公共环境 YAML

真实项目仍可以把下面这些内容上传到 GitHub 供别人参考：

```text
config/env.<project>.yaml
+ testcases/<project>/
```

公共环境 YAML 保存：

- API host、timeout、TLS 等环境级参数；
- `test_selection.include_suites`；
- 当前 Project Adapter 所需的非敏感结构；
- MySQL/Redis 数据源结构；
- 敏感字段的 `CHANGE_ME` 占位符。

这样别人可以完整看到“一个真实项目如何接入框架”，但仓库里没有你的真实密码。

### 3.2 外部私有覆盖 YAML

真实账号、数据库密码以及某台机器独有的差异，放在 **Git 仓库外** 的 YAML。它不需要复制整份公共环境，只写需要覆盖的字段即可。

ConfigManager 的最终优先级是：

```text
CLI 覆盖
> API_* 环境变量覆盖
> 外部环境 YAML
> config/env.<name>.yaml
> config/config.yaml
```

例如当前真实项目的公开参考模板位于：

```text
docs/examples/env.shortlink-local.override.example.yaml
```

实际 Jenkins 副本建议放到类似：

```text
C:\ProgramData\Jenkins\.jenkins\private-configs\<project>.override.yaml
```

该路径位于仓库外，因此不会被 `git add`、GitHub Actions 或普通代码提交带走。

## 4. run.py 的通用外部环境能力

本地命令可以直接使用：

```bash
python run.py --env <project> --env-file "<仓库外覆盖 YAML 路径>" --level smoke
```

`--env-file` 只传“文件路径”，真实账号和密码仍然写在 YAML 中，不放在命令行参数里。

如果 CI 更适合环境变量方式，也可以只设置：

```text
API_TEST_ENV_FILE=<仓库外覆盖 YAML 路径>
```

Pytest collection hooks、fixtures 和统一 Runner 都通过同一个 ConfigManager 读取该文件，因此不会出现 Runner 使用一份配置、collection 又读取另一份配置的问题。

如果用户显式指定的外部文件不存在，ConfigManager 会立即报 `FileNotFoundError`，而不是静默回退到公共 YAML 的 `CHANGE_ME` 后再产生误导性的业务接口失败。

## 5. GitHub Actions 公共框架 CI

文件：

```text
.github/workflows/api-test.yml
```

触发方式：`push`、`pull_request`、`workflow_dispatch`。

执行链：

```text
Checkout
↓
Python 3.11
↓
requirements-dev.txt + constraints.txt
↓
pytest tests/
↓
python run.py --env test --level smoke
↓
compileall
↓
上传 Artifact
```

`env=test` 是框架受控 Mock 环境。它通过环境 YAML 选择 Demo suite，并由 fixture 自动启动随机本地端口的 Mock Server，因此 GitHub Runner 不需要真实 Gateway、MySQL、Redis 或第三方域名。

公共 CI 同时跑 `tests/` 和 Demo smoke，是因为前者验证框架内部契约，后者从正式用户入口验证 YAML → Pytest → Fixture → ApiRunner → RequestClient → Assertions 完整主链。

## 6. Jenkins 参数化 Pipeline

Jenkinsfile 现在只暴露三个 **框架级** 参数：

```text
ENV_NAME
→ 对应 config/env.<name>.yaml

LEVEL
→ smoke / core / regression

ENV_FILE
→ 可选的 Jenkins Agent 仓库外环境覆盖 YAML 路径
→ 留空时不启用外部覆盖
```

Jenkinsfile 不包含任何当前真实项目的环境名、域名、表名、Redis Key、用户名或密码。

### 6.1 Mock / 公共环境

```text
ENV_NAME = test
LEVEL    = smoke
ENV_FILE = 留空
```

### 6.2 任意真实 SUT

```text
ENV_NAME = <真实项目环境名>
LEVEL    = smoke/core/regression
ENV_FILE = <该 Jenkins Agent 上的仓库外覆盖 YAML 路径>
```

Pipeline 只把 `ENV_FILE` 的 **路径** 临时注入测试进程树：

```text
ENV_FILE parameter
        ↓
API_TEST_ENV_FILE
        ↓
run.py
        ↓
ConfigManager
```

不会执行下面这种复制：

```text
private YAML → Jenkins Workspace
```

因此真实凭据不会形成 Workspace 持久副本，也不会进入 `reports/`、`logs/` 或 Artifact 归档规则。

## 7. Windows / Linux Agent 兼容

Jenkinsfile 使用 `isUnix()` 分别选择 `sh` / `bat`，并在每次构建创建 Workspace 独立 `.venv`。Windows Pipeline 同时启用 `PYTHONUTF8=1`，解决中文系统 Service 场景下 pip 读取 UTF-8 requirements 时的 CP936/GBK 解码问题。

真实项目运行前，Jenkins Agent 只需要满足：

1. 能执行系统 Python 以创建 `.venv`；
2. 能访问目标 SUT；
3. 目标 SUT 自己依赖的 MySQL/Redis/域名映射等已经准备好；
4. 如需私有覆盖，`ENV_FILE` 指向的文件对 Jenkins Service 账号可读。

这些都是“目标环境准备”，不写入公共 Jenkinsfile。

## 8. 报告与 Artifact

无论测试通过还是失败，`post { always { ... } }` 都执行，但 **只消费当前 Jenkins Build 对应的 run 目录**：

```text
junit
→ reports/runs/jenkins-${BUILD_NUMBER}/junit.xml
→ Jenkins Test Result

archiveArtifacts
→ reports/runs/jenkins-${BUILD_NUMBER}/**
→ logs/**/*
```

Jenkins Workspace 默认会跨构建保留文件。如果递归扫描整个 `reports/runs/`，上一轮失败构建的 `junit.xml` 会在下一轮再次被 JUnit 插件读取，可能导致“当前 Pytest 全通过但 Jenkins 仍显示 UNSTABLE”。因此报告路径必须按 `BUILD_NUMBER` 隔离。旧构建报告已经由 Jenkins 自己的 Build 历史归档，不需要在新构建中重复收集。

外部环境 YAML 不在归档路径内。当前不强制 Jenkins Allure 插件；原始 `allure-results` 作为当前 Build Artifact 保存即可。

## 9. 已完成的真实 Stage 6 证据

当前已经真实验证：

```text
GitHub Actions 公共 CI                       ✅
Jenkins 从 GitHub SCM Checkout               ✅
Windows Workspace 独立 .venv                 ✅
依赖自动安装                                 ✅
ENV_NAME / LEVEL 参数化                      ✅
Mock smoke                                   ✅ 2 passed
JUnit Test Result                            ✅
Artifacts(logs + reports/runs/<run-id>)      ✅
```

外部私有 YAML 机制在本版本已完成代码与离线契约验证；真实 SUT 的 Jenkins smoke 仍需在用户本机以实际私有覆盖文件执行后，才能标记为真实平台验收通过。
