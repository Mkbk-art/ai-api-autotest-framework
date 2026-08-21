"""Safe, explainable regression SelectionPlan construction."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from contracts.model import ApiContract
from core.case_registry import CaseRegistry
from core.case_spec import CaseSpec
from core.context_provider import ContextProviderRegistry
from regression_engine.dependency import DependencyGraphError, DependencyImpact, analyze_dependencies
from regression_engine.diff import ContractDiff, diff_contracts

_LEVELS = {"smoke", "core", "regression", "all"}
_SELECTIONS = {"full", "auto"}


class SelectionInputError(ValueError):
    """Raised for invalid user-controlled selection inputs."""


@dataclass(frozen=True)
class SelectionReason:
    """One stable machine-readable reason attached to a selected Case."""

    code: str
    operation_id: str | None = None
    dependency_path: tuple[str, ...] = ()
    details: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_impact(cls, impact: DependencyImpact) -> "SelectionReason":
        return cls(
            code=impact.reason_code,
            operation_id=impact.operation_id,
            dependency_path=impact.dependency_path,
            details=dict(impact.details),
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"code": self.code}
        if self.operation_id is not None:
            data["operation_id"] = self.operation_id
        if self.dependency_path:
            data["dependency_path"] = list(self.dependency_path)
        if self.details:
            data["details"] = dict(self.details)
        return data


@dataclass(frozen=True)
class SelectedCase:
    """One selected structured test asset plus all accumulated reasons."""

    case_id: str
    level: str
    execution: str
    reasons: tuple[SelectionReason, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "level": self.level,
            "execution": self.execution,
            "reasons": [item.to_dict() for item in self.reasons],
        }


@dataclass(frozen=True)
class SelectionPlan:
    """Complete deterministic plan handed to Pytest collection."""

    project: str
    level: str
    requested_selection: str
    mode: str
    eligible_case_ids: tuple[str, ...]
    selected_cases: tuple[SelectedCase, ...]
    changed_operation_ids: tuple[str, ...] = ()
    uncovered_changed_operation_ids: tuple[str, ...] = ()
    fallback_reason: str | None = None
    contract_diff: ContractDiff | None = None

    @property
    def selected_case_ids(self) -> tuple[str, ...]:
        return tuple(item.case_id for item in self.selected_cases)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "level": self.level,
            "requested_selection": self.requested_selection,
            "mode": self.mode,
            "eligible_count": len(self.eligible_case_ids),
            "selected_count": len(self.selected_cases),
            "eligible_case_ids": list(self.eligible_case_ids),
            "selected_case_ids": list(self.selected_case_ids),
            "changed_operation_ids": list(self.changed_operation_ids),
            "uncovered_changed_operation_ids": list(self.uncovered_changed_operation_ids),
            "fallback_reason": self.fallback_reason,
            "selected_cases": [item.to_dict() for item in self.selected_cases],
        }

    def write_json(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return target


def _eligible_cases(registry: CaseRegistry, level: str) -> tuple[CaseSpec, ...]:
    normalized = level.strip().lower() if isinstance(level, str) else ""
    if normalized not in _LEVELS:
        raise SelectionInputError(f"level must be one of {sorted(_LEVELS)}")
    if normalized == "all":
        return registry.all_cases()
    return tuple(case for case in registry.all_cases() if case.level == normalized)


def _full_plan(
    *,
    current: ApiContract,
    eligible: tuple[CaseSpec, ...],
    level: str,
    requested_selection: str,
    mode: str,
    reason_code: str,
    fallback_reason: str | None = None,
    diff: ContractDiff | None = None,
) -> SelectionPlan:
    selected = tuple(
        SelectedCase(
            case_id=case.case_id,
            level=case.level,
            execution=case.execution,
            reasons=(SelectionReason(code=reason_code),),
        )
        for case in eligible
    )
    return SelectionPlan(
        project=current.project,
        level=level,
        requested_selection=requested_selection,
        mode=mode,
        eligible_case_ids=tuple(case.case_id for case in eligible),
        selected_cases=selected,
        changed_operation_ids=diff.changed_operation_ids if diff is not None else (),
        fallback_reason=fallback_reason,
        contract_diff=diff,
    )


def _validate_user_includes(
    *,
    registry: CaseRegistry,
    eligible: tuple[CaseSpec, ...],
    include_case_ids: Iterable[str],
    include_tags: Iterable[str],
) -> tuple[set[str], dict[str, list[str]]]:
    eligible_ids = {case.case_id for case in eligible}
    requested_ids: set[str] = set()
    source: dict[str, list[str]] = {}

    for case_id in dict.fromkeys(include_case_ids):
        try:
            case = registry.get(case_id)
        except KeyError as exc:
            raise SelectionInputError(f"unknown included case: {case_id}") from exc
        if case.case_id not in eligible_ids:
            raise SelectionInputError(
                f"included case is outside selected level: {case.case_id} "
                f"(case level={case.level})"
            )
        requested_ids.add(case.case_id)
        source.setdefault(case.case_id, []).append(f"case:{case.case_id}")

    for raw_tag in dict.fromkeys(include_tags):
        tag = raw_tag.strip() if isinstance(raw_tag, str) else ""
        if not tag:
            raise SelectionInputError("included tag must be non-empty text")
        matches = [case for case in eligible if tag in case.tags]
        if not matches:
            raise SelectionInputError(f"included tag matched no cases in selected level: {tag}")
        for case in matches:
            requested_ids.add(case.case_id)
            source.setdefault(case.case_id, []).append(f"tag:{tag}")
    return requested_ids, source


def build_selection_plan(
    *,
    baseline: ApiContract | None,
    current: ApiContract,
    registry: CaseRegistry,
    providers: ContextProviderRegistry,
    level: str,
    selection: str = "full",
    include_case_ids: Iterable[str] = (),
    include_tags: Iterable[str] = (),
    baseline_error: str | None = None,
) -> SelectionPlan:
    """Build a safe selection plan without executing tests or mutating assets."""
    normalized_level = level.strip().lower() if isinstance(level, str) else ""
    eligible = _eligible_cases(registry, normalized_level)
    normalized_selection = selection.strip().lower() if isinstance(selection, str) else ""
    if normalized_selection not in _SELECTIONS:
        raise SelectionInputError(f"selection must be one of {sorted(_SELECTIONS)}")

    if normalized_selection == "full":
        return _full_plan(
            current=current,
            eligible=eligible,
            level=normalized_level,
            requested_selection="full",
            mode="full",
            reason_code="FULL_MODE",
        )

    if baseline is None:
        return _full_plan(
            current=current,
            eligible=eligible,
            level=normalized_level,
            requested_selection="auto",
            mode="fallback_full",
            reason_code="AUTO_FALLBACK_FULL",
            fallback_reason=baseline_error or "CONTRACT_BASELINE_MISSING",
        )

    try:
        diff = diff_contracts(baseline, current)
        valid_operation_ids = tuple(
            dict.fromkeys((*baseline.operation_ids, *current.operation_ids))
        )
        dependency = analyze_dependencies(
            contract=current,
            registry=registry,
            providers=providers,
            changed_operation_ids=diff.changed_operation_ids,
            valid_operation_ids=valid_operation_ids,
        )
    except (ValueError, DependencyGraphError) as exc:
        return _full_plan(
            current=current,
            eligible=eligible,
            level=normalized_level,
            requested_selection="auto",
            mode="fallback_full",
            reason_code="AUTO_FALLBACK_FULL",
            fallback_reason=str(exc),
            diff=locals().get("diff"),
        )

    eligible_ids = {case.case_id for case in eligible}
    reasons_by_case: dict[str, list[SelectionReason]] = {case.case_id: [] for case in eligible}

    for impact in dependency.impacts:
        if impact.case_id in eligible_ids:
            reasons_by_case[impact.case_id].append(SelectionReason.from_impact(impact))

    if normalized_level == "all":
        for case in eligible:
            if case.level == "smoke":
                reasons_by_case[case.case_id].append(SelectionReason(code="SMOKE_SAFETY_SET"))

    included_ids, include_sources = _validate_user_includes(
        registry=registry,
        eligible=eligible,
        include_case_ids=include_case_ids,
        include_tags=include_tags,
    )
    for case_id in included_ids:
        for source in include_sources[case_id]:
            reasons_by_case[case_id].append(
                SelectionReason(code="USER_INCLUDE", details={"source": source})
            )

    selected: list[SelectedCase] = []
    for case in eligible:
        reasons = reasons_by_case[case.case_id]
        if not reasons:
            continue
        # Preserve reason generation order while de-duplicating equivalent evidence.
        unique: list[SelectionReason] = []
        seen: set[str] = set()
        for reason in reasons:
            key = json.dumps(reason.to_dict(), ensure_ascii=False, sort_keys=True)
            if key not in seen:
                seen.add(key)
                unique.append(reason)
        selected.append(
            SelectedCase(
                case_id=case.case_id,
                level=case.level,
                execution=case.execution,
                reasons=tuple(unique),
            )
        )

    uncovered: list[str] = []
    for operation_id in diff.changed_operation_ids:
        changes = diff.changes_for_operation(operation_id)
        if any(change.change_type == "OPERATION_ADDED" for change in changes):
            if not registry.cases_for_operation(operation_id):
                uncovered.append(operation_id)

    return SelectionPlan(
        project=current.project,
        level=normalized_level,
        requested_selection="auto",
        mode="auto",
        eligible_case_ids=tuple(case.case_id for case in eligible),
        selected_cases=tuple(selected),
        changed_operation_ids=diff.changed_operation_ids,
        uncovered_changed_operation_ids=tuple(uncovered),
        contract_diff=diff,
    )
