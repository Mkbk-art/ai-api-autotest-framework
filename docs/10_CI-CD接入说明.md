# Stage 6：CI/CD 是可选工程化能力，不是框架运行前提

## 1. 先区分 Framework Core 与运行方式

本项目主体始终是 **AI 辅助接口自动化测试框架**。Framework Core 能够在完全不使用 GitHub/Jenkins 的情况下运行：

```text
Python + YAML + 目标测试环境
        ↓
run.py / Pytest
```

GitHub Actions、Jenkins、GitLab CI 等属于“如何自动执行框架”的工程化选择，不属于框架核心依赖。

## 2. 三种典型使用模式

### 2.1 Local Only

最终用户拿到框架后可以直接：

```text
配置 config/env.<project>.yaml
配置 testcases/<project>/
python run.py --env <project> --level smoke
```

不需要 Git，不需要 Jenkins。

### 2.2 Team SCM + Optional CI

团队可使用：

```text
GitHub / GitLab / Gitee / 企业内部 Git / 其他 SCM
```

再按需要选择 Jenkins 或其他 CI。当前 Jenkinsfile 使用 `checkout scm`，并没有写死 GitHub 仓库地址。

### 2.3 当前公共框架开发模式

本仓库自己使用：

```text
GitHub Actions
→ 公共框架 / Mock / 架构契约

Jenkins Windows Agent
→ 真实 SUT / JUnit / Artifact / 参数化环境
```

这是为了版本管理、真实平台验收和作品证据，不代表最终用户必须照搬。

## 3. SUT 配置与私有覆盖

现有 `ConfigManager` 继续使用已经真实验收的优先级：

```text
CLI
> API_* 环境变量
> 外部环境 YAML
> config/env.<name>.yaml
> config/config.yaml
```

外部 YAML 是团队/Git/CI 场景的可选安全手段。例如公共仓库保留结构和占位符，本机/Jenkins 再覆盖真实账号或数据库密码。

最终用户如果完全不使用 Git，也可以直接在自己的环境 YAML 中写真实值；框架不会强迫他把配置拆到仓库外。

## 4. `run.py` 外部环境文件

```bash
python run.py \
  --env <project> \
  --env-file "<optional-private-yaml>" \
  --level smoke
```

CI 也可以只传路径：

```text
API_TEST_ENV_FILE=<private-yaml-path>
```

Jenkinsfile 不复制私有 YAML 到 Workspace，只把文件路径临时注入测试进程树。

## 5. 当前 Jenkins 参数

```text
ENV_NAME
→ config/env.<name>.yaml 的逻辑环境名

LEVEL
→ smoke / core / regression

ENV_FILE
→ 可选外部 YAML 路径
```

这些都是框架级参数，不包含当前真实 SUT 的业务名、域名、表名、Redis Key 或账号。

## 6. 为什么当前 Jenkins 从 SCM Checkout

当前项目 Job 选择了 Pipeline from SCM，因此 Jenkinsfile 中执行：

```text
checkout scm
```

这里的 `scm` 由 Jenkins Job 自己配置，可以指向 GitHub、GitLab、Gitee、企业 Git 等；它不是 `github.com/...` 硬编码。

如果最终用户采用不同 Jenkins 管理方式，也可以自行使用 Jenkins UI Pipeline、其他 SCM 或其他 CI 产品。Framework Core 不受影响。

## 7. Windows / Linux Agent

Jenkinsfile 使用 `isUnix()` 选择 `sh` / `bat`，每次构建创建 Workspace 独立 `.venv`。Windows 开启 `PYTHONUTF8=1`，避免 Jenkins Service 在中文区域设置下用 CP936/GBK 读取 UTF-8 requirements。

## 8. 当前 Build 报告隔离

JUnit 与 Artifact 只读取当前 Build 对应目录：

```text
reports/runs/jenkins-${BUILD_NUMBER}/junit.xml
reports/runs/jenkins-${BUILD_NUMBER}/**
```

这样不会把上一次失败 `junit.xml` 再次聚合进本次成功构建。

## 9. Stage 6 已完成的真实证据

```text
GitHub Actions 公共 CI                         ✅
Jenkins SCM Checkout                           ✅
Windows Workspace 独立 .venv                   ✅
ENV_NAME / LEVEL / ENV_FILE                    ✅
Mock Smoke                                     ✅ 2 passed
真实 SUT Smoke                                  ✅ 6 passed
JUnit                                           ✅
Artifacts                                       ✅
外部私有 YAML                                  ✅
按 Build 隔离报告                              ✅
```

Stage 6 到此保持稳定。本次 Stage 7.1 AI 配置重构不会修改 `Jenkinsfile` 或 `core/config_manager.py`。
