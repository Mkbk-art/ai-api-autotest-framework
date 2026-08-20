"""Command-line entrypoint for Stage 5 Contract/Coverage analysis."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from coverage_engine.analyzer import analyze_environment


def build_parser() -> argparse.ArgumentParser:
    """Build the standalone analysis CLI without changing ``run.py`` semantics."""
    parser = argparse.ArgumentParser(description="Generate API contract coverage artifacts")
    parser.add_argument("--env", required=True, help="Named environment, for example test or staging")
    parser.add_argument("--env-file", help="Optional external environment YAML override")
    parser.add_argument("--output", help="Output directory; defaults to reports/coverage/<env>")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Generate the three Stage 5 artifacts and print a concise summary."""
    args = build_parser().parse_args(argv)
    result = analyze_environment(
        args.env,
        env_file=args.env_file,
        output_dir=Path(args.output) if args.output else None,
    )
    gap = result.gap
    print(
        f"project={gap.project} coverage={gap.covered_operations}/{gap.total_operations} "
        f"({gap.coverage_percent:.2f}%) untested={len(gap.untested_operation_ids)} "
        f"unknown_bindings={len(gap.unknown_bindings)} output={result.gap_path.parent}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
