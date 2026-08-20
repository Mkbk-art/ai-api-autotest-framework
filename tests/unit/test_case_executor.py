"""Context Provider、Hook 与 CaseExecutor 的通用执行边界测试。"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import pytest

from core.case_executor import CaseExecutor
from core.case_registry import CaseRegistry
from core.context_provider import CaseHookRegistry, ContextProviderError, ContextProviderRegistry


class _Response:
    status_code = 200


class _Runner:
    def __init__(self):
        from core.variable_context import VariableContext

        self.context = VariableContext()
        self.calls = []

    def run(self, base_info, test_case):
        self.calls.append((base_info, test_case))
        self.context.set("response_seen", True, scope="scenario")
        return _Response()

    def run_polling(self, base_info, test_case):
        self.calls.append((base_info, {**test_case, "_polling": True}))
        return _Response()


def _registry(tmp_path: Path, *, extra: str = "") -> CaseRegistry:
    path = tmp_path / "cases.yaml"
    path.write_text(
        f"""
version: 2
cases:
  - id: demo.case
    name: demo
    level: smoke
    requires: [authenticated]
    request:
      method: GET
      path: /demo
    assertions:
      - status_code: 200
{extra}
""",
        encoding="utf-8",
    )
    return CaseRegistry.from_paths([path])


def test_case_executor_enters_context_provider_before_running_case(tmp_path):
    runner = _Runner()
    providers = ContextProviderRegistry()

    @contextmanager
    def authenticated(executor):
        executor.runner.context.set("token", "safe-token", scope="scenario")
        yield

    providers.register("authenticated", authenticated)
    executor = CaseExecutor(runner=runner, registry=_registry(tmp_path), providers=providers)

    with executor:
        response = executor.execute("demo.case")

    assert response.status_code == 200
    assert runner.context.get("token", scope="scenario") == "safe-token"
    assert len(runner.calls) == 1


def test_context_provider_cycle_fails_before_http_request(tmp_path):
    runner = _Runner()
    providers = ContextProviderRegistry()

    def first(executor):
        executor.ensure_context("second")

    def second(executor):
        executor.ensure_context("first")

    providers.register("first", first)
    providers.register("second", second)
    registry = _registry(tmp_path)
    case = registry.get("demo.case")
    object.__setattr__(case, "requires", ("first",))
    executor = CaseExecutor(runner=runner, registry=registry, providers=providers)

    with executor, pytest.raises(ContextProviderError, match="cycle"):
        executor.execute(case)

    assert runner.calls == []


def test_case_executor_runs_after_response_and_teardown_hooks(tmp_path):
    runner = _Runner()
    providers = ContextProviderRegistry()
    providers.register("authenticated", lambda executor: None)
    hooks = CaseHookRegistry()
    events = []

    hooks.register("capture", lambda executor, case, response: events.append(("capture", response.status_code)))
    hooks.register("cleanup", lambda executor, case, response: events.append(("cleanup", response.status_code)))
    registry = _registry(
        tmp_path,
        extra="""
    hooks:
      after_response: [capture]
      teardown: [cleanup]
""",
    )
    executor = CaseExecutor(runner=runner, registry=registry, providers=providers, hooks=hooks)

    with executor:
        executor.execute("demo.case")

    assert events == [("capture", 200), ("cleanup", 200)]


def test_case_executor_can_defer_teardown_for_python_workflow(tmp_path):
    runner = _Runner()
    providers = ContextProviderRegistry()
    providers.register("authenticated", lambda executor: None)
    hooks = CaseHookRegistry()
    events = []
    hooks.register("cleanup", lambda executor, case, response: events.append("cleanup"))
    registry = _registry(
        tmp_path,
        extra="""
    hooks:
      teardown: [cleanup]
""",
    )

    with CaseExecutor(runner=runner, registry=registry, providers=providers, hooks=hooks) as executor:
        executor.execute("demo.case", defer_teardown=True)
        assert events == []

    assert events == ["cleanup"]


def test_case_executor_uses_polling_when_case_declares_poll(tmp_path):
    runner = _Runner()
    providers = ContextProviderRegistry()
    providers.register("authenticated", lambda executor: None)
    registry = _registry(
        tmp_path,
        extra="""
    poll:
      timeout_seconds: 3
      interval_seconds: 1
""",
    )

    with CaseExecutor(runner=runner, registry=registry, providers=providers) as executor:
        executor.execute("demo.case")

    assert runner.calls[0][1]["_polling"] is True


def test_case_executor_runs_teardown_even_when_runner_assertion_fails(tmp_path):
    class FailingRunner(_Runner):
        def run(self, base_info, test_case):
            self.context.set("created_id", "resource-1", scope="scenario")
            raise AssertionError("business assertion failed")

    runner = FailingRunner()
    providers = ContextProviderRegistry()
    providers.register("authenticated", lambda executor: None)
    hooks = CaseHookRegistry()
    events = []
    hooks.register(
        "cleanup",
        lambda executor, case, response: events.append(
            (executor.runner.context.get("created_id", scope="scenario"), response)
        ),
    )
    registry = _registry(
        tmp_path,
        extra="""
    hooks:
      teardown: [cleanup]
""",
    )

    with CaseExecutor(runner=runner, registry=registry, providers=providers, hooks=hooks) as executor:
        with pytest.raises(AssertionError, match="business assertion failed"):
            executor.execute("demo.case")

    assert events == [("resource-1", None)]
