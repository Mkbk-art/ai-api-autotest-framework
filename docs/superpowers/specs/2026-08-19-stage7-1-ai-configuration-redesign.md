# Stage 7.1 AI Configuration Redesign — Final Design Draft V2

> 项目定位：**AI 辅助接口自动化测试框架**  
> 目的：同时站在“框架开发者”和“最终框架使用者”两个视角重新设计 AI 配置层。  
> 本设计替代 Stage 7.1 第一版“主要依赖 OS 环境变量”的 Provider 配置方式。  
> 现有 FailureEvidence / Facts / Sanitizer / Analysis Validator 设计继续保留。

---

## 1. 为什么必须重写 AI 配置层

Stage 7.1 第一版已经完成：

```text
run.json + junit.xml
→ FailureEvidence
→ Deterministic Facts
→ Sanitizer
→ AIClient
→ Validator
→ analysis.json / analysis.md
```

这些能力本身保留。

需要重构的是 **AI Provider 配置来源**。第一版主要读取：

```text
AI_API_BASE
AI_API_KEY
AI_MODEL
AI_TIMEOUT
```

这适合“我们把代码公开到 GitHub 时避免泄露 Key”的开发场景，但不符合最终用户拿到框架后的自然流程：

```text
下载框架
→ 配置 YAML
→ 接入自己的真实项目
→ 配置自己的真实 AI Provider
→ 直接运行
```

因此本次不是推翻 7.1，而是重写 **AI Configuration / Provider Resolution**。

---

## 2. 两种身份必须同时成立

### 2.1 框架开发者

当前项目公开在 GitHub，因此要求：

- 公共仓库不能出现真实 AI API Key；
- 可以提交完整 AI YAML 结构和示例；
- 开发者本机可以有私有覆盖文件；
- 私有文件必须被 `.gitignore`；
- GitHub Actions 不依赖真实 AI Key；
- 真实 Provider 验收在本机完成。

### 2.2 最终框架用户

最终用户拿到框架后：

- **不要求使用 GitHub**；
- **不要求使用 Jenkins**；
- **不要求使用环境变量**；
- 可以直接修改 `config/ai.yaml`；
- 可以把自己的真实 `api_key` 写进 YAML；
- 可以选择不同 Provider Profile；
- 可以用 CLI 临时覆盖 Provider / Model 等运行参数；
- 如果他使用 Git/CI，再自行选择 `ai.local.yaml`、环境变量或 Secret 管理。

结论：

> GitHub 安全策略是开发/协作模式，不是 Framework Core 的使用前提。

---

## 3. 前阶段架构回顾与纠正结论

### Stage 1–3：核心框架

**保持，不修改。**

请求执行、Case Loader、VariableContext、AssertionEngine 都是通用能力，不依赖 GitHub/Jenkins，也不依赖 Shortlink。

### Stage 4 / 4.5：真实 Shortlink SUT

**保持，不修改核心逻辑。**

Gateway、Sentinel 业务限流、创建重试、302、统计、Cleanup 均位于项目适配层，没有泄漏到 `core/`。

### Stage 5：MySQL / Redis

**保持，不修改。**

当前模式本身正确：

```text
YAML
→ named data source
→ generic MySQL / Redis Client
→ AssertionEngine
```

现有 `core/config_manager.py` 已经过真实 SUT/Jenkins 验收。本轮 AI 配置优先级不同，因此**不修改全局 ConfigManager**，新增 AI 专用 Resolver。

### Stage 6：CI/CD

**Jenkinsfile 代码保持。文档定位需要纠正。**

当前 Jenkinsfile 使用 `checkout scm`，依赖的是 SCM 模式 Job，而不是 GitHub 厂商。

README / CI 文档必须明确三种模式：

```text
A. Local Only
   Python + YAML
   不需要 Git / Jenkins

B. Team SCM
   GitHub / GitLab / Gitee / internal Git
   + optional Jenkins

C. Current Framework Development
   GitHub Actions + Jenkins
   这是当前项目自己的开发/展示方式
```

### Repository Hygiene：发现前阶段真实回归

当前仓库仍然跟踪 `.idea/`，而根 `.gitignore` 已没有 `.idea/`。

本轮必须：

```text
.gitignore
├─ .idea/
└─ config/ai.local.yaml
```

并从 Git 跟踪中移除 `.idea/`，同时增加 Repository Hygiene Contract，防止后续完整 ZIP 再次回退。

### README：发现版本/定位滞后

当前 README：

- 顶部版本仍停留在 V3.2.6；
- Stage 7.1 仍写成 Provider 只从 OS 环境/Secret Store 读取。

本轮必须同步修正。

---

## 4. AI 配置总体架构

最终结构：

```text
config/
├─ ai.yaml
└─ ai.local.yaml         # 可选；默认 Git ignored

用户 Home：
~/.ai-api-autotest-framework/
└─ ai.yaml               # 项目没有 ai.yaml 时的个人默认配置
```

Production code：

```text
ai/
├─ config.py
├─ client.py
├─ contracts.py
├─ failure_analyzer.py
└─ cli.py
```

---

## 5. `config/ai.yaml` 是真实主配置，不是模板

公共仓库初始内容：

```yaml
# AI 辅助能力主配置。
# 最终用户可以直接修改本文件并运行框架。
# 当前公共仓库不保存真实 Provider/Key，因此 provider 默认为 null。

ai:
  # 当前选择的 Provider Profile。
  provider: null

  # Provider 未单独配置 timeout 时使用该值。
  timeout: 20

  # Provider Profile 完全由 YAML 定义。
  providers: {}
```

最终用户可以直接改成：

```yaml
ai:
  provider: my-model
  timeout: 30

  providers:
    my-model:
      protocol: openai_chat_completions
      base_url: https://provider.example/v1
      model: model-name
      api_key: real-user-key
```

此时无需 GitHub、`.env`、OS 环境变量或 Jenkins。

---

## 6. `config/ai.local.yaml` 的定位

它不是框架运行必需文件，而是：

> 开发者 / Git 用户 / CI 用户的可选私有覆盖。

公共 `ai.yaml` 可保留 `api_key: null`，本机 `ai.local.yaml` 只覆盖真实 Key 或其他私有差异。

最终用户如果完全不使用 Git，可以直接把 Key 写在 `ai.yaml`。

---

## 7. 主配置搜索顺序

AI 主 YAML 搜索：

```text
1. <PROJECT_ROOT>/config/ai.yaml
   ↓ 不存在
2. ~/.ai-api-autotest-framework/ai.yaml
   ↓ 不存在
3. 无 YAML 主配置
```

`config/ai.local.yaml` 不是第二套主配置，而是**项目本地覆盖层**。

如果存在：

```text
Primary YAML
+
config/ai.local.yaml
```

递归 merge。

这准确实现：

> 项目配置优先；项目没有时才读取用户 Home 配置。

---

## 8. 最终字段优先级

用户要求正式固定为：

```text
最高

1. CLI direct override
2. project config/ai.local.yaml
3. Primary YAML
   - project config/ai.yaml
   - 或 home ~/.ai-api-autotest-framework/ai.yaml
4. Environment fallback

最低
```

即：

```text
CLI > local YAML > main YAML > ENV
```

---

## 9. 为什么不复用全局 ConfigManager

现有 SUT ConfigManager：

```text
CLI > ENV > external YAML > named YAML > default
```

AI：

```text
CLI > local YAML > main YAML > ENV
```

用途不同，因此：

```text
core/config_manager.py     # 保持
ai/config.py               # 新增 AIConfigResolver
```

不强行统一两种不同的配置生命周期。

---

## 10. CLI 设计

默认：

```bash
python -m ai.cli analyze \
  --run-dir reports/runs/<run_id>
```

允许临时覆盖：

```bash
python -m ai.cli analyze \
  --run-dir reports/runs/<run_id> \
  --provider qwen-main \
  --model another-model
```

支持：

```text
--provider
--protocol
--base-url
--model
--timeout
--api-key-prompt
```

---

## 11. API Key 规则

最终用户可以在 YAML 中直接写：

```yaml
api_key: real-key
```

但不提供：

```bash
--api-key real-key
```

避免 shell history / process list 泄露。

如果希望控制台临时输入：

```bash
--api-key-prompt
```

使用 `getpass.getpass()`。

Key 优先级：

```text
--api-key-prompt
> ai.local.yaml
> ai.yaml
> AI_API_KEY
```

任何日志 / Artifact 都不能打印 Key。

---

## 12. Environment Variables 只是 fallback

保留：

```text
AI_PROVIDER
AI_PROTOCOL
AI_API_BASE
AI_MODEL
AI_API_KEY
AI_TIMEOUT
```

只有 CLI/YAML 对应字段没有值时才使用 ENV。

---

## 13. Provider 与 Protocol 必须彻底分离

Provider 只是 YAML Profile Name：

```yaml
providers:
  deepseek-main:
    protocol: openai_chat_completions

  qwen-main:
    protocol: openai_chat_completions

  openai-main:
    protocol: openai_chat_completions

  company-private:
    protocol: openai_chat_completions
```

Production code 禁止：

```python
if provider == "deepseek":
    ...
elif provider == "qwen":
    ...
elif provider == "openai":
    ...
```

---

## 14. Protocol Adapter 是真正扩展点

第一版支持：

```text
openai_chat_completions
```

Client Factory：

```text
ResolvedAIConfig
→ protocol
→ AIClientFactory
→ OpenAIChatCompletionsClient
```

Factory 只认识协议，不认识厂商。

未来新协议才新增 Adapter，例如：

```text
openai_responses
anthropic_messages
dashscope_native
```

同协议的新 Provider **不改 Python**。

---

## 15. AI Config 数据契约

新增：

```python
@dataclass(frozen=True)
class AIProviderConfig:
    provider: str
    protocol: str
    base_url: str
    model: str
    api_key: str
    timeout: float
```

`AIConfigResolver.resolve(...)` 返回：

```text
AIProviderConfig
或 None（完全未配置 AI）
```

如果用户已经选择 Provider，但缺少 `protocol/base_url/model/api_key`，属于明确配置错误；错误信息只写缺失字段名，不打印 secret 值。

---

## 16. Client 类命名修正

当前 `OpenAICompatibleClient` 语义过宽，它实际上只实现 `/chat/completions`。

正式改为：

```text
OpenAIChatCompletionsClient
```

为避免已有公开调用突然破坏，暂时保留兼容 alias：

```python
OpenAICompatibleClient = OpenAIChatCompletionsClient
```

文档只使用新名称。

---

## 17. `AIClientFactory`

```python
class AIClientFactory:
    _PROTOCOLS = {
        "openai_chat_completions": OpenAIChatCompletionsClient,
    }

    @classmethod
    def create(cls, config: AIProviderConfig) -> AIClient:
        ...
```

如果 YAML 使用未知协议，明确失败：

```text
Unsupported AI protocol: <name>
```

不按厂商 fallback。

---

## 18. Failure Analysis 主链保持不变

保留：

```text
FailureEvidenceBuilder
Facts
Sanitizer
Validator
analysis.json
analysis.md
```

只改变：

```text
旧：CLI → OpenAICompatibleClient.from_env()

新：CLI → AIConfigResolver → AIClientFactory → AIClient
```

---

## 19. `run.py` 仍然不 import AI

继续保持独立辅助链：

```text
run.py
→ Pytest
→ 原始 exit code
```

AI：

```text
python -m ai.cli analyze ...
```

---

## 20. Jenkins / GitHub 最终定位

README 必须明确：

### Local Mode

```text
下载框架
→ 配 YAML
→ python run.py
→ python -m ai.cli
```

不需要 Git/Jenkins。

### Team SCM Mode

可以使用 GitHub / GitLab / Gitee / 企业内部 Git，Jenkins 可选。

### Current Framework Development Mode

我们当前使用 GitHub Actions + Jenkins 做版本管理、公共 CI、真实 SUT 验收和作品展示。

这不是最终用户必须复制的部署方式。

---

## 21. Repository Hygiene 修正

`.gitignore` 必须增加：

```gitignore
.idea/
config/ai.local.yaml
```

当前已被 Git 跟踪的 `.idea/` 必须移除。

新增：

```text
tests/integration/test_repository_hygiene.py
```

守门：

- `.gitignore` 必须含 `.idea/`；
- 必须含 `config/ai.local.yaml`；
- 发布 ZIP 不允许含 `.idea/`；
- 发布 ZIP 不允许含 `config/ai.local.yaml`；
- 公共 `config/ai.yaml` 不允许出现真实 API Key。

---

## 22. YAML 注释要求

`config/ai.yaml` 必须继续使用高密度中文注释，说明：

- `provider` 是什么；
- `providers` 是什么；
- `protocol` 为什么不是厂商名；
- `base_url` 的含义；
- `model` 可自由修改；
- `api_key` 最终用户可以填写；
- Git 用户为什么建议使用 `ai.local.yaml`；
- 环境变量只是 fallback；
- CLI 是临时最高优先级。

---

## 23. Stage 7.1 真实 Provider 验收顺序

配置重构完成后：

```text
1. GitHub Actions 再次绿色
2. local config/ai.local.yaml 配真实 Provider
3. 不设置 AI_* 环境变量
4. 运行真实 AI 分析
5. 验证 ai_status=success
6. 验证 Facts 引用
7. 验证无 Secret 泄漏
```

这样首先证明：

> YAML 本身就能驱动真实 Provider。

之后可选再测试第二个同协议 Provider：

```text
只改 YAML
Python 不变
→ ai_status=success
```

作为 Provider 解耦的更强证据。

---

## 24. 本轮不做

- 动态 `/models` 查询；
- GUI；
- Provider 市场；
- 自动下载 SDK；
- OpenAI Responses Adapter；
- Anthropic Adapter；
- DashScope Native Adapter；
- Stage 7.2 YAML Case Generator。

先把配置和协议扩展点做正确。

---

## 25. 本轮必须修改的文件

Production：

```text
ai/config.py                   # 新增
ai/client.py                   # 重构
ai/cli.py                      # 重构
```

Config / hygiene：

```text
config/ai.yaml                 # 新增
.gitignore                     # 修正
.idea/                         # 从 Git tracking 移除
```

Tests：

```text
tests/ai/test_ai_config.py
tests/ai/test_ai_client.py
tests/ai/test_ai_cli.py
tests/integration/test_repository_hygiene.py
tests/integration/test_ai_architecture_contract.py
```

Docs：

```text
README.md
docs/10_CI-CD接入说明.md
docs/11_AI失败分析接入说明.md
AI_API_Autotest_Framework_Project_Plan_Latest.md
```

---

## 26. 不修改的核心文件

除非 TDD 发现真实缺陷，否则禁止为了“统一”修改：

```text
core/config_manager.py
core/api_runner.py
core/assertion_engine.py
core/request_client.py
db/mysql_client.py
db/redis_client.py
run.py
Jenkinsfile
testcases/shortlink/*
```

---

## 27. 最终验收标准

```text
[ ] 普通用户只用 config/ai.yaml 可配置完整 Provider
[ ] 开发者可用 ai.local.yaml 覆盖 Key
[ ] 项目没有 ai.yaml 时可 fallback 到用户 Home ai.yaml
[ ] CLI > local YAML > main YAML > ENV
[ ] --api-key-prompt 可用
[ ] 不存在 --api-key 明文参数
[ ] Provider 名称不出现在 production Python 分支
[ ] Factory 只按 protocol 路由
[ ] 同协议任意 profile 无需改 Python
[ ] AI 未配置时继续 unavailable 安全降级
[ ] Stage 7.1 既有测试不回归
[ ] 全量 tests 不回归
[ ] run.py Mock Smoke 不回归
[ ] core ConfigManager 未改变
[ ] Jenkinsfile 未被 AI 配置侵入
[ ] .idea 不再被发布
[ ] ai.local.yaml 不进入 Git/ZIP
[ ] README 明确 GitHub/Jenkins 是可选工程化方式
```

---

## 28. 当前结论

Stage 7.1 第一版不是作废，而是：

```text
Evidence / Facts / Sanitizer / Validator   ✅ 保留
Provider Configuration                     ❌ 重构
Provider Factory                           ➕ 新增
User YAML Experience                       ➕ 新增
Repository Hygiene                         🔧 修复
CI/CD Documentation Positioning            🔧 修正
```

完成本设计后再进行真实 Provider 验收。

---

## V2 实施时的最终用户视角补充

“公共 `config/ai.yaml` 不出现真实 Key”只属于**本项目公开发布时的 Release Hygiene 检查**，不能做成会阻止最终用户本地使用的运行时规则。最终用户如果完全不使用 Git，合法地把真实 `api_key` 写入自己的 `config/ai.yaml` 后，框架测试/CLI 仍必须正常工作。

因此 production/runtime tests 只守以下边界：

- `.gitignore` 默认保护 `config/ai.local.yaml`；
- `AIProviderConfig` repr 不泄露 Key；
- CLI/Artifact/异常不泄露 Key；
- 本公共发布包在打包时额外扫描当前仓库 `config/ai.yaml` 不包含真实 Key。

这个补充用于避免把“框架开发者的 GitHub 安全策略”错误强加给“最终用户本地运行方式”。
