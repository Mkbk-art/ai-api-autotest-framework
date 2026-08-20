"""Configured-project Stage 5 analysis entrypoint tests."""
from __future__ import annotations

import json

from coverage_engine.analyzer import analyze_environment


def test_analyze_environment_writes_contract_index_and_gap_artifacts(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "config.yaml").write_text("{}\n", encoding="utf-8")
    (tmp_path / "config" / "env.demo.yaml").write_text(
        """
test_selection:
  include_suites: [demo]
contract:
  provider: static_manifest
  source: testcases/demo/contract/contract.yaml
""".strip()
        + "\n",
        encoding="utf-8",
    )
    contract_dir = tmp_path / "testcases" / "demo" / "contract"
    contract_dir.mkdir(parents=True)
    (contract_dir / "contract.yaml").write_text(
        """
version: 1
project: demo
operations:
  - id: ping
    method: GET
    path: /ping
    visibility: external
  - id: createItem
    method: POST
    path: /items
    visibility: external
""".strip()
        + "\n",
        encoding="utf-8",
    )
    yaml_dir = tmp_path / "testcases" / "demo" / "yaml"
    yaml_dir.mkdir(parents=True)
    (yaml_dir / "cases.yaml").write_text(
        """
version: 2
cases:
  - id: ping.success
    name: ping
    operation_id: ping
    level: smoke
    request: {method: GET, path: /ping}
    assertions: [{status_code: 200}]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    output = tmp_path / "artifacts"
    result = analyze_environment("demo", project_root=tmp_path, output_dir=output)

    assert result.contract_path == output / "contract.json"
    assert result.index_path == output / "coverage-index.json"
    assert result.gap_path == output / "coverage-gap.json"
    assert json.loads(result.gap_path.read_text(encoding="utf-8"))["untested_operations"] == [
        "createItem"
    ]
    assert result.gap.coverage_percent == 50.0
