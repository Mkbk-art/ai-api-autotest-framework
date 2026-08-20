"""Configured-project Contract/Coverage analysis orchestration.

This module is intentionally independent from Pytest execution: it reads the same
environment configuration and V2 test assets, then writes deterministic Stage 5
artifacts without changing test PASS/FAIL behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from contracts.model import ApiContract
from contracts.provider import load_contract_from_config
from core.case_registry import CaseRegistry
from core.config_manager import ConfigManager
from coverage_engine.gap import CoverageGap
from coverage_engine.index import CoverageIndex
from utils.project_paths import PROJECT_ROOT


@dataclass(frozen=True)
class CoverageAnalysisResult:
    """In-memory analysis plus the three generated artifact paths."""

    contract: ApiContract
    index: CoverageIndex
    gap: CoverageGap
    contract_path: Path
    index_path: Path
    gap_path: Path


def _selected_case_paths(runtime_config: Mapping[str, Any], project_root: Path) -> list[Path]:
    selection = runtime_config.get("test_selection", {})
    if not isinstance(selection, Mapping):
        raise ValueError("test_selection must be a mapping")
    suites = selection.get("include_suites", [])
    if suites in (None, []):
        roots = [path / "yaml" for path in sorted((project_root / "testcases").iterdir()) if path.is_dir()]
    else:
        if not isinstance(suites, list) or not all(isinstance(item, str) and item.strip() for item in suites):
            raise ValueError("test_selection.include_suites must be a list of non-empty strings")
        roots = [project_root / "testcases" / item.strip() / "yaml" for item in suites]

    paths: list[Path] = []
    for root in roots:
        if root.is_dir():
            paths.extend(sorted(root.glob("*.yaml")))
    return paths


def analyze_environment(
    env_name: str,
    *,
    project_root: str | Path = PROJECT_ROOT,
    env_file: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> CoverageAnalysisResult:
    """Load one configured project and write Contract/Coverage artifacts."""
    root = Path(project_root).resolve()
    runtime_config = ConfigManager(root).load(env_name, env_file=env_file)
    contract = load_contract_from_config(runtime_config, project_root=root)
    registry = CaseRegistry.from_paths(_selected_case_paths(runtime_config, root))
    index = CoverageIndex.build(contract, registry)
    gap = CoverageGap.build(index)

    target_dir = (
        Path(output_dir)
        if output_dir is not None
        else root / "reports" / "coverage" / env_name
    )
    if not target_dir.is_absolute():
        target_dir = root / target_dir
    target_dir = target_dir.resolve()

    contract_path = contract.write_json(target_dir / "contract.json")
    index_path = index.write_json(target_dir / "coverage-index.json")
    gap_path = gap.write_json(target_dir / "coverage-gap.json")
    return CoverageAnalysisResult(
        contract=contract,
        index=index,
        gap=gap,
        contract_path=contract_path,
        index_path=index_path,
        gap_path=gap_path,
    )
