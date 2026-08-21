"""Standalone Stage 6 baseline lifecycle CLI.

Normal ``run.py`` execution never writes accepted baselines. This module provides
the explicit user actions that initialize or accept a normalized Contract snapshot.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from contracts.provider import load_contract_from_config
from core.config_manager import ConfigManager
from regression_engine.snapshot import BaselineSnapshotError, load_baseline_path, write_baseline
from utils.project_paths import PROJECT_ROOT


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Change-aware regression baseline management")
    subparsers = parser.add_subparsers(dest="command", required=True)
    baseline = subparsers.add_parser("baseline", help="manage accepted normalized Contract baseline")
    baseline_sub = baseline.add_subparsers(dest="baseline_command", required=True)
    for action in ("init", "accept"):
        command = baseline_sub.add_parser(action)
        command.add_argument("--env", default="test", help="named framework environment")
        command.add_argument("--env-file", help="optional external environment override YAML")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    project_root: str | Path = PROJECT_ROOT,
) -> int:
    """Execute one explicit baseline lifecycle command."""
    args = _parser().parse_args(argv)
    root = Path(project_root).resolve()
    try:
        runtime = ConfigManager(root).load(args.env, env_file=args.env_file)
        contract = load_contract_from_config(runtime, project_root=root)
        baseline_path = load_baseline_path(runtime, project_root=root)
        snapshot = write_baseline(contract, baseline_path, mode=args.baseline_command)
    except (BaselineSnapshotError, FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    verb = "initialized" if args.baseline_command == "init" else "accepted"
    print(
        f"baseline {verb}: project={snapshot.contract.project} "
        f"operations={len(snapshot.contract.operations)} path={baseline_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
