"""Standalone Stage 5 CLI tests."""
from __future__ import annotations

from types import SimpleNamespace

import coverage_engine.cli as cli


def test_cli_prints_coverage_summary_without_changing_test_runner(monkeypatch, capsys, tmp_path):
    fake_gap = SimpleNamespace(
        project="demo",
        covered_operations=3,
        total_operations=4,
        coverage_percent=75.0,
        untested_operation_ids=("missing",),
        unknown_bindings=(),
    )
    fake_result = SimpleNamespace(gap=fake_gap, gap_path=tmp_path / "coverage-gap.json")
    captured = {}

    def fake_analyze(env_name, *, env_file=None, output_dir=None):
        captured.update(env=env_name, env_file=env_file, output_dir=output_dir)
        return fake_result

    monkeypatch.setattr(cli, "analyze_environment", fake_analyze)

    exit_code = cli.main(["--env", "demo", "--output", str(tmp_path)])

    assert exit_code == 0
    assert captured == {"env": "demo", "env_file": None, "output_dir": tmp_path}
    output = capsys.readouterr().out
    assert "coverage=3/4 (75.00%)" in output
    assert "untested=1" in output
    assert "unknown_bindings=0" in output
