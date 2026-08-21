"""Deterministic semantic diff for normalized API Contracts.

The diff intentionally ignores documentation-only metadata and compares only the
subset already represented by Stage 5's normalized model.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Any, Iterable

from contracts.model import ApiContract, Operation, Parameter, SchemaField


class ChangeSeverity(str, Enum):
    """Compatibility/risk classification for one semantic Contract change."""

    BREAKING = "BREAKING"
    RISKY = "RISKY"
    NON_BREAKING = "NON_BREAKING"


@dataclass(frozen=True)
class ContractChange:
    """One explainable semantic change bound to a stable operation ID."""

    operation_id: str
    change_type: str
    severity: ChangeSeverity
    location: str | None = None
    before: Any = None
    after: Any = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "operation_id": self.operation_id,
            "type": self.change_type,
            "severity": self.severity.value,
        }
        if self.location is not None:
            data["location"] = self.location
        if self.before is not None:
            data["before"] = self.before
        if self.after is not None:
            data["after"] = self.after
        return data


@dataclass(frozen=True)
class ContractDiff:
    """Semantic diff between an accepted baseline and current Contract."""

    project: str
    changes: tuple[ContractChange, ...]

    @property
    def changed_operation_ids(self) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for change in self.changes:
            if change.operation_id not in seen:
                seen.add(change.operation_id)
                result.append(change.operation_id)
        return tuple(result)

    def changes_for_operation(self, operation_id: str) -> tuple[ContractChange, ...]:
        return tuple(item for item in self.changes if item.operation_id == operation_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "changed_operations": list(self.changed_operation_ids),
            "changes": [item.to_dict() for item in self.changes],
        }

    def write_json(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return target


def _add(
    changes: list[ContractChange],
    operation_id: str,
    change_type: str,
    severity: ChangeSeverity,
    *,
    location: str | None = None,
    before: Any = None,
    after: Any = None,
) -> None:
    changes.append(
        ContractChange(
            operation_id=operation_id,
            change_type=change_type,
            severity=severity,
            location=location,
            before=before,
            after=after,
        )
    )


def _compare_scalar(
    changes: list[ContractChange],
    *,
    operation_id: str,
    prefix: str,
    location: str,
    before: Any,
    after: Any,
    severity: ChangeSeverity,
) -> None:
    if before != after:
        _add(
            changes,
            operation_id,
            f"{prefix}_CHANGED",
            severity,
            location=location,
            before=before,
            after=after,
        )


def _compare_parameters(
    changes: list[ContractChange], operation_id: str, before: Operation, after: Operation
) -> None:
    old = {(item.name, item.location): item for item in before.parameters}
    new = {(item.name, item.location): item for item in after.parameters}
    for key in old.keys() - new.keys():
        item = old[key]
        _add(
            changes,
            operation_id,
            "PARAMETER_REMOVED",
            ChangeSeverity.BREAKING,
            location=f"{item.location}:{item.name}",
            before=item.to_dict(),
        )
    for key in new.keys() - old.keys():
        item = new[key]
        severity = ChangeSeverity.BREAKING if item.required else ChangeSeverity.NON_BREAKING
        _add(
            changes,
            operation_id,
            "PARAMETER_ADDED",
            severity,
            location=f"{item.location}:{item.name}",
            after=item.to_dict(),
        )
    for key in old.keys() & new.keys():
        left, right = old[key], new[key]
        location = f"{left.location}:{left.name}"
        if left.required != right.required:
            severity = (
                ChangeSeverity.BREAKING
                if not left.required and right.required
                else ChangeSeverity.NON_BREAKING
            )
            _add(
                changes,
                operation_id,
                "PARAMETER_REQUIRED_CHANGED",
                severity,
                location=location,
                before=left.required,
                after=right.required,
            )
        _compare_scalar(
            changes,
            operation_id=operation_id,
            prefix="PARAMETER_TYPE",
            location=location,
            before=left.schema_type,
            after=right.schema_type,
            severity=ChangeSeverity.BREAKING,
        )
        _compare_scalar(
            changes,
            operation_id=operation_id,
            prefix="PARAMETER_FORMAT",
            location=location,
            before=left.format,
            after=right.format,
            severity=ChangeSeverity.RISKY,
        )


def _flatten_fields(fields: Iterable[SchemaField], prefix: str = "") -> dict[str, SchemaField]:
    result: dict[str, SchemaField] = {}
    for field in fields:
        path = f"{prefix}.{field.name}" if prefix else field.name
        result[path] = field
        result.update(_flatten_fields(field.fields, path))
    return result


def _compare_fields(
    changes: list[ContractChange],
    operation_id: str,
    *,
    prefix: str,
    old_fields: Iterable[SchemaField],
    new_fields: Iterable[SchemaField],
    added_required_breaking: bool,
    removed_breaking: bool = True,
) -> None:
    old = _flatten_fields(old_fields)
    new = _flatten_fields(new_fields)
    for name in old.keys() & new.keys():
        left, right = old[name], new[name]
        if left.required != right.required:
            if prefix == "REQUEST":
                severity = (
                    ChangeSeverity.BREAKING
                    if not left.required and right.required
                    else ChangeSeverity.NON_BREAKING
                )
            else:
                severity = ChangeSeverity.RISKY
            _add(
                changes,
                operation_id,
                f"{prefix}_FIELD_REQUIRED_CHANGED",
                severity,
                location=name,
                before=left.required,
                after=right.required,
            )
        _compare_scalar(
            changes,
            operation_id=operation_id,
            prefix=f"{prefix}_FIELD_TYPE",
            location=name,
            before=left.schema_type,
            after=right.schema_type,
            severity=ChangeSeverity.BREAKING,
        )
        _compare_scalar(
            changes,
            operation_id=operation_id,
            prefix=f"{prefix}_FIELD_FORMAT",
            location=name,
            before=left.format,
            after=right.format,
            severity=ChangeSeverity.RISKY,
        )
        _compare_scalar(
            changes,
            operation_id=operation_id,
            prefix=f"{prefix}_FIELD_NULLABLE",
            location=name,
            before=left.nullable,
            after=right.nullable,
            severity=ChangeSeverity.RISKY,
        )
    for name in old.keys() - new.keys():
        _add(
            changes,
            operation_id,
            f"{prefix}_FIELD_REMOVED",
            ChangeSeverity.BREAKING if removed_breaking else ChangeSeverity.RISKY,
            location=name,
            before=old[name].to_dict(),
        )
    for name in new.keys() - old.keys():
        severity = (
            ChangeSeverity.BREAKING
            if added_required_breaking and new[name].required
            else ChangeSeverity.NON_BREAKING
        )
        _add(
            changes,
            operation_id,
            f"{prefix}_FIELD_ADDED",
            severity,
            location=name,
            after=new[name].to_dict(),
        )


def _response_fields(operation: Operation) -> tuple[SchemaField, ...]:
    # V1 treats normalized response fields as an operation-level shape. Status-code
    # differences are compared separately; duplicate field names across statuses are de-duped.
    seen: set[str] = set()
    result: list[SchemaField] = []
    for response in operation.responses:
        for name, field in _flatten_fields(response.fields).items():
            if name not in seen:
                seen.add(name)
                result.append(field)
    return tuple(result)


def _compare_operation(changes: list[ContractChange], left: Operation, right: Operation) -> None:
    operation_id = left.operation_id
    if left.method != right.method:
        _add(
            changes,
            operation_id,
            "METHOD_CHANGED",
            ChangeSeverity.BREAKING,
            before=left.method,
            after=right.method,
        )
    if left.path != right.path:
        _add(
            changes,
            operation_id,
            "PATH_CHANGED",
            ChangeSeverity.BREAKING,
            before=left.path,
            after=right.path,
        )
    _compare_parameters(changes, operation_id, left, right)

    old_body, new_body = left.request_body, right.request_body
    if old_body is None and new_body is not None:
        _add(
            changes,
            operation_id,
            "REQUEST_BODY_ADDED",
            ChangeSeverity.BREAKING if new_body.required else ChangeSeverity.NON_BREAKING,
            after=new_body.to_dict(),
        )
    elif old_body is not None and new_body is None:
        _add(
            changes,
            operation_id,
            "REQUEST_BODY_REMOVED",
            ChangeSeverity.BREAKING,
            before=old_body.to_dict(),
        )
    elif old_body is not None and new_body is not None:
        if old_body.required != new_body.required:
            _add(
                changes,
                operation_id,
                "REQUEST_BODY_REQUIRED_CHANGED",
                ChangeSeverity.BREAKING
                if not old_body.required and new_body.required
                else ChangeSeverity.NON_BREAKING,
                before=old_body.required,
                after=new_body.required,
            )
        if old_body.content_type != new_body.content_type:
            _add(
                changes,
                operation_id,
                "REQUEST_CONTENT_TYPE_CHANGED",
                ChangeSeverity.BREAKING,
                before=old_body.content_type,
                after=new_body.content_type,
            )
        _compare_fields(
            changes,
            operation_id,
            prefix="REQUEST",
            old_fields=old_body.fields,
            new_fields=new_body.fields,
            added_required_breaking=True,
        )

    old_status = {item.status_code for item in left.responses}
    new_status = {item.status_code for item in right.responses}
    for status in sorted(old_status - new_status):
        severity = ChangeSeverity.BREAKING if status.startswith("2") else ChangeSeverity.RISKY
        _add(
            changes,
            operation_id,
            "RESPONSE_STATUS_REMOVED",
            severity,
            location=status,
            before=status,
        )
    for status in sorted(new_status - old_status):
        _add(
            changes,
            operation_id,
            "RESPONSE_STATUS_ADDED",
            ChangeSeverity.NON_BREAKING,
            location=status,
            after=status,
        )
    _compare_fields(
        changes,
        operation_id,
        prefix="RESPONSE",
        old_fields=_response_fields(left),
        new_fields=_response_fields(right),
        added_required_breaking=False,
    )


def diff_contracts(baseline: ApiContract, current: ApiContract) -> ContractDiff:
    """Compare normalized Contract semantics under stable operation IDs."""
    if baseline.project != current.project:
        raise ValueError(
            f"contract project mismatch: baseline={baseline.project!r}, current={current.project!r}"
        )
    old = {item.operation_id: item for item in baseline.operations}
    new = {item.operation_id: item for item in current.operations}
    changes: list[ContractChange] = []

    # Keep deterministic baseline order for removals/changes, then current order for additions.
    for operation in baseline.operations:
        operation_id = operation.operation_id
        if operation_id not in new:
            _add(
                changes,
                operation_id,
                "OPERATION_REMOVED",
                ChangeSeverity.BREAKING,
                before=operation.to_dict(),
            )
            continue
        _compare_operation(changes, operation, new[operation_id])
    for operation in current.operations:
        if operation.operation_id not in old:
            _add(
                changes,
                operation.operation_id,
                "OPERATION_ADDED",
                ChangeSeverity.NON_BREAKING,
                after=operation.to_dict(),
            )

    return ContractDiff(project=current.project, changes=tuple(changes))
