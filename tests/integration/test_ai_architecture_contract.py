"""Stage 7.1 AI 子系统的架构守门测试。

这些测试不验证模型“聪不聪明”，而是锁定更重要的工程边界：AI production code 不得
写死当前真实 SUT，也不得按 DeepSeek/Qwen/OpenAI 等 Provider 厂商名分支；现有
``run.py`` 主测试链继续不反向依赖 AI 分析模块。
"""
from pathlib import Path

# ROOT 统一定位仓库；测试从任意工作目录启动都能读取 production source。
ROOT = Path(__file__).parents[2]
AI_DIR = ROOT / "ai"

# 这些 token 属于当前 Shortlink SUT；允许存在项目适配层，但不能进入通用 AI production code。
FORBIDDEN_SUT_TOKENS = (
    "/api/short-link",
    "shortlink-local",
    "nurl.ink",
    "t_link_",
    "short-link:goto:",
)

# Provider Profile 名应该完全属于 YAML 数据；如果 production Python 出现这种厂商判断，
# 就意味着“换模型服务必须改代码”，违背 V2 的 Provider/Protocol 解耦目标。
FORBIDDEN_PROVIDER_BRANCH_TOKENS = (
    'provider == "deepseek"',
    "provider == 'deepseek'",
    'provider == "qwen"',
    "provider == 'qwen'",
    'provider == "openai"',
    "provider == 'openai'",
)


def _ai_source() -> str:
    """合并 ai/ 下所有 production Python 源码，供架构 token 扫描复用。"""

    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in AI_DIR.glob("*.py")
    ).lower()


def test_ai_production_code_has_no_real_sut_hardcoding():
    """AI production package 必须对未来订单/支付等项目保持可复用。"""

    source = _ai_source()
    for token in FORBIDDEN_SUT_TOKENS:
        assert token.lower() not in source


def test_ai_production_code_does_not_branch_on_provider_vendor_name():
    """Provider 是 YAML Profile；Python 只允许按 protocol 选择 Adapter。"""

    source = _ai_source()
    for token in FORBIDDEN_PROVIDER_BRANCH_TOKENS:
        assert token.lower() not in source


def test_run_py_does_not_import_ai_analysis():
    """Stage 7.1 必须保持 run.py 默认测试执行链与 AI 完全解耦。"""

    source = (ROOT / "run.py").read_text(encoding="utf-8")
    assert "from ai." not in source
    assert "import ai." not in source
