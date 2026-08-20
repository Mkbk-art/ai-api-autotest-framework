"""声明式 Case 的统一索引。

Registry 让 Pytest Runtime、Python Workflow、后续 Contract/Coverage 模块都通过稳定
``case_id`` 访问测试资产，而不是依赖 YAML 文件名或中文展示名称。
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable

from core.case_spec import CaseSpec, CaseSpecError, load_case_specs


class CaseRegistry:
    """保存项目已加载的全部 CaseSpec，并提供稳定索引。"""

    def __init__(self, cases: Iterable[CaseSpec]) -> None:
        self._by_id: dict[str, CaseSpec] = {}
        self._by_operation: dict[str, list[CaseSpec]] = defaultdict(list)
        for case in cases:
            if case.case_id in self._by_id:
                raise CaseSpecError(f"duplicate case id: {case.case_id}")
            self._by_id[case.case_id] = case
            if case.operation_id:
                self._by_operation[case.operation_id].append(case)

    @classmethod
    def from_paths(cls, paths: Iterable[str | Path]) -> "CaseRegistry":
        """按给定 YAML 文件集合构建 Registry。"""
        cases: list[CaseSpec] = []
        for path in paths:
            cases.extend(load_case_specs(path))
        return cls(cases)

    def get(self, case_id: str) -> CaseSpec:
        """按稳定 ID 获取 Case；未知 ID 明确失败。"""
        try:
            return self._by_id[case_id]
        except KeyError as exc:
            raise KeyError(f"unknown case id: {case_id}") from exc

    def all_cases(self) -> tuple[CaseSpec, ...]:
        """按加载顺序返回全部 Case。"""
        return tuple(self._by_id.values())

    def declarative_cases(self) -> tuple[CaseSpec, ...]:
        """返回可以由框架 Generic Runtime 自动执行的 Case。"""
        return tuple(case for case in self._by_id.values() if case.execution == "declarative")

    def cases_for_operation(self, operation_id: str) -> tuple[CaseSpec, ...]:
        """返回绑定到指定 API Operation 的 Case，为后续 Coverage 提供基础。"""
        return tuple(self._by_operation.get(operation_id, ()))
