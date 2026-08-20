"""Stage 7.1 V2 AI YAML-first 配置解析测试。

这里重点验证“框架最终用户直接改 YAML 就能运行”，同时保留 Git 开发者的
``ai.local.yaml`` 私有覆盖和 CI 环境变量 fallback；测试不会写入真实用户 Home。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ai.config import AIConfigError, AIConfigResolver


def _write_yaml(path: Path, text: str) -> None:
    """创建测试配置目录并写入 UTF-8 YAML，减少每个优先级用例的样板代码。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _full_yaml(*, provider: str = "yaml-profile", api_key: str = "yaml-secret") -> str:
    """返回一份完整 YAML Profile；不同测试只覆盖自己真正关心的字段。"""

    return f"""
ai:
  provider: {provider}
  timeout: 25
  providers:
    {provider}:
      protocol: openai_chat_completions
      base_url: https://yaml.example/v1
      model: yaml-model
      api_key: {api_key}
"""


def test_project_ai_yaml_is_primary_source(tmp_path):
    """项目 config/ai.yaml 存在时应直接作为最终用户主配置。"""

    project = tmp_path / "project"
    _write_yaml(project / "config" / "ai.yaml", _full_yaml())

    config = AIConfigResolver(
        project_root=project,
        home_dir=tmp_path / "home",
        environ={},
    ).resolve()

    assert config is not None
    assert config.provider == "yaml-profile"
    assert config.model == "yaml-model"
    assert config.timeout == 25


def test_home_ai_yaml_is_used_only_when_project_yaml_missing(tmp_path):
    """项目没有主配置时才读取用户 Home，避免个人默认配置覆盖项目明确选择。"""

    project = tmp_path / "project"
    home = tmp_path / "home"
    _write_yaml(
        home / ".ai-api-autotest-framework" / "ai.yaml",
        _full_yaml(provider="home-profile", api_key="home-secret"),
    )

    config = AIConfigResolver(project_root=project, home_dir=home, environ={}).resolve()

    assert config is not None
    assert config.provider == "home-profile"
    assert config.api_key == "home-secret"

    # 一旦项目自身出现 ai.yaml，Home 中的默认 Provider 就必须失去主配置地位。
    _write_yaml(project / "config" / "ai.yaml", _full_yaml(provider="project-profile"))
    config = AIConfigResolver(project_root=project, home_dir=home, environ={}).resolve()
    assert config is not None
    assert config.provider == "project-profile"


def test_project_local_yaml_overrides_main_yaml(tmp_path):
    """Git 开发者可把真实 Key/本机差异写进 ignored ai.local.yaml 覆盖公共主配置。"""

    project = tmp_path / "project"
    _write_yaml(project / "config" / "ai.yaml", _full_yaml(api_key="public-placeholder"))
    _write_yaml(
        project / "config" / "ai.local.yaml",
        """
ai:
  providers:
    yaml-profile:
      model: local-model
      api_key: local-secret
""",
    )

    config = AIConfigResolver(project_root=project, home_dir=tmp_path / "home", environ={}).resolve()

    assert config is not None
    assert config.model == "local-model"
    assert config.api_key == "local-secret"
    assert config.base_url == "https://yaml.example/v1"


def test_cli_overrides_local_and_main_yaml(tmp_path):
    """CLI 只作为单次运行临时覆盖，其优先级高于所有 YAML 层。"""

    project = tmp_path / "project"
    _write_yaml(project / "config" / "ai.yaml", _full_yaml())
    _write_yaml(
        project / "config" / "ai.local.yaml",
        """
ai:
  provider: yaml-profile
  providers:
    yaml-profile:
      model: local-model
""",
    )

    config = AIConfigResolver(project_root=project, home_dir=tmp_path / "home", environ={}).resolve(
        cli_overrides={"model": "cli-model", "timeout": 9}
    )

    assert config is not None
    assert config.model == "cli-model"
    assert config.timeout == 9


def test_yaml_beats_environment_fallback(tmp_path):
    """YAML 是用户主入口；环境变量只有 YAML 对应字段缺失时才兜底。"""

    project = tmp_path / "project"
    _write_yaml(project / "config" / "ai.yaml", _full_yaml())

    config = AIConfigResolver(
        project_root=project,
        home_dir=tmp_path / "home",
        environ={
            "AI_PROVIDER": "env-profile",
            "AI_PROTOCOL": "env-protocol",
            "AI_API_BASE": "https://env.example/v1",
            "AI_MODEL": "env-model",
            "AI_API_KEY": "env-secret",
            "AI_TIMEOUT": "99",
        },
    ).resolve()

    assert config is not None
    assert config.provider == "yaml-profile"
    assert config.protocol == "openai_chat_completions"
    assert config.base_url == "https://yaml.example/v1"
    assert config.model == "yaml-model"
    assert config.api_key == "yaml-secret"
    assert config.timeout == 25


def test_environment_can_fully_configure_ai_when_yaml_absent(tmp_path):
    """CI/高级用户仍可完全依赖环境变量，但它只是 fallback 而不是普通用户前提。"""

    config = AIConfigResolver(
        project_root=tmp_path / "project",
        home_dir=tmp_path / "home",
        environ={
            "AI_PROVIDER": "ci-profile",
            "AI_PROTOCOL": "openai_chat_completions",
            "AI_API_BASE": "https://ci.example/v1",
            "AI_MODEL": "ci-model",
            "AI_API_KEY": "ci-secret",
            "AI_TIMEOUT": "12",
        },
    ).resolve()

    assert config is not None
    assert config.provider == "ci-profile"
    assert config.base_url == "https://ci.example/v1"
    assert config.model == "ci-model"
    assert config.api_key == "ci-secret"
    assert config.timeout == 12


def test_api_key_override_beats_yaml_and_env(tmp_path):
    """getpass 得到的临时 Key 通过专用参数注入，优先级最高且不进入普通 CLI 参数。"""

    project = tmp_path / "project"
    _write_yaml(project / "config" / "ai.yaml", _full_yaml())

    config = AIConfigResolver(
        project_root=project,
        home_dir=tmp_path / "home",
        environ={"AI_API_KEY": "env-secret"},
    ).resolve(api_key_override="prompt-secret")

    assert config is not None
    assert config.api_key == "prompt-secret"


def test_provider_not_configured_returns_none(tmp_path):
    """YAML/CLI/ENV 都没选 Provider 时属于“AI 未配置”，必须安全返回 None。"""

    project = tmp_path / "project"
    _write_yaml(
        project / "config" / "ai.yaml",
        """
ai:
  provider: null
  timeout: 20
  providers: {}
""",
    )

    assert AIConfigResolver(project_root=project, home_dir=tmp_path / "home", environ={}).resolve() is None


def test_selected_provider_missing_required_fields_raises_safe_error(tmp_path):
    """已选择 Provider 却缺关键字段属于用户配置错误，错误文本不能回显已有 Key。"""

    project = tmp_path / "project"
    _write_yaml(
        project / "config" / "ai.yaml",
        """
ai:
  provider: broken
  providers:
    broken:
      protocol: openai_chat_completions
      api_key: super-secret-value
""",
    )

    with pytest.raises(AIConfigError) as exc_info:
        AIConfigResolver(project_root=project, home_dir=tmp_path / "home", environ={}).resolve()

    message = str(exc_info.value)
    assert "base_url" in message
    assert "model" in message
    assert "super-secret-value" not in message


def test_provider_config_repr_never_contains_api_key(tmp_path):
    """Dataclass repr 常被日志/调试器展示，因此必须从结构层隐藏真实 Key。"""

    project = tmp_path / "project"
    _write_yaml(project / "config" / "ai.yaml", _full_yaml(api_key="repr-secret"))

    config = AIConfigResolver(project_root=project, home_dir=tmp_path / "home", environ={}).resolve()

    assert config is not None
    assert "repr-secret" not in repr(config)


@pytest.mark.parametrize("timeout", ["0", "-1", "not-a-number"])
def test_timeout_must_be_positive_number(tmp_path, timeout):
    """Timeout 必须为正数，避免 0/负数或非法文本造成难以解释的网络行为。"""

    project = tmp_path / "project"
    _write_yaml(
        project / "config" / "ai.yaml",
        _full_yaml().replace("timeout: 25", f"timeout: {timeout}"),
    )

    with pytest.raises(AIConfigError, match="timeout"):
        AIConfigResolver(project_root=project, home_dir=tmp_path / "home", environ={}).resolve()
