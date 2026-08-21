"""Load project-owned Context Providers and Hooks without SUT hardcoding."""
from __future__ import annotations

import importlib
from collections.abc import Iterable

from core.context_provider import CaseHookRegistry, ContextProviderRegistry


def load_project_extensions(
    project_names: Iterable[str],
) -> tuple[ContextProviderRegistry, CaseHookRegistry]:
    """Load ``testcases.<project>.context`` modules into shared registries.

    Missing context modules are valid: a project that needs no special setup can
    remain YAML-only. Import errors raised *inside* an existing module are not
    swallowed.
    """
    providers = ContextProviderRegistry()
    hooks = CaseHookRegistry()
    for project_name in sorted({name.strip() for name in project_names if isinstance(name, str) and name.strip()}):
        module_name = f"testcases.{project_name}.context"
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            # A project may be YAML-only and therefore have no importable package
            # or context module. Missing dependencies imported *inside* an existing
            # module must still surface instead of being swallowed.
            if isinstance(exc.name, str) and (
                exc.name == module_name or module_name.startswith(f"{exc.name}.")
            ):
                continue
            raise
        register = getattr(module, "register_extensions", None)
        if register is not None:
            register(providers, hooks)
    return providers, hooks
