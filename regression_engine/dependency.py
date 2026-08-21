"""Deterministic test dependency expansion for change-aware regression.

Only explicit structured assets are traversed: Case/Workflow operation bindings and
Context Provider metadata. The module deliberately does not infer dependencies from
tags, risks, database tables, Redis keys, or project source code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from contracts.model import ApiContract
from core.case_registry import CaseRegistry
from core.case_spec import CaseSpec
from core.context_provider import ContextProviderError, ContextProviderRegistry


class DependencyGraphError(ValueError):
    """Raised when dependency metadata is incomplete or unsafe for AUTO selection."""


@dataclass(frozen=True)
class DependencyImpact:
    """One evidence-backed reason why a Case is affected."""

    case_id: str
    reason_code: str
    operation_id: str | None = None
    dependency_path: tuple[str, ...] = ()
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "case_id": self.case_id,
            "reason": self.reason_code,
        }
        if self.operation_id is not None:
            data["operation_id"] = self.operation_id
        if self.dependency_path:
            data["dependency_path"] = list(self.dependency_path)
        if self.details:
            data["details"] = dict(self.details)
        return data


@dataclass(frozen=True)
class DependencyAnalysis:
    """All deterministic dependency/drift impacts for one selection attempt."""

    impacts: tuple[DependencyImpact, ...]

    def impacts_for_case(self, case_id: str) -> tuple[DependencyImpact, ...]:
        return tuple(item for item in self.impacts if item.case_id == case_id)


def _used_provider_names(registry: CaseRegistry, providers: ContextProviderRegistry) -> set[str]:
    """Return all Providers reachable from Case ``requires`` declarations."""
    used: set[str] = set()
    visiting: set[str] = set()

    def visit(name: str) -> None:
        if name in used:
            return
        if name in visiting:
            # Registry validation emits the more precise cycle chain later.
            return
        visiting.add(name)
        try:
            spec = providers.get_spec(name)
        except ContextProviderError as exc:
            raise DependencyGraphError(str(exc)) from exc
        for dependency in spec.requires:
            visit(dependency)
        visiting.remove(name)
        used.add(name)

    for case in registry.all_cases():
        for name in case.requires:
            visit(name)
    return used


def _validate(
    contract: ApiContract,
    registry: CaseRegistry,
    providers: ContextProviderRegistry,
    *,
    valid_operation_ids: Iterable[str] | None = None,
) -> set[str]:
    valid_operations = set(valid_operation_ids or contract.operation_ids)
    for case in registry.all_cases():
        for operation_id in case.operation_ids:
            if operation_id not in valid_operations:
                raise DependencyGraphError(
                    f"unknown case operation dependency: {case.case_id} -> {operation_id}"
                )

    try:
        providers.validate_dependencies(valid_operations)
    except ContextProviderError as exc:
        raise DependencyGraphError(str(exc)) from exc

    used = _used_provider_names(registry, providers)
    for name in used:
        spec = providers.get_spec(name)
        if not spec.metadata_declared:
            raise DependencyGraphError(f"context provider dependency metadata not declared: {name}")
    return valid_operations


def _provider_operation_path(
    providers: ContextProviderRegistry,
    provider_name: str,
    operation_id: str,
    *,
    visited: frozenset[str] = frozenset(),
) -> tuple[str, ...] | None:
    """Find one deterministic Provider chain to an Operation dependency."""
    if provider_name in visited:
        return None
    spec = providers.get_spec(provider_name)
    prefix = (f"provider:{provider_name}",)
    if operation_id in spec.operations:
        return (*prefix, f"operation:{operation_id}")
    next_visited = visited | {provider_name}
    for dependency in spec.requires:
        child = _provider_operation_path(
            providers,
            dependency,
            operation_id,
            visited=next_visited,
        )
        if child is not None:
            return (*prefix, *child)
    return None



def analyze_dependencies(
    *,
    contract: ApiContract,
    registry: CaseRegistry,
    providers: ContextProviderRegistry,
    changed_operation_ids: Iterable[str],
    valid_operation_ids: Iterable[str] | None = None,
) -> DependencyAnalysis:
    """Expand changed Operations through explicit test dependency metadata.

    ``valid_operation_ids`` may include operations removed from the current
    Contract so old bindings remain analyzable during a removal diff.
    """
    valid_operations = _validate(
        contract,
        registry,
        providers,
        valid_operation_ids=valid_operation_ids,
    )
    changed = tuple(dict.fromkeys(changed_operation_ids))
    unknown_changed = [item for item in changed if item not in valid_operations]
    if unknown_changed:
        raise DependencyGraphError(
            f"changed operation is not present in dependency contract: {unknown_changed[0]}"
        )

    impacts: list[DependencyImpact] = []
    seen: set[tuple[Any, ...]] = set()

    def add(impact: DependencyImpact) -> None:
        key = (
            impact.case_id,
            impact.reason_code,
            impact.operation_id,
            impact.dependency_path,
            tuple(sorted(impact.details.items())),
        )
        if key not in seen:
            seen.add(key)
            impacts.append(impact)

    for case in registry.all_cases():
        for operation_id in changed:
            if operation_id in case.operation_ids:
                add(
                    DependencyImpact(
                        case_id=case.case_id,
                        reason_code=(
                            "WORKFLOW_OPERATION_CHANGE"
                            if case.execution == "workflow"
                            else "DIRECT_OPERATION_CHANGE"
                        ),
                        operation_id=operation_id,
                    )
                )
            for provider_name in case.requires:
                path = _provider_operation_path(providers, provider_name, operation_id)
                if path is not None:
                    add(
                        DependencyImpact(
                            case_id=case.case_id,
                            reason_code="CONTEXT_OPERATION_DEPENDENCY",
                            operation_id=operation_id,
                            dependency_path=(f"case:{case.case_id}", *path),
                        )
                    )

    return DependencyAnalysis(impacts=tuple(impacts))
