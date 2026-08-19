"""Stage 7.1 AI 失败分析独立命令行入口。

该 CLI 与 ``run.py`` 主测试入口完全分离：它只读取一次已经结束的 run Artifact，
生成确定性 Evidence，并按配置可选调用模型。CLI 自己的退出码表示“分析命令是否完成”，
绝不覆盖原 Pytest/Jenkins 的测试结论。
"""
from __future__ import annotations

# argparse 提供稳定独立入口；不把 AI 参数塞进现有 run.py。
import argparse
# sys 只用于把输入 Artifact 错误写到 stderr，避免混入正常结果输出。
import sys
# Path 用于输出 ai-analysis 目录的规范路径。
from pathlib import Path
# Sequence 让 main(argv) 可直接单元测试，不需要启动子进程。
from typing import Sequence

# Provider 未配置时 from_env 返回 None，CLI 会安全降级为离线 Evidence 模式。
from ai.client import OpenAICompatibleClient
# 只捕获用户输入相关异常；内部编程错误不伪装成成功。
from ai.failure_analyzer import (
    FailureArtifactError,
    NoFailureEvidence,
    analyze_run,
)


def _parser() -> argparse.ArgumentParser:
    """构建 Stage 7.1 独立 CLI 参数树。"""

    parser = argparse.ArgumentParser(description="AI 接口测试失败分析")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser(
        "analyze",
        help="分析一个已经结束的测试 run Artifact",
    )
    # run-dir 指向 reports/runs/<run_id>，而不是 Jenkins Console Output 全文。
    analyze.add_argument(
        "--run-dir",
        required=True,
        help="包含 run.json 与 junit.xml 的测试运行目录",
    )
    # --no-ai 用于完全离线地验证 Evidence Builder 与安全输出，不读取任何 Provider 配置。
    analyze.add_argument(
        "--no-ai",
        action="store_true",
        help="只构建确定性证据，不调用模型",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """执行一次失败分析命令并返回分析 CLI 自己的退出码。

    Returns:
        0: 已成功生成 ``ai-analysis`` Artifact；即使 AI 未配置/超时，确定性证据仍成功。
        2: run Artifact 缺失、非法或没有 failure/error 可分析。
    """

    args = _parser().parse_args(argv)
    # 当前只有 analyze 子命令；保留显式分支，未来扩展也不会让未知命令误入分析逻辑。
    if args.command != "analyze":
        raise RuntimeError(f"unsupported command: {args.command}")

    try:
        # --no-ai 明确禁用模型；否则从 OS Secret/环境读取可选 Provider。
        client = None if args.no_ai else OpenAICompatibleClient.from_env()
        result = analyze_run(args.run_dir, client=client)
    except (FailureArtifactError, NoFailureEvidence) as exc:
        # 这里只输出 Artifact 层错误；错误文本不包含 Provider Key 或原始请求凭据。
        print(str(exc), file=sys.stderr)
        return 2

    output_dir = Path(args.run_dir).expanduser().resolve() / "ai-analysis"
    summary = result.get("summary") or {}
    failure_count = int(summary.get("failed", 0)) + int(summary.get("errors", 0))
    # 控制台只输出无敏感值的运行摘要，完整分析留在 Artifact 文件中。
    print(
        f"run_id={result.get('run_id', '')} "
        f"failures={failure_count} "
        f"ai_status={result.get('ai_status', '')} "
        f"output={output_dir}"
    )
    return 0


if __name__ == "__main__":
    # 模块入口把 main() 返回码交给 Shell/Jenkins；不会读取或改写原测试 exit code。
    raise SystemExit(main())
