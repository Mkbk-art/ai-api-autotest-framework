"""仓库卫生守门测试。

这些测试不是业务功能测试，而是防止开发阶段的本机文件和私有 AI 配置被误提交、
误打包。它们直接锁定此前已经真实发生过的 ``.idea`` 回归，以及 Stage 7.1 新增的
``config/ai.local.yaml`` 私有覆盖文件边界。
"""
from __future__ import annotations

# subprocess 只在存在 Git 元数据时检查 Git index，验证“忽略规则”之外还没有历史已跟踪文件。
import subprocess
# Path 统一定位仓库根目录，避免测试依赖当前工作目录。
from pathlib import Path

# pytest 用于在发布 ZIP 等没有 .git 元数据的环境里跳过 Git index 检查，而不是误判失败。
import pytest


ROOT = Path(__file__).parents[2]


def test_gitignore_protects_ide_and_private_ai_config():
    """根 .gitignore 必须同时保护 IDE 元数据和可能包含真实 Key 的 AI 本地覆盖文件。"""

    content = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert ".idea/" in content
    assert "config/ai.local.yaml" in content
    assert "config/env.*.private.yaml" in content


def test_public_tree_does_not_track_idea_directory():
    """Git 仓库不能继续跟踪 .idea；仅添加 ignore 无法修复已经进入 index 的历史文件。"""

    if not (ROOT / ".git").exists():
        pytest.skip("git metadata is not available in packaged artifact")

    result = subprocess.run(
        ["git", "ls-files", ".idea"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert not result.stdout.strip()

def test_private_local_configs_are_never_tracked_by_git():
    """本机可以存在私有覆盖文件，但它们绝不能进入 Git index。"""

    if not (ROOT / ".git").exists():
        pytest.skip("git metadata is not available in packaged artifact")

    result = subprocess.run(
        ["git", "ls-files", "config/ai.local.yaml", "config/env.*.private.yaml"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert not result.stdout.strip()
