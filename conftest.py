"""所有被测项目共享的 Pytest 运行夹具与 collection glue。

这里仅保存框架级 fixture：环境配置、Mock Server、ApiRunner 和 VariableContext。
具体项目的登录、前置资源、清理逻辑放在各自 ``testcases/<suite>/context.py``，复杂控制流
放在 ``workflows/``；当前要收集哪个 suite 由 ``env.<name>.yaml -> test_selection.include_suites`` 声明。
因此新增真实项目时只增加环境 YAML 和测试目录，不需要修改本公共文件。
"""
from __future__ import annotations

# API_TEST_ENV 由 run.py 设置；直接运行 pytest 时默认使用 test 环境。
import importlib
import os
# Path 用于扫描各项目 YAML 并在 collection 前自动注册它们声明的 markers。
from pathlib import Path
from typing import Any

# Pytest 提供 collection hooks 与通用 fixture 生命周期。
import pytest

# ApiRunner 是所有项目共享的 YAML 请求/提取/断言执行入口。
from core.api_runner import ApiRunner
from core.case_executor import CaseExecutor
from core.case_registry import CaseRegistry
from core.case_spec import CaseSpecError, load_case_specs
from core.context_provider import CaseHookRegistry, ContextProviderRegistry
# 旧版 YAML Marker Loader 仅在 Shortlink V1 迁移期间提供兼容；V2 直接读取 CaseSpec。
from core.case_loader import get_testcase_marker_names
# ConfigManager 负责合并 config.yaml 与当前命名环境 YAML。
from core.config_manager import ConfigManager
# VariableContext 保证每条测试的动态变量互相隔离。
from core.variable_context import VariableContext
# MockApiServer 只由 use_mock=true 的环境按需启动。
from mock_server.server import MockApiServer
# PROJECT_ROOT 让 YAML marker 扫描不依赖启动命令的当前工作目录。
from utils.project_paths import PROJECT_ROOT


def _hook_runtime_config(config) -> dict[str, Any]:
    """为 collection hooks 缓存当前环境配置，避免每个路径重复读取 YAML。"""
    # Pytest Config 对象贯穿整个会话，适合作为 collection 阶段的只读缓存载体。
    cached = getattr(config, "_api_autotest_runtime_config", None)
    if isinstance(cached, dict):
        return cached
    # 环境名只决定“读取哪份环境 YAML”，具体 suite 名称不在 Python 中写死。
    env_name = os.environ.get("API_TEST_ENV", "test")
    runtime = ConfigManager().load(env_name)
    # setattr 只保存内部缓存，不会改变 ConfigManager 的正式配置结构。
    setattr(config, "_api_autotest_runtime_config", runtime)
    return runtime


def _include_suites(config) -> set[str]:
    """读取当前环境允许收集的 testcases 一级 suite；空集合表示不做目录过滤。"""
    runtime = _hook_runtime_config(config)
    # test_selection 是框架通用 collection 配置，不携带任何具体业务含义。
    selection = runtime.get("test_selection", {})
    if not isinstance(selection, dict):
        raise ValueError("test_selection must be a mapping")
    # include_suites 由环境 YAML 声明，例如一个本地环境只接入某个真实 SUT suite。
    values = selection.get("include_suites", [])
    if values in (None, []):
        return set()
    if not isinstance(values, list) or not all(
        isinstance(item, str) and item.strip() for item in values
    ):
        raise ValueError("test_selection.include_suites must be a list of non-empty strings")
    # 标准化后返回集合，collection 判断只关心成员关系。
    return {item.strip() for item in values}


def _suite_name_from_path(collection_path: Path) -> str | None:
    """从 ``testcases/<suite>/...`` 路径提取一级 suite 名；共享文件返回 None。"""
    try:
        # resolve 后用 relative_to 限定在 testcases 根目录内，tests/ 等框架测试不会被过滤。
        relative = Path(collection_path).resolve().relative_to((PROJECT_ROOT / "testcases").resolve())
    except ValueError:
        return None
    # 顶层 conftest.py / __init__.py 没有项目 suite，不参与 include_suites 判断。
    if len(relative.parts) < 2:
        return None
    # 第一个目录名就是 suite；新项目只需创建 testcases/<new_suite>/。
    return relative.parts[0]


def _selected_project_case_paths(config) -> list[Path]:
    """返回当前环境选择项目下的 V2 YAML 路径。"""
    included = _include_suites(config)
    roots: list[Path]
    if included:
        roots = [PROJECT_ROOT / "testcases" / name / "yaml" for name in sorted(included)]
    else:
        roots = [path / "yaml" for path in sorted((PROJECT_ROOT / "testcases").iterdir()) if path.is_dir()]

    paths: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for yaml_path in sorted(root.glob("*.yaml")):
            try:
                load_case_specs(yaml_path)
            except CaseSpecError:
                # 迁移期允许项目目录中暂时存在 V1；Generic Runtime 只执行已经升级到 V2 的文件。
                continue
            paths.append(yaml_path)
    return paths


def _case_registry(config) -> CaseRegistry:
    """为当前环境缓存声明式 CaseRegistry。"""
    cached = getattr(config, "_api_autotest_case_registry", None)
    if isinstance(cached, CaseRegistry):
        return cached
    registry = CaseRegistry.from_paths(_selected_project_case_paths(config))
    setattr(config, "_api_autotest_case_registry", registry)
    return registry


def pytest_generate_tests(metafunc) -> None:
    """把当前项目全部 declarative Case 注入唯一 Generic Pytest Runtime。"""
    if "yaml_case" not in metafunc.fixturenames:
        return
    registry = _case_registry(metafunc.config)
    params = []
    for case in registry.declarative_cases():
        marks = [getattr(pytest.mark, name) for name in case.marker_names]
        params.append(pytest.param(case, marks=marks, id=case.case_id))
    metafunc.parametrize("yaml_case", params)


def pytest_configure(config) -> None:
    """在严格 marker 校验前，从全部项目 YAML 动态注册 level/tags。"""
    # 先缓存环境配置，后续 ignore_collect 与 fixtures 使用同一命名环境来源。
    _hook_runtime_config(config)
    # 只扫描约定的 testcases/<suite>/yaml/*.yaml。项目还可以拥有 contract/、fixtures/ 等其他 YAML，
    # 这些不是 Test Specification，不能因为扩展项目资产就被 Pytest marker 注册逻辑误解析。
    yaml_files = sorted((PROJECT_ROOT / "testcases").glob("*/yaml/*.yaml"))
    marker_names: set[str] = set()
    for yaml_path in yaml_files:
        try:
            specs = load_case_specs(yaml_path)
        except CaseSpecError:
            # V1 只作为迁移兼容；完成迁移后该分支可删除。
            marker_names.update(get_testcase_marker_names(yaml_path))
        else:
            for case in specs:
                marker_names.update(case.marker_names)
    # addinivalue_line 是 Pytest 官方动态 marker 注册入口，可继续配合 --strict-markers。
    for name in sorted(marker_names):
        config.addinivalue_line("markers", f"{name}: marker declared by YAML testcase metadata")


def pytest_ignore_collect(collection_path, config):
    """按环境 YAML 的 include_suites 隔离不同真实项目/Mock 示例测试目录。"""
    # 空 include_suites 表示用户显式选择 --test-path 或希望收集所有 suite，不做额外过滤。
    included = _include_suites(config)
    if not included:
        return None
    # 只过滤 testcases 下的一级项目目录；tests/ 下的框架单元/集成测试永远不受影响。
    suite_name = _suite_name_from_path(Path(collection_path))
    if suite_name is None:
        return None
    # 当前目录不在环境 YAML 白名单时让 Pytest 跳过整个 suite。
    return suite_name not in included


@pytest.fixture(scope="session")
def case_registry(request):
    """返回当前环境声明式 Case 的统一 Registry。"""
    return _case_registry(request.config)


@pytest.fixture(scope="session")
def project_extensions(request):
    """按环境选择的项目加载 Context Provider 与 Case Hook。"""
    providers = ContextProviderRegistry()
    hooks = CaseHookRegistry()
    for project_name in sorted(_include_suites(request.config)):
        module_name = f"testcases.{project_name}.context"
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name == module_name:
                continue
            raise
        register = getattr(module, "register_extensions", None)
        if register is not None:
            register(providers, hooks)
    return providers, hooks


@pytest.fixture
def case_executor(request_base, case_registry, project_extensions):
    """为当前 Pytest Item 创建统一 CaseExecutor，并保证 Provider cleanup 被执行。"""
    providers, hooks = project_extensions
    with CaseExecutor(
        runner=request_base,
        registry=case_registry,
        providers=providers,
        hooks=hooks,
    ) as executor:
        yield executor


@pytest.fixture
def variable_context():
    """为每条业务测试创建独立的内存变量上下文。"""
    # function scope 是默认值；不同测试不会共享 token/id 等运行时数据。
    return VariableContext()


@pytest.fixture(scope="session")
def runtime_config():
    """在整个 Pytest 会话中加载一次当前命名环境配置。"""
    # 与 collection hooks 使用相同 API_TEST_ENV，保证配置和用例目录选择属于同一环境。
    env_name = os.environ.get("API_TEST_ENV", "test")
    return ConfigManager().load(env_name)


@pytest.fixture(scope="session")
def mock_api_server(runtime_config):
    """仅在当前环境 ``api.use_mock=true`` 时启动受控 Mock Server。"""
    # 真实项目环境返回 None，不会无意启动第二套服务或修改真实 API host。
    if not runtime_config.get("api", {}).get("use_mock", False):
        yield None
        return
    # Mock Server 生命周期覆盖当前会话，多个 Demo Case 共用同一个随机本地端口。
    with MockApiServer() as server:
        yield server


@pytest.fixture(scope="session")
def api_host(runtime_config, mock_api_server):
    """返回本次运行真正交给 ApiRunner 的 API 根地址。"""
    # Mock 环境优先使用动态端口；真实环境直接读取 env.<name>.yaml 中的 api.host。
    if mock_api_server is not None:
        return mock_api_server.url
    return runtime_config["api"]["host"]


@pytest.fixture
def request_base(api_host, runtime_config, variable_context):
    """构造当前测试专属 ApiRunner，并注入同一份环境配置与变量上下文。"""
    # timeout/TLS 等网络策略都是环境配置，不由具体项目测试函数重复维护。
    api = runtime_config.get("api", {})
    return ApiRunner(
        host=api_host,
        timeout=float(api.get("timeout", 30)),
        verify_ssl=bool(api.get("verify_ssl", True)),
        context=variable_context,
        runtime_config=runtime_config,
    )
