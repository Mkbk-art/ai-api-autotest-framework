"""Stage 6 baseline CLI tests."""
from __future__ import annotations

import json
from pathlib import Path

from regression_engine.cli import main
from regression_engine.snapshot import load_contract_snapshot


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "config").mkdir(parents=True)
    (root / "testcases/fixture/contract").mkdir(parents=True)
    (root / "config/config.yaml").write_text("{}\n", encoding="utf-8")
    (root / "config/env.test.yaml").write_text(
        """
contract:
  provider: static_manifest
  source: testcases/fixture/contract/contract.yaml
  baseline: testcases/fixture/contract/baseline.json
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (root / "testcases/fixture/contract/contract.yaml").write_text(
        """
version: 1
project: example
operations:
  - id: query
    method: GET
    path: /query
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return root


def test_baseline_cli_init_then_accept_requires_explicit_commands(tmp_path, capsys):
    root = _project(tmp_path)
    baseline = root / "testcases/fixture/contract/baseline.json"

    assert main(["baseline", "init", "--env", "test"], project_root=root) == 0
    assert baseline.is_file()
    first = load_contract_snapshot(baseline)
    assert first.contract.get_operation("query").path == "/query"

    contract = root / "testcases/fixture/contract/contract.yaml"
    contract.write_text(
        """
version: 1
project: example
operations:
  - id: query
    method: GET
    path: /v2/query
""".strip()
        + "\n",
        encoding="utf-8",
    )

    assert main(["baseline", "accept", "--env", "test"], project_root=root) == 0
    assert load_contract_snapshot(baseline).contract.get_operation("query").path == "/v2/query"
    assert "accepted" in capsys.readouterr().out.lower()


def test_baseline_cli_init_refuses_existing_and_accept_refuses_missing(tmp_path, capsys):
    root = _project(tmp_path)

    assert main(["baseline", "accept", "--env", "test"], project_root=root) == 2
    assert "initialize" in capsys.readouterr().err.lower()

    assert main(["baseline", "init", "--env", "test"], project_root=root) == 0
    assert main(["baseline", "init", "--env", "test"], project_root=root) == 2
    assert "already exists" in capsys.readouterr().err.lower()
