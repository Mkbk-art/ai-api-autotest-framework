# Stage 6：CI/CD 与报告归档说明

## 1. 为什么同时使用 GitHub Actions 和 Jenkins

本项目是 **AI 辅助接口自动化测试框架**，短链接 SaaS 只是当前真实被测系统。两类 CI 的职责因此分开：

```text
GitHub Actions
→ 验证公共框架、Mock/Demo、语法和架构契约
→ 不依赖开发者本机服务

Jenkins
→ 运行在能够访问目标 SUT 的节点
→ 通过 ENV_NAME + LEVEL 调用统一 run.py
→ 可执行真实项目 smoke/core/regression
```

GitHub 托管 Runner 中的 `127.0.0.1` 指向 GitHub 的临时虚拟机，而不是开发者 Windows，所以公共 workflow 不应该直接运行只存在于本机的真实环境。

## 2. GitHub Actions 公共框架 CI

文件：

```text
.github/workflows/api-test.yml
```

触发方式：

- `push`；
- `pull_request`；
- `workflow_dispatch` 手工触发。

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

### 2.1 为什么同时跑 `tests/` 和 Demo smoke

两者验证层级不同：

- `python -m pytest tests`：验证 VariableContext、AssertionEngine、CaseLoader、数据源 Client、Runner、架构守门等框架内部契约；
- `python run.py --env test --level smoke`：从用户正式入口验证 YAML -> Pytest -> Fixture -> ApiRunner -> RequestClient -> Assertions 的完整 Mock 主链。

因此不是重复执行。

### 2.2 Artifact 中保存什么

GitHub Actions 无论测试成功还是失败都会尝试上传：

```text
reports/ci/
reports/runs/github-actions-demo/
logs/
```

其中可能包含：

- `framework-junit.xml`；
- Demo `junit.xml`；
- `allure-results/`；
- `run.json`；
- 运行日志。

如果测试已经失败，Artifact 仍保留，方便下载后定位，而不是 Runner 销毁后只剩一个红叉。

## 3. Jenkins 参数化 Pipeline

文件：

```text
Jenkinsfile
```

Jenkinsfile 不写死任何具体项目，只暴露两个参数：

```text
ENV_NAME
→ 对应 config/env.<name>.yaml

LEVEL
→ smoke / core / regression
```

例如框架 Mock：

```text
ENV_NAME = test
LEVEL = smoke
```

如果 Jenkins Agent 就运行在能访问某个真实 SUT 的机器上，则把 `ENV_NAME` 填成该环境 YAML 的名称即可。

Jenkins 最终始终调用：

```bash
python run.py --env "<ENV_NAME>" --level "<LEVEL>" --run-id "jenkins-<BUILD_NUMBER>"
```

所以新增其他真实项目时，CI 不需要知道项目叫什么。

## 4. Windows / Linux Agent 兼容

Jenkinsfile 使用：

```text
isUnix() == true  → sh
isUnix() == false → bat
```

因此一份 Jenkinsfile 可以在 Linux Agent 或 Windows Agent 上工作。

Windows 本机执行真实项目时需要保证：

1. Jenkins 服务账号能够执行 `python`；
2. Python 环境已能安装项目依赖；
3. 被测服务/MySQL/Redis 已启动；
4. 本地域名映射等 SUT 自己的运行条件已经准备好；
5. 对应 `config/env.<name>.yaml` 已配置正确。

这些属于具体 SUT 的环境准备，不写进公共 Jenkinsfile。

## 5. Jenkins 报告归档

无论测试通过还是失败，`post { always { ... } }` 都执行：

```text
junit
→ 读取 reports/runs/**/junit.xml
→ Jenkins 页面展示 Test Result

archiveArtifacts
→ 保存 reports/runs/**/*
→ 保存 logs/**/*
```

当前不强制依赖 Jenkins Allure 插件。原始 `allure-results` 会作为 Artifact 保存；如果以后在 Jenkins 安装 Allure 插件，可以再增加可视化展示，但它不是框架运行的前置条件。

## 6. 为什么 CI 不能重新实现 Runner 逻辑

不推荐下面这种方式：

```text
Jenkins/GitHub Actions
→ 自己拼 pytest -m ...
→ 自己判断 suite
→ 自己定义报告目录
```

因为这会形成第二套执行入口。

当前统一关系：

```text
CI 平台
↓
run.py
↓
ConfigManager
↓
Pytest collection
↓
YAML level/tags + include_suites
↓
ApiRunner
```

所以本地、Jenkins 与后续其他 CI 平台共享同一语义。

## 7. 常用执行方式

### GitHub Actions

提交到 GitHub 后自动触发，也可以在仓库 Actions 页面手工运行 `API Autotest Framework CI`。

### Jenkins Mock 验证

```text
ENV_NAME=test
LEVEL=smoke
```

### Jenkins 真实 SUT 验证

先确保 Jenkins Agent 能访问目标环境，然后：

```text
ENV_NAME=<真实环境配置名>
LEVEL=smoke/core/regression
```

## 8. Stage 6 验收边界

Stage 6 可由本地离线测试证明的内容：

- GitHub workflow 结构；
- Action 主版本；
- framework/Mock 执行入口；
- Jenkins 参数化设计；
- JUnit/Artifact 失败后归档；
- 公共 CI 无当前 SUT 业务硬编码。

只有真正把仓库 push 到 GitHub 后产生绿色 workflow run，才能把“GitHub Actions 云端运行通过”标记为真实平台证据；只有 Jenkins 实际创建 Pipeline 并执行成功，才能把“Jenkins Pipeline 真实运行通过”标记为真实平台证据。
