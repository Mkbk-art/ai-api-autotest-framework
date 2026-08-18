"""YAML 接口测试用例加载与 Pytest 参数化适配。

本模块是“YAML 驱动”进入 Pytest 的统一入口：它只解析用例文件、校验结构，
并把 YAML 中声明的 ``level`` / ``tags`` 转换为 Pytest marks。它不理解任何
具体业务，也不保存 token、订单号等运行时数据；这些职责分别属于项目 YAML
和 :mod:`core.variable_context`。因此接入新的被测项目时，普通单接口场景通常
只新增/修改 YAML，而不需要复制一套 Python 装饰器和参数化代码。
"""
from __future__ import annotations

# os.fspath 让 PathLike 和普通字符串都能走同一条路径处理逻辑。
import os
# Path 负责跨 Windows/Linux 的 UTF-8 YAML 文件定位与读取。
from pathlib import Path
# Any 用于表达 YAML 反序列化后的动态映射/列表结构。
from typing import Any

# PyYAML 只负责安全反序列化；业务变量替换发生在 ApiRunner，而不是加载阶段。
import yaml


def get_testcase_yaml(
    file_path: str | os.PathLike[str],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """读取并校验 YAML，用统一二元组结构返回所有 Case。

    Args:
        file_path: YAML 文件路径，可传字符串或 ``Path``。

    Returns:
        每条参数化用例对应的 ``(baseInfo, testCase)`` 二元组列表。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 文件不是 UTF-8、YAML 语法非法或结构不符合框架约定。
    """
    # 先归一化路径；这里不尝试猜测目录，防止项目适配层写错路径时静默读到别的文件。
    path = Path(os.fspath(file_path))
    # 配置文件缺失属于用例定义错误，应在 collection 阶段立即暴露，而不是运行到请求阶段。
    if not path.is_file():
        raise FileNotFoundError(f"YAML testcase file not found: {path}")

    try:
        # 框架统一要求 UTF-8，确保中文注释和跨平台提交不会依赖本机默认编码。
        with path.open("r", encoding="utf-8") as file_obj:
            # safe_load 禁止构造任意 Python 对象，YAML 只作为声明式测试数据使用。
            data = yaml.safe_load(file_obj)
    except UnicodeDecodeError as exc:
        # 编码错误单独转成 ValueError，错误信息明确指出是哪份用例文件。
        raise ValueError(f"YAML testcase must be UTF-8: {path}") from exc
    except yaml.YAMLError as exc:
        # YAML 语法错误保留原始解析异常作为 cause，便于 Pytest traceback 定位行号。
        raise ValueError(f"Invalid YAML syntax in {path}: {exc}") from exc

    # 顶层固定为列表，允许一份业务域 YAML 声明多个接口 baseInfo，而不是“一接口一文件”。
    if not isinstance(data, list):
        raise ValueError(f"YAML testcase top-level list required: {path}")

    # 最终扁平化为 Pytest 参数列表；同一个 baseInfo 下可配置多个正常/异常/回归 Case。
    testcase_list: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for entry_index, entry in enumerate(data):
        # 每个顶层元素必须是映射，避免无效标量被后续代码当成接口定义。
        if not isinstance(entry, dict):
            raise ValueError(f"Entry {entry_index} must be a mapping: {path}")

        # baseInfo 描述接口级公共信息，testCase 描述同一接口下的不同测试数据和断言。
        base_info = entry.get("baseInfo")
        test_cases = entry.get("testCase")
        # 接口定义必须是 mapping，method/url/header 才能由 ApiRunner 统一读取。
        if not isinstance(base_info, dict):
            raise ValueError(f"Entry {entry_index} missing mapping baseInfo: {path}")
        # 至少保留一个 Case，防止空接口定义在 collection 时看似存在但永远不执行。
        if not isinstance(test_cases, list) or not test_cases:
            raise ValueError(f"Entry {entry_index} requires non-empty testCase list: {path}")

        for case_index, test_case in enumerate(test_cases):
            # 单条 Case 也必须是映射；level/tags/json/validation 等元数据都从这里读取。
            if not isinstance(test_case, dict):
                raise ValueError(
                    f"testCase {entry_index}.{case_index} must be a mapping: {path}"
                )
            # baseInfo 不复制修改，多个 Case 共享同一接口定义，减少 YAML 重复字段。
            testcase_list.append((base_info, test_case))

    # Loader 不做动态变量替换，`${...}` 原样交给 ApiRunner 在真实运行上下文中解析。
    return testcase_list


def _case_marker_names(test_case: dict[str, Any]) -> list[str]:
    """规范化单条 YAML Case 的 level/tags，并保持声明顺序去重。"""
    # level 是 smoke/core/regression 等执行层级；为空时表示该 Case 不绑定固定层级。
    mark_names: list[str] = []
    level = test_case.get("level")
    if level is not None:
        # 非空文本是 marker 的最低要求；结构问题在 collection 阶段直接暴露。
        if not isinstance(level, str) or not level.strip():
            raise ValueError(f"YAML case level must be non-empty text: {test_case!r}")
        mark_names.append(level.strip())

    # tags 承载模块、能力或异常类型等横向分类，由具体项目 YAML 自己命名。
    tags = test_case.get("tags", [])
    if not isinstance(tags, list) or not all(
        isinstance(item, str) and item.strip() for item in tags
    ):
        raise ValueError(f"YAML case tags must be a list of non-empty strings: {test_case!r}")
    for tag in tags:
        # 统一 trim 并按首次出现顺序去重，避免 level 与 tag 或重复 tag 生成多个同名 mark。
        normalized = tag.strip()
        if normalized not in mark_names:
            mark_names.append(normalized)
    return mark_names


def get_testcase_marker_names(file_path: str | os.PathLike[str]) -> set[str]:
    """发现一份 YAML 中声明的全部 marker，供 Pytest collection 前动态注册。

    这样业务标签不需要预先写进公共 ``pytest.ini``：新增项目只要在 YAML 的 ``level``
    和 ``tags`` 中声明分类，公共 Pytest glue 就能注册它们，同时继续启用 strict-markers。
    """
    # set 只用于注册去重，不承诺 marker 输出顺序；单 Case 参数化仍由 _case_marker_names 保序。
    names: set[str] = set()
    for _, test_case in get_testcase_yaml(file_path):
        # 复用同一规范化函数，保证“注册”和“真正参数化”看到完全一致的 marker 名称。
        names.update(_case_marker_names(test_case))
    return names


def get_testcase_params(
    file_path: str | os.PathLike[str],
    *,
    workflows: set[str] | None = None,
):
    """把 YAML Case 元数据转换为 ``pytest.mark.parametrize`` 参数。

    ``level`` 用于 smoke/core/regression 分层；``tags`` 用于 auth、storage、redirect
    等业务/能力标签；``workflow`` 仅用于筛选需要某类 Python 编排的 Case。这样
    marker 和用例等级都由 YAML 声明，Python 测试入口只负责选择一个业务域文件。

    Args:
        file_path: 当前业务域 YAML 文件。
        workflows: 可选 workflow 白名单；``None`` 表示不过滤。

    Returns:
        可直接传给 ``pytest.mark.parametrize`` 的 ``pytest.param`` 列表。
    """
    # pytest 仅在生成参数时需要，局部导入避免 case_loader 成为普通 YAML 解析的强依赖入口。
    import pytest

    # 每个元素都保留 base_info/test_case，同时附带 YAML 声明的 marks 和可读 Case ID。
    params = []
    for base_info, test_case in get_testcase_yaml(file_path):
        # workflow 解决“少量复杂流程需要 Python 编排”的问题，但不把流程细节写死在框架核心。
        workflow = test_case.get("workflow")
        if workflows is not None and workflow not in workflows:
            # 当前 Python 入口只收集自己负责的 workflow，其他 Case 留给同业务域的另一个入口。
            continue

        # level/tags 的规范化与动态 marker 注册共用同一函数，避免两套规则逐渐漂移。
        mark_names = _case_marker_names(test_case)
        # marker 已由公共 conftest 从仓库 YAML 自动注册；strict-markers 仍可发现拼写错误。
        marks = [getattr(pytest.mark, name) for name in mark_names]
        # Case ID 优先使用 YAML case_name，使 `pytest -v` 输出直接对应业务场景名称。
        case_id = str(test_case.get("case_name", "unnamed"))
        # Python 入口不再重复声明 level/tag，所有分类信息与请求/断言一起保存在 YAML。
        params.append(pytest.param(base_info, test_case, marks=marks, id=case_id))

    # 返回空列表也是合法结果，例如某个 workflow 在当前 YAML 中暂时没有 Case。
    return params
