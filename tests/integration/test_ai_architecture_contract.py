"""Stage 7.1 AI 子系统的架构守门测试。

这些测试不验证模型“聪不聪明”，而是锁定更重要的工程边界：AI production code 不得
写死当前真实 SUT，现有 run.py 主测试链也不得反向依赖 AI 分析模块。
"""
from pathlib import Path

# ROOT 统一定位仓库；测试从任意工作目录启动都能读取 production source。
ROOT = Path(__file__).parents[2]
AI_DIR = ROOT / "ai"

# 这些 token 都属于当前真实 Shortlink SUT；它们允许存在项目适配层，但不能进入通用 ai/。
FORBIDDEN_SUT_TOKENS = (
    "/api/short-link",
    "shortlink-local",
    "nurl.ink",
    "t_link_",
    "short-link:goto:",
)


def test_ai_production_code_has_no_real_sut_hardcoding():
    """AI production package 必须对未来订单/支付等项目保持可复用。"""
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in AI_DIR.glob("*.py")
    ).lower()

    for token in FORBIDDEN_SUT_TOKENS:
        assert token.lower() not in source


def test_run_py_does_not_import_ai_analysis():
    """Stage 7.1 第一版必须保持 run.py 默认测试执行链与 AI 完全解耦。"""
    source = (ROOT / "run.py").read_text(encoding="utf-8")

    assert "from ai." not in source
    assert "import ai." not in source
