"""Project context Provider and Case Hook registries.

Stage 6 extends Provider registration with optional, explicit dependency metadata.
The runtime can resolve declared Provider dependencies while the regression engine
can inspect the same metadata without parsing project Python source.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any


class ContextProviderError(RuntimeError):
    """Raised for invalid Provider registration or dependency metadata."""


ContextProvider = Callable[[Any], Any]
CaseHook = Callable[[Any, Any, Any], None]


def _names(values: Iterable[str] | None, *, field_name: str) -> tuple[str, ...]:
    """Normalize explicit Provider metadata names while preserving declaration order."""
    if values is None:
        return ()
    if isinstance(values, str):
        raise ContextProviderError(f"{field_name} must be an iterable of names, not text")
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip() if isinstance(value, str) else ""
        if not normalized:
            raise ContextProviderError(f"{field_name} values must be non-empty strings")
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return tuple(result)


@dataclass(frozen=True)
class ContextProviderSpec:
    """One Provider implementation plus deterministic dependency metadata."""

    name: str
    provider: ContextProvider
    requires: tuple[str, ...] = ()
    operations: tuple[str, ...] = ()
    metadata_declared: bool = False


class ContextProviderRegistry:
    """Store project-level context Providers and their dependency metadata."""

    def __init__(self) -> None:
        self._providers: dict[str, ContextProviderSpec] = {}

    def register(
        self,
        name: str,
        provider: ContextProvider,
        *,
        requires: Iterable[str] | None = None,
        operations: Iterable[str] | None = None,
    ) -> None:
        """Register one stable Provider name.

        ``requires``/``operations`` omitted means legacy registration. Stage 6 AUTO
        treats such metadata as incomplete, while existing runtime use remains
        backwards compatible. Passing explicit empty tuples marks the Provider as
        reviewed and dependency-free.
        """
        normalized = name.strip() if isinstance(name, str) else ""
        if not normalized:
            raise ContextProviderError("context provider name must be non-empty")
        if normalized in self._providers:
            raise ContextProviderError(f"context provider already registered: {normalized}")
        metadata_declared = requires is not None and operations is not None
        self._providers[normalized] = ContextProviderSpec(
            name=normalized,
            provider=provider,
            requires=_names(requires, field_name=f"{normalized}.requires"),
            operations=_names(operations, field_name=f"{normalized}.operations"),
            metadata_declared=metadata_declared,
        )

    def get(self, name: str) -> ContextProvider:
        """Return the Provider callable; unknown names fail before HTTP."""
        return self.get_spec(name).provider

    def get_spec(self, name: str) -> ContextProviderSpec:
        """Return one full Provider specification."""
        try:
            return self._providers[name]
        except KeyError as exc:
            raise ContextProviderError(f"unknown context provider: {name}") from exc

    def specs(self) -> tuple[ContextProviderSpec, ...]:
        """Return Provider specs in registration order."""
        return tuple(self._providers.values())

    def validate_dependencies(self, operation_ids: set[str] | frozenset[str]) -> None:
        """Validate declared Provider references, Operation IDs and graph cycles."""
        names = set(self._providers)
        for spec in self._providers.values():
            for dependency in spec.requires:
                if dependency not in names:
                    raise ContextProviderError(
                        f"unknown context provider dependency: {spec.name} -> {dependency}"
                    )
            for operation_id in spec.operations:
                if operation_id not in operation_ids:
                    raise ContextProviderError(
                        f"unknown operation dependency: {spec.name} -> {operation_id}"
                    )

        visiting: list[str] = []
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            if name in visiting:
                start = visiting.index(name)
                chain = [*visiting[start:], name]
                raise ContextProviderError(
                    f"context provider dependency cycle detected: {' -> '.join(chain)}"
                )
            visiting.append(name)
            try:
                for dependency in self._providers[name].requires:
                    visit(dependency)
            finally:
                visiting.pop()
            visited.add(name)

        for name in self._providers:
            visit(name)


class CaseHookRegistry:
    """Store before/after/teardown project Hooks."""

    def __init__(self) -> None:
        self._hooks: dict[str, CaseHook] = {}

    def register(self, name: str, hook: CaseHook) -> None:
        """Register one project Hook."""
        normalized = name.strip() if isinstance(name, str) else ""
        if not normalized:
            raise ContextProviderError("case hook name must be non-empty")
        if normalized in self._hooks:
            raise ContextProviderError(f"case hook already registered: {normalized}")
        self._hooks[normalized] = hook

    def run(self, name: str, executor: Any, case: Any, response: Any) -> None:
        """Run a named Hook."""
        try:
            hook = self._hooks[name]
        except KeyError as exc:
            raise ContextProviderError(f"unknown case hook: {name}") from exc
        hook(executor, case, response)
