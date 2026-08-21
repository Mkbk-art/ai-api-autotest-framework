"""Context Provider dependency metadata used by Stage 6 selection."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.case_executor import CaseExecutor
from core.case_registry import CaseRegistry
from core.context_provider import ContextProviderError, ContextProviderRegistry


class _Runner:
    def __init__(self):
        from core.variable_context import VariableContext

        self.context = VariableContext()
        self.calls = []

    def run(self, base_info, test_case):
        self.calls.append(test_case["case_id"])
        return object()


def _registry(tmp_path: Path) -> CaseRegistry:
    path = tmp_path / "cases.yaml"
    path.write_text(
        """
version: 2
cases:
  - id: demo.case
    name: demo
    level: smoke
    requires: [resource]
    request: {method: GET, path: /demo}
    assertions: []
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return CaseRegistry.from_paths([path])


def test_provider_registry_preserves_explicit_empty_dependency_metadata():
    providers = ContextProviderRegistry()
    providers.register("static", lambda executor: None, requires=(), operations=())

    spec = providers.get_spec("static")

    assert spec.name == "static"
    assert spec.requires == ()
    assert spec.operations == ()
    assert spec.metadata_declared is True


def test_legacy_provider_registration_is_distinguishable_from_explicit_metadata():
    providers = ContextProviderRegistry()
    providers.register("legacy", lambda executor: None)

    assert providers.get_spec("legacy").metadata_declared is False


def test_case_executor_resolves_declared_provider_dependencies_before_provider(tmp_path):
    providers = ContextProviderRegistry()
    events = []
    providers.register(
        "auth",
        lambda executor: events.append("auth"),
        requires=(),
        operations=("login",),
    )
    providers.register(
        "resource",
        lambda executor: events.append("resource"),
        requires=("auth",),
        operations=("createResource",),
    )

    with CaseExecutor(runner=_Runner(), registry=_registry(tmp_path), providers=providers) as executor:
        executor.execute("demo.case")

    assert events == ["auth", "resource"]


def test_provider_metadata_validation_rejects_unknown_provider_and_operation():
    providers = ContextProviderRegistry()
    providers.register(
        "resource",
        lambda executor: None,
        requires=("missing",),
        operations=("createResource",),
    )

    with pytest.raises(ContextProviderError, match="unknown context provider dependency"):
        providers.validate_dependencies({"createResource"})

    providers = ContextProviderRegistry()
    providers.register(
        "resource",
        lambda executor: None,
        requires=(),
        operations=("missingOperation",),
    )
    with pytest.raises(ContextProviderError, match="unknown operation dependency"):
        providers.validate_dependencies({"createResource"})


def test_provider_metadata_validation_rejects_cycle():
    providers = ContextProviderRegistry()
    providers.register("a", lambda executor: None, requires=("b",), operations=())
    providers.register("b", lambda executor: None, requires=("a",), operations=())

    with pytest.raises(ContextProviderError, match=r"a -> b -> a|b -> a -> b"):
        providers.validate_dependencies(set())


def test_project_extension_loader_reuses_same_registry_outside_pytest():
    from core.project_extensions import load_project_extensions

    providers, hooks = load_project_extensions(("shortlink",))

    assert providers.get_spec("shortlink.visited").operations == ("shortlinkRedirect",)
    assert "shortlink.capture_created" in hooks._hooks
