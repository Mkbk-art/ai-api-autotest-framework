"""Compute deterministic API coverage gaps from ``CoverageIndex``."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from coverage_engine.index import CoverageIndex, UnknownOperationBinding

_DEFAULT_SCOPE = ("external", "external_gateway", "external_direct")


@dataclass(frozen=True)
class CoverageGap:
    """Stage 5 gaps that can be proven without AI or a risk policy."""

    project: str
    scope_visibilities: tuple[str, ...]
    total_operations: int
    covered_operations: int
    coverage_percent: float
    untested_operation_ids: tuple[str, ...]
    unknown_bindings: tuple[UnknownOperationBinding, ...]
    unbound_case_ids: tuple[str, ...]

    @classmethod
    def build(
        cls,
        index: CoverageIndex,
        *,
        visibilities: tuple[str, ...] | None = None,
    ) -> "CoverageGap":
        """Build a coverage gap for the requested operation visibility scope."""
        scope = _DEFAULT_SCOPE if visibilities is None else tuple(visibilities)
        scoped = [item for item in index.operations if item.visibility in scope]
        covered = sum(1 for item in scoped if item.covered)
        total = len(scoped)
        percent = round((covered / total * 100.0), 2) if total else 0.0
        return cls(
            project=index.project,
            scope_visibilities=scope,
            total_operations=total,
            covered_operations=covered,
            coverage_percent=percent,
            untested_operation_ids=tuple(item.operation_id for item in scoped if not item.covered),
            unknown_bindings=index.unknown_bindings,
            unbound_case_ids=index.unbound_case_ids,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "scope_visibilities": list(self.scope_visibilities),
            "summary": {
                "total_operations": self.total_operations,
                "covered_operations": self.covered_operations,
                "coverage_percent": self.coverage_percent,
            },
            "untested_operations": list(self.untested_operation_ids),
            "unknown_operation_bindings": [item.to_dict() for item in self.unknown_bindings],
            "unbound_cases": list(self.unbound_case_ids),
        }

    def write_json(self, path: str | Path) -> Path:
        """Persist the deterministic gap report as UTF-8 JSON."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return target
