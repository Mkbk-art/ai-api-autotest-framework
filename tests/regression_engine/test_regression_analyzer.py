"""Local-first regression analysis artifact orchestration tests."""
from __future__ import annotations

import json
from pathlib import Path

from contracts.manifest_provider import StaticManifestProvider
from regression_engine.analyzer import analyze_selection
from regression_engine.snapshot import write_baseline


def _project(tmp_path: Path, *, current_path: str = "/v2/create", baseline_path: str = "/create") -> Path:
    root = tmp_path / "project"
    (root / "config").mkdir(parents=True)
    (root / "testcases/fixture/yaml").mkdir(parents=True)
    (root / "testcases/fixture/contract").mkdir(parents=True)
    (root / "config/config.yaml").write_text(
        "report:\n  root_dir: reports/runs\n", encoding="utf-8"
    )
    (root / "config/env.test.yaml").write_text(
        """
test_selection:
  include_suites: [fixture]
contract:
  provider: static_manifest
  source: testcases/fixture/contract/contract.yaml
  baseline: testcases/fixture/contract/baseline.json
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (root / "testcases/fixture/yaml/cases.yaml").write_text(
        """
version: 2
cases:
  - id: create.success
    name: create
    operation_id: create
    level: regression
    request: {}
    assertions: []
""".strip()
        + "\n",
        encoding="utf-8",
    )

    def manifest(path: str) -> str:
        return f"""
version: 1
project: example
operations:
  - id: create
    method: POST
    path: {path}
    visibility: external
""".strip() + "\n"

    contract_path = root / "testcases/fixture/contract/contract.yaml"
    contract_path.write_text(manifest(current_path), encoding="utf-8")
    baseline_source = root / "testcases/fixture/contract/baseline-source.yaml"
    baseline_source.write_text(manifest(baseline_path), encoding="utf-8")
    baseline_contract = StaticManifestProvider().load(baseline_source)
    write_baseline(
        baseline_contract,
        root / "testcases/fixture/contract/baseline.json",
        mode="init",
    )
    return root


def test_analyzer_writes_contract_diff_selection_json_and_markdown(tmp_path):
    root = _project(tmp_path)
    out = tmp_path / "run"

    result = analyze_selection(
        "test",
        project_root=root,
        output_dir=out,
        level="regression",
        selection="auto",
    )

    assert result.plan.mode == "auto"
    assert result.plan.selected_case_ids == ("create.success",)
    assert result.baseline_artifact.is_file()
    assert result.current_artifact.is_file()
    assert result.diff_artifact.is_file()
    assert result.selection_json.is_file()
    assert result.selection_markdown.is_file()
    selection = json.loads(result.selection_json.read_text(encoding="utf-8"))
    assert selection["selected_case_ids"] == ["create.success"]
    markdown = result.selection_markdown.read_text(encoding="utf-8")
    assert "PATH_CHANGED" in markdown
    assert "CASE_CONTRACT_DRIFT" not in markdown


def test_analyzer_missing_baseline_falls_back_full_without_creating_it(tmp_path):
    root = _project(tmp_path)
    baseline = root / "testcases/fixture/contract/baseline.json"
    baseline.unlink()

    result = analyze_selection(
        "test",
        project_root=root,
        output_dir=tmp_path / "run",
        level="regression",
        selection="auto",
    )

    assert result.plan.mode == "fallback_full"
    assert "not found" in result.plan.fallback_reason
    assert result.plan.selected_case_ids == ("create.success",)
    assert not baseline.exists()
    assert result.baseline_artifact is None
    assert result.diff_artifact is None


def test_analyzer_invalid_baseline_falls_back_and_never_mutates_baseline(tmp_path):
    root = _project(tmp_path)
    baseline = root / "testcases/fixture/contract/baseline.json"
    baseline.write_text("invalid-json", encoding="utf-8")
    before = baseline.read_bytes()

    result = analyze_selection(
        "test",
        project_root=root,
        output_dir=tmp_path / "run",
        level="regression",
        selection="auto",
    )

    assert result.plan.mode == "fallback_full"
    assert "invalid JSON" in result.plan.fallback_reason
    assert baseline.read_bytes() == before


def test_analyzer_full_mode_does_not_require_or_read_baseline(tmp_path):
    root = _project(tmp_path)
    baseline = root / "testcases/fixture/contract/baseline.json"
    baseline.write_text("invalid-json", encoding="utf-8")

    result = analyze_selection(
        "test",
        project_root=root,
        output_dir=tmp_path / "run",
        level="regression",
        selection="full",
    )

    assert result.plan.mode == "full"
    assert result.plan.selected_case_ids == ("create.success",)
