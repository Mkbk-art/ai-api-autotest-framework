"""Stage 4 真实业务代码的注释质量守护测试。

用户要求后续交付的 Python/YAML 代码必须带完整中文说明。这个测试不评价注释文字是否
“漂亮”，而是守住两个可自动检查的最低标准：Python 业务模块必须有模块 docstring 且
保持足够的解释性注释密度；真实 YAML 用例也必须有高密度 ``#`` 注释。这样以后新增
Stage 4 文件时，如果又退化成“只有代码没有说明”，框架测试会主动失败提醒。
"""

# ast 用于可靠判断 Python 文件是否存在模块级 docstring。
import ast
# Path 用于遍历 Stage 4 业务 Python 和 YAML 文件。
from pathlib import Path

# PROJECT_ROOT 保证测试不依赖执行时工作目录。
from utils.project_paths import PROJECT_ROOT


# 真实业务 Python 文件所在目录。
SHORTLINK_PY_DIR = PROJECT_ROOT / "testcases" / "shortlink"
# 真实 YAML 用例所在目录。
SHORTLINK_YAML_DIR = PROJECT_ROOT / "testcases" / "shortlink" / "yaml"


def _comment_ratio(path: Path) -> float:
    """计算文件中独立注释行占全部非空行的比例。"""

    # 使用 UTF-8 读取，确保中文注释在 Windows/Linux 上都能稳定解析。
    lines = path.read_text(encoding="utf-8").splitlines()
    # 空行只用于排版，不参与注释密度计算。
    nonblank = [line for line in lines if line.strip()]
    # 这里只统计以 # 开头的解释性注释，不把 docstring 或代码尾注释重复计入。
    comments = [line for line in nonblank if line.lstrip().startswith("#")]
    # 空文件没有解释价值，比例按 0 处理。
    return len(comments) / len(nonblank) if nonblank else 0.0


def test_stage4_python_business_files_keep_module_docs_and_dense_comments():
    """Stage 4 Python 业务文件应保持模块说明和至少 20% 的独立注释行。"""

    # __init__.py 只负责包声明，不要求达到业务文件的高密度注释阈值。
    python_files = sorted(path for path in SHORTLINK_PY_DIR.glob("*.py") if path.name != "__init__.py")
    # 当前 Stage 4 必须至少存在一个真实业务 Python 文件，否则扫描本身没有意义。
    assert python_files

    # 逐个检查所有真实业务模块，防止未来新增文件遗漏说明。
    for path in python_files:
        # ast.parse 同时验证文件可被 Python 语法解析。
        module = ast.parse(path.read_text(encoding="utf-8"))
        # 每个业务模块顶部必须有明确的模块用途 docstring。
        assert ast.get_docstring(module), f"missing module docstring: {path}"
        # 20% 是最低守护阈值；当前实际文件大多明显高于该比例。
        assert _comment_ratio(path) >= 0.20, f"insufficient explanatory comments: {path}"


def test_stage4_yaml_cases_keep_dense_field_comments():
    """真实 YAML 用例应保持至少 35% 的独立注释行，解释接口字段和业务原因。"""

    # 收集全部 shortlink YAML，未来新增 Redirect/Cleanup 等用例会自动进入检查范围。
    yaml_files = sorted(SHORTLINK_YAML_DIR.glob("*.yaml"))
    # 没有真实 YAML 时应失败，避免误把空目录当成“注释检查通过”。
    assert yaml_files

    # 每个 YAML 都必须达到高于 Python 的注释比例，因为字段本身没有 docstring 可承载说明。
    for path in yaml_files:
        assert _comment_ratio(path) >= 0.35, f"insufficient YAML field comments: {path}"


# Stage 5 本次真正修改/新增的通用框架文件。这里故意不扫描全部历史模块，
# 只守住本次交付边界，避免为了满足比例去给未改动的旧代码机械补注释。
STAGE5_GENERIC_FILES = [
    PROJECT_ROOT / "core" / "api_runner.py",
    PROJECT_ROOT / "core" / "assertion_engine.py",
    PROJECT_ROOT / "core" / "case_loader.py",
    PROJECT_ROOT / "db" / "mysql_client.py",
    PROJECT_ROOT / "db" / "redis_client.py",
    PROJECT_ROOT / "utils" / "debugtalk.py",
    PROJECT_ROOT / "utils" / "sharding.py",
    PROJECT_ROOT / "conftest.py",
    PROJECT_ROOT / "testcases" / "demo" / "conftest.py",
]


def test_stage5_modified_generic_files_keep_dense_chinese_explanations():
    """Stage 5 通用框架改动也必须保留模块说明和高密度解释性注释。"""

    # 这些文件组成 Stage 5 的可复用能力边界；任意一个丢失都意味着交付结构不完整。
    for path in STAGE5_GENERIC_FILES:
        assert path.is_file(), f"missing Stage 5 generic module: {path}"
        # 模块 docstring 负责说明整体职责，独立注释负责解释关键分支、数据源和安全原因。
        module = ast.parse(path.read_text(encoding="utf-8"))
        assert ast.get_docstring(module), f"missing module docstring: {path}"
        # 通用核心逻辑分支较多，阈值略低于业务适配层，但仍要求至少 15% 的解释性注释行。
        assert _comment_ratio(path) >= 0.15, f"insufficient Stage 5 explanatory comments: {path}"


# 本次 Stage 5 也修改了环境 YAML；它们承担 suite 选择、数据源和项目参数说明。
STAGE5_ENV_YAMLS = [
    PROJECT_ROOT / "config" / "config.yaml",
    PROJECT_ROOT / "config" / "env_template.yaml",
    PROJECT_ROOT / "config" / "env.test.yaml",
    PROJECT_ROOT / "config" / "env.shortlink-local.yaml",
]


def test_stage5_modified_environment_yaml_keeps_field_level_comments():
    """环境 YAML 也必须解释 suite、数据源和项目参数来源，不能只剩裸配置值。"""

    # 30% 是环境 YAML 的最低解释密度；当前两份配置实际明显高于此阈值。
    for path in STAGE5_ENV_YAMLS:
        assert path.is_file(), f"missing Stage 5 environment YAML: {path}"
        assert _comment_ratio(path) >= 0.30, f"insufficient environment YAML comments: {path}"
