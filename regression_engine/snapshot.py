"""Accepted normalized Contract snapshot lifecycle.

A baseline is an explicit project-owned decision artifact. Normal test runs only
read it; only the dedicated ``init``/``accept`` operations may create or replace
it.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from contracts.model import ApiContract, ContractError

_SNAPSHOT_SCHEMA_VERSION = 1
_BASELINE_MODES = {"init", "accept"}


class BaselineSnapshotError(ValueError):
    """Raised when an accepted baseline cannot be safely used."""


def _portable_contract(contract: ApiContract) -> ApiContract:
    """Remove runtime-only machine paths before a Contract becomes a durable snapshot."""
    data = contract.to_dict()
    metadata = data.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop("source_path", None)
        if not metadata:
            data.pop("metadata", None)
    return ApiContract.from_dict(data)


@dataclass(frozen=True)
class ContractSnapshot:
    """Versioned wrapper around one normalized :class:`ApiContract`."""

    contract: ApiContract
    created_at: str
    source_digest: str
    snapshot_schema_version: int = _SNAPSHOT_SCHEMA_VERSION

    @classmethod
    def create(cls, contract: ApiContract) -> "ContractSnapshot":
        portable = _portable_contract(contract)
        payload = json.dumps(
            portable.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return cls(
            contract=portable,
            created_at=datetime.now(timezone.utc).isoformat(),
            source_digest=hashlib.sha256(payload).hexdigest(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_schema_version": self.snapshot_schema_version,
            "project": self.contract.project,
            "created_at": self.created_at,
            "source_digest": self.source_digest,
            "contract": self.contract.to_dict(),
        }

    def write_json(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return target


def _resolve_project_path(value: str | Path, *, project_root: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path(project_root).resolve() / path
    return path.resolve()


def load_baseline_path(
    runtime_config: Mapping[str, Any], *, project_root: str | Path
) -> Path:
    """Resolve an explicit baseline path or default beside the Contract source."""
    section = runtime_config.get("contract")
    if not isinstance(section, Mapping):
        raise BaselineSnapshotError("contract configuration must be a mapping")
    explicit = section.get("baseline")
    if isinstance(explicit, str) and explicit.strip():
        return _resolve_project_path(explicit.strip(), project_root=project_root)
    source = section.get("source")
    if not isinstance(source, str) or not source.strip():
        raise BaselineSnapshotError("contract.source must be non-empty text")
    source_path = _resolve_project_path(source.strip(), project_root=project_root)
    return source_path.parent / "baseline.json"


def load_contract_snapshot(
    path: str | Path, *, expected_project: str | None = None
) -> ContractSnapshot:
    """Load and validate one accepted normalized baseline snapshot."""
    target = Path(path)
    if not target.is_file():
        raise BaselineSnapshotError(f"baseline snapshot not found: {target}")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BaselineSnapshotError(f"baseline snapshot invalid JSON: {target}") from exc
    if not isinstance(data, Mapping):
        raise BaselineSnapshotError("baseline snapshot root must be a mapping")
    if data.get("snapshot_schema_version") != _SNAPSHOT_SCHEMA_VERSION:
        raise BaselineSnapshotError(
            f"unsupported baseline snapshot schema version: {data.get('snapshot_schema_version')!r}"
        )
    try:
        contract = ApiContract.from_dict(data.get("contract"))
    except (ContractError, TypeError) as exc:
        raise BaselineSnapshotError(f"invalid normalized contract in baseline: {exc}") from exc
    project = data.get("project")
    if project != contract.project:
        raise BaselineSnapshotError("baseline project metadata does not match normalized contract")
    if expected_project is not None and contract.project != expected_project:
        raise BaselineSnapshotError(
            f"baseline project mismatch: expected={expected_project!r}, actual={contract.project!r}"
        )
    created_at = data.get("created_at")
    digest = data.get("source_digest")
    if not isinstance(created_at, str) or not created_at:
        raise BaselineSnapshotError("baseline created_at must be non-empty text")
    if not isinstance(digest, str) or not digest:
        raise BaselineSnapshotError("baseline source_digest must be non-empty text")
    return ContractSnapshot(contract=contract, created_at=created_at, source_digest=digest)


def write_baseline(
    contract: ApiContract,
    path: str | Path,
    *,
    mode: str,
) -> ContractSnapshot:
    """Explicitly initialize or accept a baseline; normal runs never call this."""
    normalized_mode = mode.strip().lower() if isinstance(mode, str) else ""
    if normalized_mode not in _BASELINE_MODES:
        raise BaselineSnapshotError(f"baseline mode must be one of {sorted(_BASELINE_MODES)}")
    target = Path(path)
    if normalized_mode == "init" and target.exists():
        raise BaselineSnapshotError(f"baseline already exists: {target}")
    if normalized_mode == "accept" and not target.exists():
        raise BaselineSnapshotError(f"baseline does not exist; initialize it first: {target}")
    snapshot = ContractSnapshot.create(contract)
    snapshot.write_json(target)
    return snapshot
