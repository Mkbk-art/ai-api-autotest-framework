"""Build deterministic Operation-to-test coverage relationships."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from contracts.model import ApiContract
from core.case_registry import CaseRegistry


def _append_unique(target: list[str], values) -> None:
    for value in values:
        if value not in target:
            target.append(value)


@dataclass(frozen=True)
class UnknownOperationBinding:
    """One Case/Workflow reference to an operation absent from the contract."""

    case_id: str
    operation_id: str
    execution: str

    def to_dict(self) -> dict[str, str]:
        return {
            "case_id": self.case_id,
            "operation_id": self.operation_id,
            "execution": self.execution,
        }


@dataclass(frozen=True)
class OperationCoverage:
    """Observed test coverage metadata for one contract operation."""

    operation_id: str
    method: str
    path: str
    service: str | None
    visibility: str
    case_ids: tuple[str, ...]
    workflow_case_ids: tuple[str, ...]
    risks: tuple[str, ...]
    levels: tuple[str, ...]

    @property
    def covered(self) -> bool:
        """Whether at least one test asset is bound to this operation."""
        return bool(self.case_ids)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "operation_id": self.operation_id,
            "method": self.method,
            "path": self.path,
            "visibility": self.visibility,
            "covered": self.covered,
            "cases": list(self.case_ids),
            "workflow_cases": list(self.workflow_case_ids),
            "risks": list(self.risks),
            "levels": list(self.levels),
        }
        if self.service is not None:
            data["service"] = self.service
        return data


@dataclass(frozen=True)
class CoverageIndex:
    """Complete observed relation between one ApiContract and CaseRegistry."""

    project: str
    operations: tuple[OperationCoverage, ...]
    unknown_bindings: tuple[UnknownOperationBinding, ...]
    unbound_case_ids: tuple[str, ...]

    @classmethod
    def build(cls, contract: ApiContract, registry: CaseRegistry) -> "CoverageIndex":
        """Build coverage without guessing expected tests or risks."""
        known_ids = set(contract.operation_ids)
        case_ids: dict[str, list[str]] = {operation_id: [] for operation_id in contract.operation_ids}
        workflow_ids: dict[str, list[str]] = {operation_id: [] for operation_id in contract.operation_ids}
        risks: dict[str, list[str]] = {operation_id: [] for operation_id in contract.operation_ids}
        levels: dict[str, list[str]] = {operation_id: [] for operation_id in contract.operation_ids}
        unknown: list[UnknownOperationBinding] = []
        unbound: list[str] = []

        for case in registry.all_cases():
            operation_ids = case.operation_ids
            if not operation_ids:
                unbound.append(case.case_id)
                continue
            for operation_id in operation_ids:
                if operation_id not in known_ids:
                    unknown.append(
                        UnknownOperationBinding(
                            case_id=case.case_id,
                            operation_id=operation_id,
                            execution=case.execution,
                        )
                    )
                    continue
                _append_unique(case_ids[operation_id], (case.case_id,))
                if case.execution == "workflow":
                    _append_unique(workflow_ids[operation_id], (case.case_id,))
                _append_unique(risks[operation_id], case.risks)
                _append_unique(levels[operation_id], (case.level,))

        operation_rows = tuple(
            OperationCoverage(
                operation_id=operation.operation_id,
                method=operation.method,
                path=operation.path,
                service=operation.service,
                visibility=operation.visibility,
                case_ids=tuple(case_ids[operation.operation_id]),
                workflow_case_ids=tuple(workflow_ids[operation.operation_id]),
                risks=tuple(risks[operation.operation_id]),
                levels=tuple(levels[operation.operation_id]),
            )
            for operation in contract.operations
        )
        return cls(
            project=contract.project,
            operations=operation_rows,
            unknown_bindings=tuple(unknown),
            unbound_case_ids=tuple(unbound),
        )

    def get_operation(self, operation_id: str) -> OperationCoverage:
        """Return one operation coverage row by stable ID."""
        for operation in self.operations:
            if operation.operation_id == operation_id:
                return operation
        raise KeyError(f"unknown coverage operation id: {operation_id}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "operations": [item.to_dict() for item in self.operations],
            "unknown_operation_bindings": [item.to_dict() for item in self.unknown_bindings],
            "unbound_cases": list(self.unbound_case_ids),
        }

    def write_json(self, path: str | Path) -> Path:
        """Persist the coverage index as deterministic UTF-8 JSON."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return target
