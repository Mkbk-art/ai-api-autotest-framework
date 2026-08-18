"""Stage 6 CI/CD 配置契约测试。

本模块不尝试在本地“模拟 GitHub/Jenkins 平台”，而是守住可离线验证的工程契约：
公共 GitHub Actions 必须只验证框架/Mock 能力，Jenkins 必须通过统一 run.py 参数化执行，
二者都要在失败时保留报告，而且不能把当前短链接 SUT 的业务细节写进公共 CI。
"""
from __future__ import annotations

# Path 统一从仓库根目录读取 CI 配置，避免测试依赖启动命令的当前工作目录。
from pathlib import Path

# BaseLoader 按字符串读取 GitHub workflow；这样 YAML 1.1 不会把键名 ``on`` 误解析为布尔值。
import yaml

# PROJECT_ROOT 是框架公共路径入口，测试不自行拼接绝对目录。
from utils.project_paths import PROJECT_ROOT


WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "api-test.yml"
JENKINSFILE_PATH = PROJECT_ROOT / "Jenkinsfile"

# 这些词属于当前短链接 SUT，公共 CI 出现它们就说明框架调度层被业务实现污染。
_FORBIDDEN_SUT_TOKENS = (
    "shortlink-local",
    "nurl.ink",
    "t_link_",
    "short-link:goto",
    "short-link:login",
)


def _workflow() -> dict:
    """读取 GitHub Actions YAML，并保留所有键和值的字符串形态。"""
    # 先断言文件存在，RED 阶段会明确告诉实现者缺少哪一个 Stage 6 交付物。
    assert WORKFLOW_PATH.is_file(), f"missing workflow: {WORKFLOW_PATH}"
    # BaseLoader 适合契约检查：我们只关心 workflow 结构和文本，不执行 YAML 类型转换。
    data = yaml.load(WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert isinstance(data, dict)
    return data


def test_github_actions_runs_framework_and_mock_via_supported_entrypoints():
    """GitHub Actions 应验证公共框架与 Mock 主链，而不是尝试访问本机真实 SUT。"""
    workflow = _workflow()
    # 三种触发方式分别覆盖代码提交、PR 合并前校验和人工演示/排障。
    triggers = workflow.get("on", {})
    assert {"push", "pull_request", "workflow_dispatch"}.issubset(triggers)

    # 当前官方 Action 主版本在设计阶段已核查；使用明确主版本避免隐式漂移。
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "actions/checkout@v6" in text
    assert "actions/setup-python@v6" in text
    assert "actions/upload-artifact@v7" in text

    # 公共框架测试直接跑 tests/；业务式执行必须复用统一 run.py，而不是 CI 自己拼 pytest 逻辑。
    assert "python -m pytest tests" in text
    assert "python run.py --env test --level smoke" in text
    # 失败后仍需上传报告，确保红灯时也能下载 JUnit/Allure/run.json 排障。
    assert "if: always()" in text


def test_jenkins_pipeline_is_parameterized_and_archives_evidence():
    """Jenkinsfile 应可切换任意环境与层级，并把真实测试证据归档。"""
    assert JENKINSFILE_PATH.is_file(), f"missing Jenkinsfile: {JENKINSFILE_PATH}"
    text = JENKINSFILE_PATH.read_text(encoding="utf-8")

    # ENV_NAME 使用自由字符串而不是 shortlink/order 等枚举，新增项目环境无需修改 Jenkinsfile。
    assert "name: 'ENV_NAME'" in text
    # LEVEL 只依赖框架已经稳定的 smoke/core/regression 三层语义。
    assert "name: 'LEVEL'" in text
    assert "smoke" in text and "core" in text and "regression" in text
    # ENV_FILE 只是一个可选“外部环境 YAML 路径”，不承载用户名、密码或任何 SUT 业务字段。
    assert "name: 'ENV_FILE'" in text
    # Jenkins 通过框架通用 API_TEST_ENV_FILE 把路径传给 ConfigManager，不复制私有文件到 Workspace。
    assert "API_TEST_ENV_FILE" in text
    assert "fileExists" in text
    # Jenkins 只调用统一 Runner；环境和层级由参数传入，避免形成第二套调度实现。
    assert "run.py --env" in text
    assert "ENV_NAME" in text and "LEVEL" in text
    # post/always 下应同时保留机器可读 JUnit 和可下载报告文件。
    assert "post" in text and "always" in text
    assert "junit" in text
    assert "archiveArtifacts" in text


def test_public_ci_files_do_not_hardcode_current_sut():
    """公共 CI 文件禁止写死当前短链接 SUT 的环境名、域名、表名或 Redis Key。"""
    # 两个文件都必须先存在，避免“文件缺失所以扫描结果为空”的假绿。
    assert WORKFLOW_PATH.is_file()
    assert JENKINSFILE_PATH.is_file()
    combined = (
        WORKFLOW_PATH.read_text(encoding="utf-8")
        + "\n"
        + JENKINSFILE_PATH.read_text(encoding="utf-8")
    ).lower()
    # 业务词命中时直接指出具体 token，便于后续接新 SUT 时快速定位架构回归。
    for token in _FORBIDDEN_SUT_TOKENS:
        assert token.lower() not in combined, f"public CI hardcodes SUT token: {token}"
