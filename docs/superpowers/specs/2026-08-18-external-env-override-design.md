# 外部私有环境 YAML 覆盖设计

## 目标

为 **AI 辅助接口自动化测试框架** 增加通用的“外部环境覆盖 YAML”能力，使 Jenkins、本地命令行或其他 CI 可以在不把真实凭据提交到公共 Git 仓库的前提下运行真实 SUT。

## 核心边界

- 框架核心、`run.py`、`Jenkinsfile` 不得出现 `shortlink-local`、短链域名、表名、Redis Key 等当前 SUT 业务知识。
- `config/env.<name>.yaml` 仍是可公开、可复用、可作为项目接入示例的命名环境配置；其中敏感值使用占位符。
- 外部私有 YAML 只作为可选覆盖层，可以只写凭据等本机私有字段，不要求复制整份公开环境 YAML。
- 外部覆盖优先级：`CLI 覆盖 > 环境变量覆盖 > 外部环境 YAML > env.<name>.yaml > config.yaml`。
- `run.py --env-file <path>` 与 `API_TEST_ENV_FILE=<path>` 都支持外部覆盖；CLI 参数只传文件路径，不承载凭据值。
- Jenkins 新增通用参数 `ENV_FILE`。为空时维持现有公共/Mock 行为；非空时只把路径作为 `API_TEST_ENV_FILE` 注入测试进程，不复制文件到 Workspace，也不归档文件内容。
- 外部文件显式指定但不存在时必须立即失败，避免错误地回退到公共占位配置并产生误导性测试失败。
- 真实项目可继续将 `testcases/<project>/`、公开的 `config/env.<project>.yaml` 上传仓库作为接入参考；真实账号、数据库密码等仅留在仓库外的私有覆盖 YAML。

## 为什么不复制私有 YAML 到 Workspace

复制方案会让真实凭据在 Jenkins Workspace 中形成持久副本，还需要额外清理与恢复逻辑。直接由 ConfigManager 读取仓库外路径更简单、更安全，也更符合框架职责：CI 只选择环境，配置系统负责加载配置。

## 示例关系

```text
公共 Git 仓库
├─ config/env.<project>.yaml        # 可公开，敏感值为占位符
└─ testcases/<project>/             # 可公开，真实项目接入示例

Jenkins Agent 本机（仓库外）
└─ private-configs/<project>.yaml   # 只写真实凭据/本机差异，不进入 Git

Jenkins
ENV_NAME=<project>
ENV_FILE=C:\\...\\private-configs\\<project>.yaml
        ↓
run.py
        ↓
ConfigManager
config.yaml
+ env.<project>.yaml
+ external private override YAML
+ env vars
+ CLI overrides
```

## 非目标

- 不在本阶段引入 Jenkins Credentials Binding 来承载业务密码值。
- 不新增项目专用 Pipeline。
- 不把 YAML 扩展成流程编排语言。
- 不修改短链接测试业务逻辑。
