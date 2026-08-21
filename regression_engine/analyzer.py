"""Local-first regression analysis orchestration and evidence artifacts."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from contracts.model import ApiContract
from contracts.provider import load_contract_from_config
from core.case_registry import CaseRegistry
from core.config_manager import ConfigManager
from core.project_extensions import load_project_extensions
from regression_engine.selection import SelectionPlan, build_selection_plan
from regression_engine.snapshot import (
    BaselineSnapshotError,
    ContractSnapshot,
    load_baseline_path,
    load_contract_snapshot,
)
from utils.project_paths import PROJECT_ROOT


@dataclass(frozen=True)
class RegressionAnalysisResult:
    """In-memory SelectionPlan plus the generated local evidence paths."""

    current_contract: ApiContract
    plan: SelectionPlan
    baseline_path: Path
    baseline_artifact: Path | None
    current_artifact: Path
    diff_artifact: Path | None
    selection_json: Path
    selection_markdown: Path

    def console_summary(self) -> str:
        """Return a concise human-readable pre-execution summary."""
        lines = [
            "Regression Selection",
            f"  Project: {self.plan.project}",
            f"  Level: {self.plan.level}",
            f"  Requested: {self.plan.requested_selection}",
            f"  Mode: {self.plan.mode}",
            f"  Changed operations: {len(self.plan.changed_operation_ids)}",
            f"  Eligible cases: {len(self.plan.eligible_case_ids)}",
            f"  Selected cases: {len(self.plan.selected_cases)}",
        ]
        if self.plan.uncovered_changed_operation_ids:
            lines.append(
                "  Changed operations without cases: "
                + ", ".join(self.plan.uncovered_changed_operation_ids)
            )
        if self.plan.fallback_reason:
            lines.append(f"  Fallback reason: {self.plan.fallback_reason}")
        lines.append(f"  Evidence: {self.selection_markdown}")
        return "\n".join(lines)


def _selected_suite_names(runtime_config: Mapping[str, Any]) -> tuple[str, ...]:
    selection = runtime_config.get("test_selection", {})
    if not isinstance(selection, Mapping):
        raise ValueError("test_selection must be a mapping")
    suites = selection.get("include_suites", [])
    if suites in (None, []):
        return ()
    if not isinstance(suites, list) or not all(
        isinstance(item, str) and item.strip() for item in suites
    ):
        raise ValueError("test_selection.include_suites must be a list of non-empty strings")
    return tuple(item.strip() for item in suites)


def _selected_case_paths(runtime_config: Mapping[str, Any], root: Path) -> list[Path]:
    suites = _selected_suite_names(runtime_config)
    if suites:
        roots = [root / "testcases" / name / "yaml" for name in suites]
    else:
        roots = [path / "yaml" for path in sorted((root / "testcases").iterdir()) if path.is_dir()]
    paths: list[Path] = []
    for yaml_root in roots:
        if yaml_root.is_dir():
            paths.extend(sorted(yaml_root.glob("*.yaml")))
    return paths


def _write_selection_markdown(plan: SelectionPlan, path: Path) -> Path:
    lines = [
        "# Regression Selection Report",
        "",
        "## Summary",
        "",
        f"- Project: `{plan.project}`",
        f"- Level: `{plan.level}`",
        f"- Requested selection: `{plan.requested_selection}`",
        f"- Final mode: `{plan.mode}`",
        f"- Eligible cases: **{len(plan.eligible_case_ids)}**",
        f"- Selected cases: **{len(plan.selected_cases)}**",
        f"- Changed operations: **{len(plan.changed_operation_ids)}**",
    ]
    if plan.fallback_reason:
        lines.extend(["", "## Safety Fallback", "", f"`{plan.fallback_reason}`"])
    if plan.contract_diff is not None:
        lines.extend(["", "## Contract Changes", ""])
        if not plan.contract_diff.changes:
            lines.append("No semantic Contract changes detected.")
        for change in plan.contract_diff.changes:
            line = f"- `{change.operation_id}` — **{change.change_type}** ({change.severity.value})"
            if change.location:
                line += f" — `{change.location}`"
            lines.append(line)
    if plan.uncovered_changed_operation_ids:
        lines.extend(["", "## Changed Operations Without Existing Cases", ""])
        lines.extend(f"- `{item}`" for item in plan.uncovered_changed_operation_ids)

    lines.extend(["", "## Selected Cases", ""])
    if not plan.selected_cases:
        lines.append("No cases selected in the requested level scope.")
    for case in plan.selected_cases:
        lines.extend([f"### `{case.case_id}`", "", f"Level: `{case.level}`  ", f"Execution: `{case.execution}`", "", "Reasons:"])
        for reason in case.reasons:
            detail = f"- **{reason.code}**"
            if reason.operation_id:
                detail += f" — `{reason.operation_id}`"
            lines.append(detail)
            if reason.dependency_path:
                lines.append(f"  - Path: `{' -> '.join(reason.dependency_path)}`")
            for key, value in reason.details.items():
                lines.append(f"  - {key}: `{value}`")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def analyze_selection(
    env_name: str,
    *,
    project_root: str | Path = PROJECT_ROOT,
    env_file: str | Path | None = None,
    output_dir: str | Path,
    level: str,
    selection: str,
    include_case_ids: tuple[str, ...] = (),
    include_tags: tuple[str, ...] = (),
) -> RegressionAnalysisResult:
    """Build a SelectionPlan and write immutable run evidence without running Pytest."""
    root = Path(project_root).resolve()
    runtime_config = ConfigManager(root).load(env_name, env_file=env_file)
    current = load_contract_from_config(runtime_config, project_root=root)
    registry = CaseRegistry.from_paths(_selected_case_paths(runtime_config, root))
    providers, _hooks = load_project_extensions(_selected_suite_names(runtime_config))
    baseline_path = load_baseline_path(runtime_config, project_root=root)

    baseline_snapshot = None
    baseline_error = None
    if selection.strip().lower() == "auto":
        try:
            baseline_snapshot = load_contract_snapshot(
                baseline_path,
                expected_project=current.project,
            )
        except BaselineSnapshotError as exc:
            baseline_error = str(exc)

    plan = build_selection_plan(
        baseline=baseline_snapshot.contract if baseline_snapshot is not None else None,
        current=current,
        registry=registry,
        providers=providers,
        level=level,
        selection=selection,
        include_case_ids=include_case_ids,
        include_tags=include_tags,
        baseline_error=baseline_error,
    )

    out = Path(output_dir)
    if not out.is_absolute():
        out = root / out
    out = out.resolve()
    contract_dir = out / "contract"
    selection_dir = out / "selection"

    current_artifact = ContractSnapshot.create(current).write_json(contract_dir / "current.json")
    baseline_artifact: Path | None = None
    if baseline_snapshot is not None:
        baseline_artifact = baseline_snapshot.write_json(contract_dir / "baseline.json")
    diff_artifact: Path | None = None
    if plan.contract_diff is not None:
        diff_artifact = plan.contract_diff.write_json(contract_dir / "diff.json")

    selection_json = plan.write_json(selection_dir / "selection.json")
    selection_markdown = _write_selection_markdown(plan, selection_dir / "selection.md")
    return RegressionAnalysisResult(
        current_contract=current,
        plan=plan,
        baseline_path=baseline_path,
        baseline_artifact=baseline_artifact,
        current_artifact=current_artifact,
        diff_artifact=diff_artifact,
        selection_json=selection_json,
        selection_markdown=selection_markdown,
    )
