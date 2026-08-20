"""Stage 7.1 V2 AI YAML-first 配置解析器。

本模块只负责“如何找到并合并 AI Provider 配置”，不负责发起模型请求，也不理解
DeepSeek、Qwen、OpenAI 等厂商名称。最终用户可以只修改项目 ``config/ai.yaml``
直接运行；使用 Git 的开发者可以额外通过被忽略的 ``config/ai.local.yaml`` 保存真实
Key；CI/高级用户仍可把 ``AI_*`` 环境变量作为最后 fallback。

最终字段优先级固定为：``CLI > ai.local.yaml > 主 YAML > ENV``。主 YAML 本身按
``项目 config/ai.yaml > 用户 Home ~/.ai-api-autotest-framework/ai.yaml`` 查找；项目主
配置存在时不会再读取 Home 主配置，避免个人默认值覆盖项目明确选择。
"""
from __future__ import annotations

# os.environ 只作为最后 fallback；普通用户不需要为了使用 AI 去配置系统环境变量。
import os
# deepcopy 防止多层 YAML merge 原地修改调用者对象，保持测试/多次解析彼此隔离。
from copy import deepcopy
# dataclass 固化最终 Provider 配置；field(repr=False) 从结构层阻止 Key 出现在 repr/log 中。
from dataclasses import dataclass, field
# Path 统一解析项目配置和用户 Home 配置，不依赖调用命令时的当前工作目录。
from pathlib import Path
# Any/Mapping 表达 YAML 与 CLI 的通用映射，同时便于单元测试注入独立环境变量字典。
from typing import Any, Mapping

# PyYAML 是框架既有依赖；AI 配置与普通测试 YAML 使用同样的 UTF-8 解析习惯。
import yaml

# PROJECT_ROOT 让默认项目配置定位与框架其他模块保持一致。
from utils.project_paths import PROJECT_ROOT


class AIConfigError(ValueError):
    """AI 配置已被用户启用但字段缺失、类型错误或值非法。"""


@dataclass(frozen=True)
class AIProviderConfig:
    """一次 AI 分析真正需要的 Provider 运行配置。

    ``provider`` 只是用户定义的 Profile 名；production code 不根据它选择厂商逻辑。
    真正决定客户端实现的是 ``protocol``。``api_key`` 明确禁止进入 dataclass repr，避免
    调试日志、异常上下文或 IDE 自动展示时无意泄露。
    """

    provider: str
    protocol: str
    base_url: str
    model: str
    api_key: str = field(repr=False)
    timeout: float = 20.0


def _is_missing(value: Any) -> bool:
    """把 YAML null、空字符串和纯空白统一视为“未配置”，方便逐层 fallback。"""

    return value is None or (isinstance(value, str) and not value.strip())


def _clean_text(value: Any) -> str | None:
    """把可用标量转换成去空白文本；缺失值返回 None。"""

    if _is_missing(value):
        return None
    return str(value).strip()


def _deep_merge(base: Mapping[str, Any] | None, override: Mapping[str, Any] | None) -> dict[str, Any]:
    """递归合并 YAML 映射，让 ai.local.yaml 只写 Key/模型等少数字段即可覆盖主配置。"""

    result: dict[str, Any] = deepcopy(dict(base or {}))
    for key, value in (override or {}).items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _read_yaml(path: Path, *, required: bool = False) -> dict[str, Any]:
    """读取 UTF-8 YAML 并要求顶层为 Mapping；可选文件缺失时返回空映射。"""

    if not path.is_file():
        if required:
            raise AIConfigError(f"AI configuration file not found: {path}")
        return {}
    try:
        with path.open("r", encoding="utf-8") as file_obj:
            value = yaml.safe_load(file_obj) or {}
    except (OSError, yaml.YAMLError) as exc:
        # 不把文件内容拼进异常，只提供路径，避免坏 YAML 中的 secret 被间接回显。
        raise AIConfigError(f"Unable to read AI configuration: {path}") from exc
    if not isinstance(value, dict):
        raise AIConfigError(f"AI configuration root must be a mapping: {path}")
    return value


def _positive_timeout(value: Any) -> float:
    """把 YAML/CLI/ENV timeout 转为正浮点数，并给出不包含其他配置值的安全错误。"""

    try:
        timeout = float(value)
    except (TypeError, ValueError) as exc:
        raise AIConfigError("AI timeout must be a positive number") from exc
    if timeout <= 0:
        raise AIConfigError("AI timeout must be a positive number")
    return timeout


class AIConfigResolver:
    """按最终用户优先的规则解析一次 AI Provider 配置。"""

    def __init__(
        self,
        project_root: str | Path = PROJECT_ROOT,
        home_dir: str | Path | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        """保存配置搜索根目录和可注入环境变量映射。

        Args:
            project_root: 当前框架/项目根目录，优先搜索 ``config/ai.yaml``。
            home_dir: 用户 Home；测试可注入临时目录，默认使用 ``Path.home()``。
            environ: 环境变量 fallback；测试传 dict 可避免污染真实 OS 环境。
        """

        self.project_root = Path(project_root).expanduser().resolve()
        self.home_dir = (Path.home() if home_dir is None else Path(home_dir)).expanduser().resolve()
        self.environ = os.environ if environ is None else environ

    def _load_yaml_layers(self) -> dict[str, Any]:
        """读取一个主 YAML，再叠加项目级 ai.local.yaml 私有覆盖。"""

        project_main = self.project_root / "config" / "ai.yaml"
        home_main = self.home_dir / ".ai-api-autotest-framework" / "ai.yaml"
        local_override = self.project_root / "config" / "ai.local.yaml"

        # 项目 ai.yaml 一旦存在就拥有主配置权；只有完全不存在时才读取用户 Home 默认配置。
        primary = _read_yaml(project_main) if project_main.is_file() else _read_yaml(home_main)
        # local 文件是“覆盖层”而非第二套主配置；即使主配置来自 Home，它仍可覆盖当前项目差异。
        local = _read_yaml(local_override)
        return _deep_merge(primary, local)

    def resolve(
        self,
        cli_overrides: Mapping[str, Any] | None = None,
        api_key_override: str | None = None,
    ) -> AIProviderConfig | None:
        """解析最终 Provider 配置；完全未选择 Provider 时返回 None 安全降级。

        ``cli_overrides`` 只接受 provider/protocol/base_url/model/timeout 等非 Secret 临时覆盖；
        Key 的最高优先级通过单独 ``api_key_override`` 传入，供 CLI ``getpass`` 使用，从接口
        设计上避免实现 ``--api-key VALUE`` 这种会进入 shell history 的危险参数。
        """

        cli = dict(cli_overrides or {})
        merged = self._load_yaml_layers()
        ai_section = merged.get("ai") or {}
        if not isinstance(ai_section, Mapping):
            raise AIConfigError("AI configuration section 'ai' must be a mapping")

        providers = ai_section.get("providers") or {}
        if not isinstance(providers, Mapping):
            raise AIConfigError("AI configuration 'ai.providers' must be a mapping")

        # Provider 本身也遵循 CLI > YAML > ENV；没有 Provider 表示用户没有启用 AI，而不是错误。
        provider = (
            _clean_text(cli.get("provider"))
            or _clean_text(ai_section.get("provider"))
            or _clean_text(self.environ.get("AI_PROVIDER"))
        )
        if provider is None:
            return None

        raw_profile = providers.get(provider) or {}
        if not isinstance(raw_profile, Mapping):
            raise AIConfigError(f"AI provider profile '{provider}' must be a mapping")
        profile = dict(raw_profile)

        # 非 Secret 字段统一执行 CLI > selected YAML profile > ENV fallback。
        protocol = (
            _clean_text(cli.get("protocol"))
            or _clean_text(profile.get("protocol"))
            or _clean_text(self.environ.get("AI_PROTOCOL"))
        )
        base_url = (
            _clean_text(cli.get("base_url"))
            or _clean_text(profile.get("base_url"))
            or _clean_text(self.environ.get("AI_API_BASE"))
        )
        model = (
            _clean_text(cli.get("model"))
            or _clean_text(profile.get("model"))
            or _clean_text(self.environ.get("AI_MODEL"))
        )

        # Timeout 多一层 YAML ai.timeout 共享默认值；只有 YAML 未配置时才读取 AI_TIMEOUT。
        timeout_raw = cli.get("timeout")
        if _is_missing(timeout_raw):
            timeout_raw = profile.get("timeout")
        if _is_missing(timeout_raw):
            timeout_raw = ai_section.get("timeout")
        if _is_missing(timeout_raw):
            timeout_raw = self.environ.get("AI_TIMEOUT")
        if _is_missing(timeout_raw):
            timeout_raw = 20
        timeout = _positive_timeout(timeout_raw)

        # Key 不支持普通 CLI 参数。getpass override > YAML profile > ENV fallback。
        api_key = (
            _clean_text(api_key_override)
            or _clean_text(profile.get("api_key"))
            or _clean_text(self.environ.get("AI_API_KEY"))
        )

        missing = [
            name
            for name, value in (
                ("protocol", protocol),
                ("base_url", base_url),
                ("model", model),
                ("api_key", api_key),
            )
            if value is None
        ]
        if missing:
            # 只列字段名，不拼 profile dict 或现有值，避免部分配置中的 Key 进入异常文本。
            raise AIConfigError(
                f"AI provider profile '{provider}' is missing required fields: {', '.join(missing)}"
            )

        return AIProviderConfig(
            provider=provider,
            protocol=protocol,
            base_url=base_url,
            model=model,
            api_key=api_key,
            timeout=timeout,
        )
