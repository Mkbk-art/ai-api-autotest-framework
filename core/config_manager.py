"""多环境配置加载与覆盖管理。

本模块把 ``config.yaml``、``env.<name>.yaml``、环境变量以及命令行覆盖项
合并成一次测试运行所使用的最终配置。覆盖优先级为：
CLI > 环境变量 > env.<name>.yaml > config.yaml。
"""
from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import yaml

from utils.project_paths import PROJECT_ROOT


def _deep_merge(base: dict[str, Any], override: Mapping[str, Any] | None) -> dict[str, Any]:
    """递归合并配置字典，override 中的值覆盖 base。"""
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, Mapping) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _read_yaml(path: Path, *, required: bool) -> dict[str, Any]:
    """读取 YAML 配置并保证顶层为映射。"""
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Configuration file not found: {path}")
        return {}
    with path.open("r", encoding="utf-8") as file_obj:
        value = yaml.safe_load(file_obj) or {}
    if not isinstance(value, dict):
        raise ValueError(f"Configuration root must be a mapping: {path}")
    return value


def _parse_bool(name: str, value: str) -> bool:
    """把常见环境变量布尔文本转换为 bool，并拒绝模糊值。"""
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value, got {value!r}")


class ConfigManager:
    """加载并合并一次测试运行所需的多环境配置。"""

    def __init__(
        self,
        project_root: str | Path = PROJECT_ROOT,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        """保存项目根目录以及可注入的环境变量映射，便于单元测试。"""
        self.project_root = Path(project_root).resolve()
        self.environ = os.environ if environ is None else environ

    def _environment_overrides(self) -> dict[str, Any]:
        """把受支持的环境变量转换为框架配置结构。"""
        result: dict[str, Any] = {}
        if value := self.environ.get("API_HOST"):
            result.setdefault("api", {})["host"] = value
        if value := self.environ.get("API_TIMEOUT"):
            try:
                result.setdefault("api", {})["timeout"] = float(value)
            except ValueError as exc:
                raise ValueError(f"API_TIMEOUT must be numeric, got {value!r}") from exc
        if value := self.environ.get("API_VERIFY_SSL"):
            result.setdefault("api", {})["verify_ssl"] = _parse_bool("API_VERIFY_SSL", value)
        if value := self.environ.get("API_USE_MOCK"):
            result.setdefault("api", {})["use_mock"] = _parse_bool("API_USE_MOCK", value)
        if value := self.environ.get("LOG_LEVEL"):
            result.setdefault("log", {})["level"] = value.upper()
        return result

    def load(
        self,
        env_name: str = "test",
        cli_overrides: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """按约定优先级生成最终配置。

        Args:
            env_name: 环境名称，例如 ``test`` 或 ``stage``。
            cli_overrides: ``run.py`` 解析出的命令行临时覆盖值。
        """
        config_dir = self.project_root / "config"
        defaults = _read_yaml(config_dir / "config.yaml", required=True)
        named = _read_yaml(config_dir / f"env.{env_name}.yaml", required=False)
        merged = _deep_merge(defaults, named)
        merged = _deep_merge(merged, self._environment_overrides())
        merged = _deep_merge(merged, cli_overrides)
        merged["environment"] = env_name
        return merged
