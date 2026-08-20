"""Stage 7.1 V2 AI 失败分析独立命令行入口。

CLI 与 ``run.py`` 主测试入口完全分离：它只读取一次已经结束的 run Artifact，并通过
``AIConfigResolver`` 解析 YAML-first Provider 配置。普通最终用户只需要修改
``config/ai.yaml``；Git 开发者可使用 ignored ``ai.local.yaml``；环境变量只是最后 fallback。

CLI 允许 provider/protocol/base-url/model/timeout 做单次最高优先级覆盖，但故意不提供
``--api-key VALUE``，避免 Secret 进入 shell history/process list。需要临时输入 Key 时使用
``--api-key-prompt``，由 ``getpass`` 隐藏读取。
"""
from __future__ import annotations

# argparse 提供稳定独立 CLI；AI 参数不会被塞进现有 run.py 主测试入口。
import argparse
# getpass 专门处理临时 Secret 输入，终端不回显真实 API Key。
import getpass
# sys 只用于把配置/Artifact 错误写 stderr，正常摘要仍写 stdout。
import sys
# Path 用于显示 ai-analysis 输出目录；不会输出配置文件里的 Secret。
from pathlib import Path
# Sequence 让 main(argv) 可直接单测；可选 resolver 参数允许测试注入临时项目目录。
from typing import Sequence

# ConfigResolver 负责 YAML/ENV/CLI 优先级，CLI 不自己解析 Provider Profile 细节。
from ai.config import AIConfigError, AIConfigResolver
# Factory 只按 protocol 创建 Adapter，CLI 不认识 DeepSeek/Qwen/OpenAI 等厂商名。
from ai.client import AIClientFactory
# Artifact 层异常与分析编排继续复用 Stage 7.1 已验证实现。
from ai.failure_analyzer import (
    FailureArtifactError,
    NoFailureEvidence,
    analyze_run,
)


def _parser() -> argparse.ArgumentParser:
    """构建 Stage 7.1 V2 CLI 参数树，并明确排除明文 ``--api-key``。"""

    parser = argparse.ArgumentParser(description="AI 接口测试失败分析")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser(
        "analyze",
        help="分析一个已经结束的测试 run Artifact",
    )
    # run-dir 只指向 reports/runs/<run_id>，不是整段 Jenkins Console Output。
    analyze.add_argument(
        "--run-dir",
        required=True,
        help="包含 run.json 与 junit.xml 的测试运行目录",
    )
    # --no-ai 完全绕过 Provider 解析，方便离线 Evidence 验证和无模型用户使用。
    analyze.add_argument(
        "--no-ai",
        action="store_true",
        help="只构建确定性证据，不调用模型",
    )

    # 以下非 Secret 参数属于“本次运行临时覆盖”，优先级高于 ai.local.yaml / ai.yaml / ENV。
    analyze.add_argument("--provider", help="临时选择 AI Provider Profile 名")
    analyze.add_argument("--protocol", help="临时覆盖 Provider 协议标识")
    analyze.add_argument("--base-url", dest="base_url", help="临时覆盖 Provider API 根地址")
    analyze.add_argument("--model", help="临时覆盖模型 ID")
    analyze.add_argument("--timeout", type=float, help="临时覆盖模型请求超时秒数")

    # Key 不支持 --api-key VALUE；这里仅设置一个“是否提示输入”的布尔开关。
    analyze.add_argument(
        "--api-key-prompt",
        action="store_true",
        help="运行时隐藏输入 API Key；该值不会出现在命令行参数中",
    )
    return parser


def _cli_overrides(args: argparse.Namespace) -> dict[str, object]:
    """只收集用户实际提供的非 Secret CLI 覆盖，未提供字段不参与 Resolver 优先级。"""

    result: dict[str, object] = {}
    for name in ("provider", "protocol", "base_url", "model", "timeout"):
        value = getattr(args, name, None)
        if value is not None:
            result[name] = value
    return result


def main(
    argv: Sequence[str] | None = None,
    *,
    resolver: AIConfigResolver | None = None,
) -> int:
    """执行一次失败分析，并返回“分析命令”自己的退出码。

    Args:
        argv: 可选参数序列；``None`` 时读取真实命令行。
        resolver: 测试/嵌入场景可注入 Resolver；普通用户不需要传，默认读取当前项目 YAML。

    Returns:
        0: 已生成 ``ai-analysis`` Artifact，包括 AI 未配置/超时等安全降级状态。
        2: AI 配置非法、协议不支持、run Artifact 缺失或没有失败可分析。

    Notes:
        这里的返回码从不覆盖原 Pytest/Jenkins 结论；AI CLI 是测试结束后的独立辅助命令。
    """

    args = _parser().parse_args(argv)
    if args.command != "analyze":
        raise RuntimeError(f"unsupported command: {args.command}")

    if args.no_ai:
        # 离线模式不读取 YAML/ENV/Key，确保没有 Provider 也能复用确定性 Evidence 能力。
        client = None
    else:
        config_resolver = resolver or AIConfigResolver()
        # 只有显式 --api-key-prompt 才读取终端 Secret；默认不打扰 YAML-first 用户。
        api_key_override = (
            getpass.getpass("AI API Key: ") if args.api_key_prompt else None
        )
        try:
            config = config_resolver.resolve(
                cli_overrides=_cli_overrides(args),
                api_key_override=api_key_override,
            )
            # 完全未配置 Provider 是支持状态，传 None 后由 analyze_run 标记 unavailable。
            client = None if config is None else AIClientFactory.create(config)
        except (AIConfigError, ValueError) as exc:
            # Resolver/Factory 的异常约定不包含 Key；这里只输出字段/协议错误，不输出配置对象。
            print(f"AI configuration error: {exc}", file=sys.stderr)
            return 2

    try:
        result = analyze_run(args.run_dir, client=client)
    except (FailureArtifactError, NoFailureEvidence) as exc:
        # Artifact 错误只包含文件路径/结构说明，不包含 Provider 配置或请求凭据。
        print(str(exc), file=sys.stderr)
        return 2

    output_dir = Path(args.run_dir).expanduser().resolve() / "ai-analysis"
    summary = result.get("summary") or {}
    failure_count = int(summary.get("failed", 0)) + int(summary.get("errors", 0))
    # 控制台只输出无敏感值摘要；Provider、Model、Key 都不在这里打印。
    print(
        f"run_id={result.get('run_id', '')} "
        f"failures={failure_count} "
        f"ai_status={result.get('ai_status', '')} "
        f"output={output_dir}"
    )
    return 0


if __name__ == "__main__":
    # 把 AI CLI 自身状态交给 shell，不读取或篡改原测试 exit code。
    raise SystemExit(main())
