"""多环境配置加载与覆盖管理。

本模块把 ``config.yaml``、公开的 ``env.<name>.yaml``、可选的仓库外环境覆盖 YAML、
环境变量以及命令行覆盖项合并成一次测试运行所使用的最终配置。覆盖优先级为：
CLI > 环境变量 > 外部环境 YAML > env.<name>.yaml > config.yaml。

外部环境 YAML 的核心用途是保存“本机/CI 私有差异”，例如真实测试账号、数据库密码
或某台 Jenkins Agent 独有的地址。它可以只包含需要覆盖的少数字段，不要求复制整份
公开环境配置；因此真实项目的 ``env.<name>.yaml`` 仍然可以保留占位符后提交到 Git，
作为框架接入示例供其他项目复用。
"""
from __future__ import annotations

# os.environ 是本地命令行、Jenkins 等运行环境向框架传递非业务级运行参数的统一入口。
import os
# deepcopy 保证多层字典合并时不会修改任何原始配置对象，避免测试会话之间串数据。
from copy import deepcopy
# Path 统一处理项目内命名环境文件和仓库外绝对/相对 YAML 路径。
from pathlib import Path
# Mapping/Any 用于表达 ConfigManager 接受的通用嵌套配置结构。
from typing import Any, Mapping

# PyYAML 只负责把 UTF-8 YAML 解析成 Python 映射；业务字段含义由具体项目自己定义。
import yaml

# PROJECT_ROOT 让默认配置解析不依赖调用者当前工作目录。
from utils.project_paths import PROJECT_ROOT


# Jenkins、本地 CLI 与其他 CI 共用这一“文件路径”变量；变量只保存路径，不保存账号或密码值。
_EXTERNAL_ENV_FILE_VAR = "API_TEST_ENV_FILE"


def _deep_merge(base: dict[str, Any], override: Mapping[str, Any] | None) -> dict[str, Any]:
    """递归合并配置字典，``override`` 中出现的字段覆盖 ``base`` 对应字段。

    对于嵌套 Mapping 继续递归，以便外部私有 YAML 只写 ``password`` 这类少数字段时，
    仍能保留公开环境文件中同级的 host、port、suite 等非敏感配置。
    """
    # 每层都复制 base，调用者传入的字典不会因为本次运行的覆盖操作被原地修改。
    result = deepcopy(base)
    for key, value in (override or {}).items():
        # 只有两侧都是映射时才递归；标量、列表等按“新层覆盖旧层”直接替换。
        if isinstance(value, Mapping) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _read_yaml(path: Path, *, required: bool) -> dict[str, Any]:
    """按 UTF-8 读取 YAML，并保证顶层结构是映射。

    ``required=True`` 用于公共默认配置以及用户显式指定的外部覆盖文件：这两类文件缺失
    都应立即失败。命名环境文件仍保持历史兼容，可在不存在时返回空映射。
    """
    if not path.exists():
        if required:
            # 失败信息包含实际解析路径，Jenkins 控制台可以直接据此检查 Agent 文件位置。
            raise FileNotFoundError(f"Configuration file not found: {path}")
        return {}
    # 所有项目 YAML 都统一使用 UTF-8，避免 Windows 中文区域设置回退到 GBK/CP936。
    with path.open("r", encoding="utf-8") as file_obj:
        value = yaml.safe_load(file_obj) or {}
    # 框架的配置合并只支持键值映射；列表/字符串作为根节点无法定义 section.key 语义。
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
    """加载并合并一次测试运行所需的框架/项目环境配置。"""

    def __init__(
        self,
        project_root: str | Path = PROJECT_ROOT,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        """保存项目根目录以及可注入的环境变量映射，便于单元测试。

        Args:
            project_root: 框架仓库根目录；相对 ``env_file`` 会以这里为基准解析。
            environ: 可替换的环境变量映射；默认使用当前进程 ``os.environ``。
        """
        # resolve 固化项目根路径，后续从任何工作目录启动都能稳定找到 config/。
        self.project_root = Path(project_root).resolve()
        # 测试可传普通 dict，避免单元测试污染机器真实环境变量。
        self.environ = os.environ if environ is None else environ

    def _environment_overrides(self) -> dict[str, Any]:
        """把受支持的非文件环境变量转换为框架配置结构。"""
        result: dict[str, Any] = {}
        # API_HOST 等是框架历史支持的临时运行覆盖；它们优先级高于所有 YAML 层。
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
        # API_TEST_ENV_FILE 本身只是“另一层 YAML 的路径”，不能被合并成业务配置字段。
        return result

    def _resolve_external_env_file(self, env_file: str | Path | None) -> Path | None:
        """解析显式 ``env_file`` 或 ``API_TEST_ENV_FILE`` 指向的外部覆盖 YAML。

        显式函数参数优先于环境变量；空字符串视为“未启用”。相对路径统一以项目根目录
        为基准，这样本地、Jenkins 与其他 CI 从不同当前目录启动时语义仍然一致。
        """
        # CLI/run.py 显式传入时优先；没有显式参数才读取 Jenkins 等注入的通用路径变量。
        raw_value: str | Path | None = env_file
        if raw_value is None:
            raw_value = self.environ.get(_EXTERNAL_ENV_FILE_VAR)
        # Jenkins 参数默认空字符串时不启用外部层，保持现有 Mock/公开环境行为完全不变。
        if raw_value is None or not str(raw_value).strip():
            return None

        candidate = Path(str(raw_value).strip()).expanduser()
        # 相对路径以 project_root 为基准；绝对路径则可直接指向仓库外私有目录。
        if not candidate.is_absolute():
            candidate = self.project_root / candidate
        return candidate.resolve()

    def load(
        self,
        env_name: str = "test",
        env_file: str | Path | None = None,
        cli_overrides: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """按稳定优先级生成本次运行的最终配置。

        Args:
            env_name: 公开命名环境，例如 ``test``、``stage`` 或任意真实项目环境名称。
            env_file: 可选的外部覆盖 YAML 路径；可只包含真实凭据/本机差异。
            cli_overrides: ``run.py`` 解析出的 API 等临时覆盖值。

        Returns:
            合并后的普通字典。具体项目字段保持原样，框架不会理解或硬编码其业务含义。
        """
        config_dir = self.project_root / "config"
        # 第一层是框架公共默认配置，必须存在。
        defaults = _read_yaml(config_dir / "config.yaml", required=True)
        # 第二层是可公开提交的命名环境；真实项目可以在这里保留 CHANGE_ME 一类占位符。
        named = _read_yaml(config_dir / f"env.{env_name}.yaml", required=False)
        # 第三层是可选仓库外私有覆盖；显式配置后缺失必须 fail-fast，不能静默回退占位符。
        external_path = self._resolve_external_env_file(env_file)
        external = _read_yaml(external_path, required=True) if external_path is not None else {}

        # 合并顺序从低优先级到高优先级，最后一个覆盖层拥有最终决定权。
        merged = _deep_merge(defaults, named)
        merged = _deep_merge(merged, external)
        merged = _deep_merge(merged, self._environment_overrides())
        merged = _deep_merge(merged, cli_overrides)
        # environment 仅记录逻辑环境名；不把私有文件路径或敏感内容写入配置证据。
        merged["environment"] = env_name
        return merged
