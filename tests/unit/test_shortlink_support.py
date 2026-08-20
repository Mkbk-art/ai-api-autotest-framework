"""短链接项目适配层的离线单元测试。

这些测试只保护“真实项目如何接入通用框架”的边界：业务常量来自项目 YAML、分片和 Redis
Key 只在 adapter 层计算、Create 前置复用归类后的 link.yaml。通用 DB/Redis 能力另由
``test_data_sources.py`` 与 ``test_assertion_engine.py`` 验证。
"""
from __future__ import annotations

import json
from pathlib import Path

from core.api_runner import ApiRunner
from core.variable_context import VariableContext
from utils.project_paths import PROJECT_ROOT


class _Runner:
    """为纯 adapter 单测提供最小 ApiRunner 兼容对象。"""

    def __init__(self):
        self.host = "http://127.0.0.1:8000"
        self.context = VariableContext()
        self.runtime_config = {
            "shortlink": {
                "username": "demo-user",
                "password": "demo-password",
                "domain": "nurl.ink:8001",
                "recycle_save_path": "/save",
                "recycle_remove_path": "/remove",
                "create_retry": {"max_attempts": 2, "interval_seconds": 0},
                "storage": {
                    "shard_count": 16,
                    "link_table_prefix": "t_link_",
                    "goto_table_prefix": "t_link_goto_",
                    "redis_login_key_prefix": "short-link:login:",
                    "redis_goto_key_prefix": "short-link:goto:",
                    "redis_uv_key_prefix": "short-link:stats:uv:",
                    "redis_uip_key_prefix": "short-link:stats:uip:",
                },
            }
        }


def test_static_context_comes_from_project_yaml_config_not_framework_constants():
    """username 与登录 Key 前缀都应由项目配置决定。"""
    from testcases.shortlink.support import prepare_shortlink_static_context

    runner = _Runner()
    prepare_shortlink_static_context(runner)

    assert runner.context.get("username", scope="scenario") == "demo-user"
    assert runner.context.get("login_redis_key", scope="scenario") == "short-link:login:demo-user"


def test_storage_context_uses_generic_hash_mod_but_project_owned_prefixes():
    """adapter 可复刻真实分片路由，同时 core/db 不需要知道 t_link/Redis Key。"""
    from testcases.shortlink.support import prepare_shortlink_storage_context

    runner = _Runner()
    prepare_shortlink_storage_context(
        runner,
        gid="0Ly9iC",
        full_short_url="nurl.ink:8001/2rHMXI",
    )

    assert runner.context.get("link_table", scope="scenario") == "t_link_6"
    assert runner.context.get("goto_table", scope="scenario") == "t_link_goto_11"
    assert runner.context.get("goto_redis_key", scope="scenario") == "short-link:goto:nurl.ink:8001/2rHMXI"


def test_capture_created_link_context_normalizes_all_representations():
    """Create 响应被规范化后，YAML 可直接引用 short_uri/full_short_url 等运行时变量。"""
    from testcases.shortlink.support import capture_created_link_context

    runner = _Runner()
    created = capture_created_link_context(
        runner,
        {
            "gid": "0Ly9iC",
            "originUrl": "https://www.doubao.com/",
            "fullShortUrl": "http://nurl.ink:8001/2rHMXI",
        },
    )

    assert created["short_uri"] == "2rHMXI"
    assert created["full_short_url"] == "nurl.ink:8001/2rHMXI"
    assert runner.context.get("link_table", scope="scenario") == "t_link_6"


def test_grouped_yaml_files_are_exactly_four_business_domains_and_hold_18_cases():
    """短链接接入保持 4 个业务域 YAML，并保留 6/6/6 分层覆盖。"""
    from core.case_registry import CaseRegistry

    yaml_dir = PROJECT_ROOT / "testcases" / "shortlink" / "yaml"
    files = sorted(path.name for path in yaml_dir.glob("*.yaml"))
    assert files == ["auth.yaml", "link.yaml", "redirect.yaml", "statistics.yaml"]

    registry = CaseRegistry.from_paths(sorted(yaml_dir.glob("*.yaml")))
    levels = [case.level for case in registry.all_cases()]
    assert len(levels) == 18
    assert levels.count("smoke") == 6
    assert levels.count("core") == 6
    assert levels.count("regression") == 6



def test_create_prerequisite_reuses_v2_case_and_retries_only_b100000(monkeypatch):
    """前置 Create 必须复用稳定 case_id，并且只对已知 Sentinel 限流做有限重试。"""
    from core.case_executor import CaseExecutor
    from core.case_registry import CaseRegistry
    from core.context_provider import ContextProviderRegistry
    from testcases.shortlink.support import create_shortlink_from_case

    runner = _Runner()
    runner.context.set("username", "demo-user", scope="scenario")
    runner.context.set("token", "token-1", scope="scenario")
    runner.context.set("gid", "0Ly9iC", scope="scenario")

    class Response:
        status_code = 200

        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    class Client:
        def __init__(self):
            self.calls = []
            self.responses = [
                Response({"code": "B100000", "message": "limited", "data": None}),
                Response(
                    {
                        "code": "0",
                        "data": {
                            "gid": "0Ly9iC",
                            "originUrl": "https://www.doubao.com/",
                            "fullShortUrl": "http://nurl.ink:8001/2rHMXI",
                        },
                    }
                ),
            ]

        def request(self, method, url, **kwargs):
            self.calls.append((method, url, kwargs))
            return self.responses.pop(0)

    runner.client = Client()
    runner.resolve_dynamic = lambda value: (
        {
            **value,
            "domain": "nurl.ink:8001",
            "gid": "0Ly9iC",
            "describe": "api-autotest-1",
        }
        if isinstance(value, dict) and "originUrl" in value
        else {"Content-Type": "application/json", "username": "demo-user", "token": "token-1"}
    )
    runner._resolve_url = lambda raw: f"{runner.host}{raw}"
    monkeypatch.setattr("testcases.shortlink.support.time.sleep", lambda _: None)

    yaml_dir = PROJECT_ROOT / "testcases" / "shortlink" / "yaml"
    registry = CaseRegistry.from_paths(sorted(yaml_dir.glob("*.yaml")))
    providers = ContextProviderRegistry()
    providers.register("shortlink.group", lambda _executor: None)

    with CaseExecutor(runner=runner, registry=registry, providers=providers) as executor:
        created = create_shortlink_from_case(executor)

    assert created["origin_url"] == "https://www.doubao.com/"
    assert len(runner.client.calls) == 2
    assert runner.client.calls[0][2]["json"]["originUrl"] == "https://www.doubao.com/"



def test_auth_yaml_uses_environment_yaml_credentials_and_never_shortlink_env_variables():
    """真实账号来源统一为 ConfigManager YAML，不再依赖 SHORTLINK_TEST_*。"""
    text = (PROJECT_ROOT / "testcases" / "shortlink" / "yaml" / "auth.yaml").read_text(
        encoding="utf-8"
    )
    assert "${config(shortlink,username)}" in text
    assert "${config(shortlink,password)}" in text
    assert "SHORTLINK_TEST_USERNAME" not in text
    assert "SHORTLINK_TEST_PASSWORD" not in text


def test_generic_framework_modules_do_not_contain_shortlink_business_tokens():
    """真正的可复用边界：框架核心、公共 Pytest glue 和 pytest.ini 都不能知道当前 SUT 业务词。"""
    # 这些 token 代表当前真实项目的表、Key、字段或 suite 名；它们只能出现在项目 adapter/YAML。
    forbidden = ("t_link_", "short-link:", "full_short_url", "short_uri", "gid", "shortlink")
    # core/db/utils 是正式框架代码，根 conftest.py 是所有项目共享的 Pytest collection/fixture glue。
    generic_paths = [PROJECT_ROOT / "conftest.py"]
    for directory in (PROJECT_ROOT / "core", PROJECT_ROOT / "db", PROJECT_ROOT / "utils"):
        generic_paths.extend(sorted(directory.glob("*.py")))
    # pytest.ini 只保留通用 smoke/core/regression；业务 tags 由 YAML 在 collection 前动态注册。
    generic_paths.append(PROJECT_ROOT / "pytest.ini")
    for path in generic_paths:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"business token {token!r} leaked into {path}"


def test_shortlink_v2_cases_have_stable_ids_and_no_top_level_test_wrappers():
    """真实 SUT 普通 Case 应由 Generic Runtime 收集，项目顶层不再维护参数化 wrapper。"""
    from core.case_registry import CaseRegistry

    shortlink_dir = PROJECT_ROOT / "testcases" / "shortlink"
    assert not list(shortlink_dir.glob("test_*.py"))

    registry = CaseRegistry.from_paths(sorted((shortlink_dir / "yaml").glob("*.yaml")))
    cases = registry.all_cases()
    assert len(cases) == 18
    assert len({case.case_id for case in cases}) == 18
    assert sum(case.level == "smoke" for case in cases) == 6
    assert sum(case.level == "core" for case in cases) == 6
    assert sum(case.level == "regression" for case in cases) == 6
    assert sum(case.execution == "workflow" for case in cases) == 2


def test_shortlink_project_registers_v2_context_providers_and_hooks():
    """真实项目只通过公开 Registry 注册前置上下文/Hook，Core 不认识具体业务。"""
    from core.context_provider import CaseHookRegistry, ContextProviderRegistry
    from testcases.shortlink.context import register_extensions

    providers = ContextProviderRegistry()
    hooks = CaseHookRegistry()
    register_extensions(providers, hooks)

    for name in (
        "shortlink.static",
        "shortlink.authenticated",
        "shortlink.group",
        "shortlink.created",
        "shortlink.recycled",
        "shortlink.visited",
    ):
        assert callable(providers.get(name))

    for name in (
        "shortlink.capture_group",
        "shortlink.capture_created",
        "shortlink.cleanup_created",
    ):
        assert name in hooks._hooks


def test_shortlink_complex_lifecycle_isolated_in_workflow_module():
    """只有两条多状态 Regression 保留 Python Workflow，其余业务 Case 都由 Generic Runtime 执行。"""
    from core.case_registry import CaseRegistry
    from testcases.shortlink.workflows.test_storage_lifecycle import WORKFLOW_CASES

    registry = CaseRegistry.from_paths(
        sorted((PROJECT_ROOT / "testcases" / "shortlink" / "yaml").glob("*.yaml"))
    )
    expected = {
        case.case_id
        for case in registry.all_cases()
        if case.execution == "workflow"
    }
    assert expected == {
        "shortlink.link.recycle.db_lifecycle",
        "shortlink.link.recycle.goto_cache_lifecycle",
    }
    assert {param.id for param in WORKFLOW_CASES} == expected
