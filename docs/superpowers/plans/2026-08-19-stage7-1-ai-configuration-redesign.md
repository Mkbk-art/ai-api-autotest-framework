# Stage 7.1 AI Configuration Redesign — TDD Implementation Plan V2

> **Goal:** 在保留 Stage 7.1 Evidence/Facts/Sanitizer/Validator 的前提下，把 AI Provider 配置重构为“最终用户 YAML 优先、开发者可安全本地覆盖、Provider 与 Protocol 解耦”的通用框架能力，同时修复前阶段发现的 `.idea` 仓库卫生回归和 CI/CD 文档定位问题。

> **Architecture:** `ai/config.py` 负责 `CLI > ai.local.yaml > ai.yaml > ENV`；`ai/client.py` 只按 `protocol` 创建 Adapter；`ai/cli.py` 负责 CLI 覆盖和 `getpass`。现有 `core/config_manager.py`、`run.py`、Jenkinsfile、Shortlink Adapter 不改。

> **Test discipline:** 每个 Task 必须 `RED -> minimal implementation -> GREEN -> targeted regression`。新增/修改 Python/YAML 继续使用高密度中文注释。

---

## Global Constraints

- Framework Core 不识别 DeepSeek / Qwen / OpenAI 等 Provider 名字。
- 第一版只支持 protocol `openai_chat_completions`。
- 同协议新 Provider 只能通过 YAML/CLI 配置接入，不得新增 `if provider == ...`。
- AI 主配置可直接包含真实 Key；这是最终用户本地使用的合法方式。
- 当前公共 GitHub 开发模式下，`config/ai.yaml` 不保存真实 Key，开发者用 `config/ai.local.yaml`。
- `config/ai.local.yaml` 必须被 `.gitignore`。
- CLI 不允许 `--api-key VALUE`；只允许 `--api-key-prompt`。
- Key 不允许进入日志、Artifact、异常文本、`repr`。
- 配置优先级：`CLI > local YAML > main YAML > ENV`。
- 主 YAML 搜索：项目 `config/ai.yaml` 优先，不存在才读用户 Home `~/.ai-api-autotest-framework/ai.yaml`。
- 不修改现有 `core/config_manager.py` 的优先级与行为。
- 不修改 `run.py` 默认测试判定链。
- Jenkins/GitHub 保持可选工程化模式，不成为 Framework Core 依赖。

---

# Task 1 — 修复前阶段 Repository Hygiene 回归

## Files

- Modify: `.gitignore`
- Remove from Git tracking: `.idea/**`
- Create: `tests/integration/test_repository_hygiene.py`

## RED tests

新增：

```python
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).parents[2]


def test_gitignore_protects_ide_and_private_ai_config():
    content = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".idea/" in content
    assert "config/ai.local.yaml" in content


def test_public_tree_does_not_track_idea_directory():
    if not (ROOT / ".git").exists():
        pytest.skip("git metadata is not available in packaged artifact")

    result = subprocess.run(
        ["git", "ls-files", ".idea"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert not result.stdout.strip()
```

Run:

```bash
python -m pytest tests/integration/test_repository_hygiene.py -q
```

Expected RED:

- `.gitignore` 缺 `.idea/`；
- 当前 Git index 仍有 `.idea/**`。

## Minimal implementation

`.gitignore` 增加：

```gitignore
# IDE 本机元数据不属于框架源码。
.idea/

# AI 私有本机覆盖文件可能包含真实 Provider Key，默认禁止提交。
config/ai.local.yaml
```

然后：

```bash
git rm -r --cached .idea
```

不得删除用户本机 IDE 自己重新生成文件的能力，只从 Git tracking 移除。

## GREEN

```bash
python -m pytest tests/integration/test_repository_hygiene.py -q
```

Expected: PASS（worktree 中有 `.git` 时两条均执行）。

---

# Task 2 — 新增 YAML-first `AIConfigResolver`

## Files

- Create: `ai/config.py`
- Create: `tests/ai/test_ai_config.py`
- Create: `config/ai.yaml`

## Public interfaces

```python
class AIConfigError(ValueError):
    ...

@dataclass(frozen=True)
class AIProviderConfig:
    provider: str
    protocol: str
    base_url: str
    model: str
    api_key: str = field(repr=False)
    timeout: float = 20.0

class AIConfigResolver:
    def __init__(
        self,
        project_root: str | Path = PROJECT_ROOT,
        home_dir: str | Path | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        ...

    def resolve(
        self,
        cli_overrides: Mapping[str, Any] | None = None,
        api_key_override: str | None = None,
    ) -> AIProviderConfig | None:
        ...
```

## Required deterministic resolution rules

### Provider selection

```text
CLI provider
> merged YAML ai.provider
> AI_PROVIDER
```

### YAML merge

```text
Primary YAML
+
project config/ai.local.yaml
```

Primary YAML：

```text
project config/ai.yaml
↓ if missing
home ~/.ai-api-autotest-framework/ai.yaml
↓ if missing
{}
```

### Profile field resolution

For `protocol/base_url/model`：

```text
CLI field
> selected merged-YAML profile field
> ENV field
```

For timeout：

```text
CLI timeout
> selected profile.timeout
> YAML ai.timeout
> AI_TIMEOUT
> 20
```

For API Key：

```text
api_key_override（来自 getpass）
> selected YAML profile api_key
> AI_API_KEY
```

`null`、空字符串、纯空白视为 missing。

## RED tests

至少覆盖：

```python
def test_project_ai_yaml_is_primary_source(tmp_path): ...

def test_home_ai_yaml_is_used_only_when_project_yaml_missing(tmp_path): ...

def test_project_local_yaml_overrides_main_yaml(tmp_path): ...

def test_cli_overrides_local_and_main_yaml(tmp_path): ...

def test_yaml_beats_environment_fallback(tmp_path): ...

def test_environment_can_fully_configure_ai_when_yaml_absent(tmp_path): ...

def test_api_key_override_beats_yaml_and_env(tmp_path): ...

def test_provider_not_configured_returns_none(tmp_path): ...

def test_selected_provider_missing_required_fields_raises_safe_error(tmp_path): ...

def test_provider_config_repr_never_contains_api_key(tmp_path): ...

def test_timeout_must_be_positive_number(tmp_path): ...
```

Key test example：

```python
def test_yaml_beats_environment_fallback(tmp_path):
    project = tmp_path / "project"
    (project / "config").mkdir(parents=True)
    (project / "config" / "ai.yaml").write_text(
        """
ai:
  provider: local-profile
  providers:
    local-profile:
      protocol: openai_chat_completions
      base_url: https://yaml.example/v1
      model: yaml-model
      api_key: yaml-secret
""",
        encoding="utf-8",
    )

    resolver = AIConfigResolver(
        project_root=project,
        home_dir=tmp_path / "home",
        environ={
            "AI_PROVIDER": "env-profile",
            "AI_API_BASE": "https://env.example/v1",
            "AI_MODEL": "env-model",
            "AI_API_KEY": "env-secret",
        },
    )

    config = resolver.resolve()
    assert config.provider == "local-profile"
    assert config.base_url == "https://yaml.example/v1"
    assert config.model == "yaml-model"
```

First run:

```bash
python -m pytest tests/ai/test_ai_config.py -q
```

Expected RED: `ai.config` missing.

## `config/ai.yaml`

必须是可直接使用的真实主配置：

```yaml
# AI 辅助能力主配置。
# 最终用户如果不使用 Git，可以直接在本文件填写 Provider / Model / API Key。
# 当前公共仓库为了避免开发者真实 Key 被提交，默认不选择 Provider。

ai:
  # 当前 Provider Profile 名称；null 表示尚未配置 AI。
  provider: null

  # Provider Profile 未声明 timeout 时的 YAML 默认值。
  timeout: 20

  # Provider 名称只是一段用户定义 Profile，不参与 Python 分支判断。
  providers: {}
```

必须补充中文注释，解释 local YAML / ENV fallback / CLI precedence。

## GREEN

```bash
python -m pytest tests/ai/test_ai_config.py -q
```

Expected: all PASS.

---

# Task 3 — 将 Client 从“Provider 环境变量”重构为“Protocol Factory”

## Files

- Modify: `ai/client.py`
- Modify: `tests/ai/test_ai_client.py`
- Modify: `tests/integration/test_ai_architecture_contract.py`

## New interfaces

```python
class OpenAIChatCompletionsClient:
    def __init__(self, *, base_url, api_key, model, timeout=20.0, session=None): ...

class AIClientFactory:
    _PROTOCOLS = {
        "openai_chat_completions": OpenAIChatCompletionsClient,
    }

    @classmethod
    def create(cls, config: AIProviderConfig) -> AIClient:
        ...

# Backward compatibility only
OpenAICompatibleClient = OpenAIChatCompletionsClient
```

删除 Provider 配置职责：

```text
OpenAICompatibleClient.from_env()
```

不得继续成为 CLI 主入口。

可以暂时保留兼容方法仅用于历史调用，但新代码和文档不得使用它；更推荐完全迁移测试后移除 `from_env`，因为 Config Resolver 已成为唯一配置边界。

## RED tests

```python
def test_factory_creates_client_by_protocol_not_provider_name(): ...

def test_same_protocol_supports_arbitrary_provider_profile_names(): ...

def test_factory_rejects_unknown_protocol(): ...

def test_backward_alias_points_to_chat_completions_client(): ...

def test_client_still_never_repairs_invalid_json(): ...
```

Architecture guard：

```python
FORBIDDEN_PROVIDER_BRANCH_TOKENS = (
    'provider == "deepseek"',
    'provider == "qwen"',
    'provider == "openai"',
)
```

还要保留原 Shortlink 硬编码守门。

Run RED：

```bash
python -m pytest tests/ai/test_ai_client.py tests/integration/test_ai_architecture_contract.py -q
```

## GREEN criteria

- Factory 只看 protocol；
- DeepSeek/Qwen/OpenAI profile name 不影响 Factory；
- HTTP request 行为与原 Stage 7.1 不回归；
- API Key 不记录日志。

---

# Task 4 — 重构 `ai.cli` 为 YAML 驱动 + CLI 临时覆盖

## Files

- Modify: `ai/cli.py`
- Modify: `tests/ai/test_ai_cli.py`

## CLI

```text
python -m ai.cli analyze --run-dir PATH
```

Options：

```text
--no-ai
--provider NAME
--protocol NAME
--base-url URL
--model NAME
--timeout SECONDS
--api-key-prompt
```

明确**不提供**：

```text
--api-key VALUE
```

## Execution flow

```text
--no-ai ?
  yes → client=None
  no  → build CLI overrides
        → optional getpass API key
        → AIConfigResolver.resolve()
        → config=None ? client=None
        → otherwise AIClientFactory.create(config)
        → analyze_run()
```

## RED tests

```python
def test_cli_reads_project_ai_yaml_without_environment(monkeypatch, tmp_path): ...

def test_cli_model_override_beats_yaml(monkeypatch, tmp_path): ...

def test_cli_api_key_prompt_uses_getpass_not_argument(monkeypatch, tmp_path): ...

def test_parser_has_no_plain_api_key_argument(): ...

def test_cli_unconfigured_ai_degrades_to_unavailable(...): ...

def test_cli_invalid_ai_config_returns_2_without_secret(...): ...
```

安全断言：

```python
assert "real-secret" not in captured.out
assert "real-secret" not in captured.err
```

## GREEN

```bash
python -m pytest tests/ai/test_ai_cli.py -q
```

---

# Task 5 — 回归 Stage 7.1 既有 Evidence / Sanitizer / Validator

## Files

除非测试发现真实缺陷，不修改：

```text
ai/contracts.py
ai/failure_analyzer.py
utils/sanitizer.py
```

## Verification

```bash
python -m pytest tests/ai -q
```

必须确认：

- FailureEvidence 仍正确；
- SECRET_SENTINEL 仍不会到 Fake Client；
- Fact 引用仍严格校验；
- timeout / invalid_model_output 降级语义不变；
- analysis.json / analysis.md 不泄密。

若失败，先判断是配置接口变更导致测试需要迁移，还是生产逻辑回归；不得为了绿灯削弱原安全测试。

---

# Task 6 — 纠正 Stage 6 / README 的“开发模式 ≠ 用户前提”文档定位

## Files

- Modify: `README.md`
- Modify: `docs/10_CI-CD接入说明.md`
- Modify: `docs/11_AI失败分析接入说明.md`
- Modify: `.env.example`

## README 必须修正

1. 顶部版本从旧 V3.2.6 更新到当前版本；
2. “AI Provider 只从 OS ENV 读取”删除；
3. 增加三个运行模式：

```text
Local Only
Team SCM / Optional Jenkins
Current Public Development (GitHub Actions + Jenkins)
```

4. AI 配置说明：

```text
普通用户：config/ai.yaml
Git 开发者：config/ai.yaml + ignored ai.local.yaml
CI：ENV 可做最后 fallback/secret source
```

5. 明确 Jenkins/GitHub 不是 Framework Core 必需依赖。

## `docs/10_CI-CD接入说明.md`

不能再给读者造成：

> 使用本框架 = 必须 GitHub + Jenkins

必须改成：

> 当前仓库用 GitHub Actions + Jenkins 完成工程验证；最终用户可选择任何 SCM 或完全本地运行。

## `.env.example`

AI 变量注释必须改成：

```text
optional fallback / CI secret
```

而不是主要配置入口。

---

# Task 7 — 更新计划与设计文档，加入前阶段审计结论

## Files

- Add repo spec: `docs/superpowers/specs/2026-08-19-stage7-1-ai-configuration-redesign.md`
- Add repo plan: `docs/superpowers/plans/2026-08-19-stage7-1-ai-configuration-redesign.md`
- Modify: `AI_API_Autotest_Framework_Project_Plan_Latest.md`

## Plan status

```text
Stage 1–5                  ✅ architecture retained
Stage 6 code               ✅ retained
Stage 6 documentation      🔧 corrected in this redesign
Repository hygiene         🔧 .idea regression fixed
Stage 7.1 evidence core    ✅ retained
Stage 7.1 AI config        🔧 redesigned
Stage 7.1 real provider    ⏳ after redesign passes CI
Stage 7.2                  ⏳
```

不得写 Stage 7.1 “fully complete”，直到真实 Provider 再验收成功。

---

# Task 8 — 全量验证

## AI-specific

```bash
python -m pytest tests/ai tests/integration/test_ai_architecture_contract.py tests/integration/test_repository_hygiene.py -q
```

Expected: all PASS.

## Full framework

```bash
python -m pytest tests -q
```

Expected: all PASS, zero regression.

## Original runner

```bash
python run.py --env test --level smoke --run-id stage7-config-redesign-regression
```

Expected:

```text
2 passed, 4 deselected
```

## Compile

```bash
python -m compileall ai core db utils testcases tests run.py
```

Expected exit `0`.

## Core immutability check

```bash
git diff <BASE_COMMIT> -- core/config_manager.py run.py Jenkinsfile
```

Expected: no functional changes.

## Provider hardcoding scan

Production Python 不得出现 vendor branch：

```text
provider == deepseek
provider == qwen
provider == openai
```

## Secret / local file package scan

最终 ZIP 不得包含：

```text
.idea/
config/ai.local.yaml
.env
```

公共 `config/ai.yaml` 不得含真实 Key。

---

# Task 9 — 重新执行真实 Provider 验收

这一 Task **不在公共 CI 中执行**。

开发者本机创建：

```text
config/ai.local.yaml
```

使用真实 Provider Profile + Key。

不设置 `AI_API_*` 环境变量，证明 YAML 独立可用。

运行：

```bash
python -m ai.cli analyze --run-dir tests/fixtures/ai/auth_failure
```

验收：

```text
[ ] CLI exit 0
[ ] ai_status=success
[ ] hypothesis refs 全部指向真实 F#
[ ] evidence/analysis 无 API Key
[ ] 原 run.json/junit.xml 未改
[ ] Python 无 Provider-specific 修改
```

如果第一个 Provider 成功，可选再配置第二个同协议 Provider：

```text
只改 YAML
不改 Python
→ ai_status=success
```

第二 Provider 成功后，可形成更强的“Provider 解耦”工程证据，但不是进入 Stage 7.2 的硬门槛。

---

# Final Gate

只有以下全部满足，才关闭 Stage 7.1：

```text
[ ] YAML-first config completed
[ ] CLI > local YAML > main YAML > ENV verified
[ ] project YAML -> home YAML fallback verified
[ ] API key prompt verified
[ ] no plain --api-key argument
[ ] protocol factory verified
[ ] no vendor branch in production Python
[ ] old Stage 7.1 safety tests remain green
[ ] full framework tests green
[ ] GitHub Actions green
[ ] .idea removed from Git tracking
[ ] ai.local.yaml ignored
[ ] README/CI docs corrected
[ ] one real Provider ai_status=success
```

完成后：

```text
Stage 7.1 ✅ FULLY COMPLETE
→ Stage 7.2 YAML Draft Generation
```
