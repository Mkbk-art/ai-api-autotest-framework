"""声明式 API Case V2 的数据契约与 YAML 解析。

CaseSpec 把项目 YAML 从“任意字典”提升为稳定、可索引的测试资产。它只描述
一条测试是什么以及如何交给现有 ApiRunner 执行，不包含任何具体被测系统业务逻辑。
复杂控制流必须留在 Python Workflow，YAML 不允许演化为第二门编程语言。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Mapping, TYPE_CHECKING

if TYPE_CHECKING:
    from contracts.model import Operation

import yaml


class CaseSpecError(ValueError):
    """表示 YAML Test Specification 不符合框架契约。"""


_CONTROL_FLOW_KEYS = {"if", "else", "for", "while", "try", "finally"}
_EXECUTION_MODES = {"declarative", "workflow"}
_PATH_PARAM_PATTERN = re.compile(r"\{([^{}]+)\}")


def _non_empty_text(value: Any, *, field_name: str, source: Path) -> str:
    """读取必需非空字符串，并把错误固定在 collection 阶段暴露。"""
    if not isinstance(value, str) or not value.strip():
        raise CaseSpecError(f"{field_name} must be non-empty text: {source}")
    return value.strip()


def _text_tuple(value: Any, *, field_name: str, source: Path) -> tuple[str, ...]:
    """把可选字符串列表规范化为不可变 tuple。"""
    if value is None:
        return ()
    if not isinstance(value, list):
        raise CaseSpecError(f"{field_name} must be a list of strings: {source}")
    items: list[str] = []
    for item in value:
        normalized = _non_empty_text(item, field_name=field_name, source=source)
        if normalized not in items:
            items.append(normalized)
    return tuple(items)


@dataclass(frozen=True)
class CaseSpec:
    """一条可执行或可编排的声明式 API 测试规格。"""

    case_id: str
    name: str
    level: str
    request: Mapping[str, Any]
    assertions: tuple[Mapping[str, Any], ...]
    operation_id: str | None = None
    operations: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    execution: str = "declarative"
    extract: Mapping[str, Any] = field(default_factory=dict)
    poll: Mapping[str, Any] | None = None
    cleanup: tuple[str, ...] = ()
    workflow: Mapping[str, Any] = field(default_factory=dict)
    hooks: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    source: Path | None = None

    @property
    def operation_ids(self) -> tuple[str, ...]:
        """返回该测试资产绑定的全部 API Operation，并保持稳定顺序。"""
        values: list[str] = []
        if self.operation_id is not None:
            values.append(self.operation_id)
        for operation_id in self.operations:
            if operation_id not in values:
                values.append(operation_id)
        return tuple(values)

    @property
    def marker_names(self) -> tuple[str, ...]:
        """返回由 level + tags 构成且保持顺序的 Pytest marker 名称。"""
        values: list[str] = [self.level]
        for tag in self.tags:
            if tag not in values:
                values.append(tag)
        return tuple(values)

    def to_runner_parts(self, operation: "Operation | None" = None) -> tuple[dict[str, Any], dict[str, Any]]:
        """转换为现有 ``ApiRunner.run(base_info, test_case)`` 所需结构。

        Contract-bound Case 的 method/path/service 来自当前 ``Operation``；Case YAML 只保留
        请求数据与 path_params。没有 ``operation_id`` 的 standalone Case 继续使用自己
        声明的 method/path/url。
        """
        request = dict(self.request)
        raw_url = request.pop("url", None)
        raw_path = request.pop("path", None)
        raw_method = request.pop("method", None)
        path_params = request.pop("path_params", {})

        if operation is not None:
            method = operation.method
            placeholders = _PATH_PARAM_PATTERN.findall(operation.path)
            provided = set(path_params) if isinstance(path_params, dict) else set()
            missing = [name for name in placeholders if name not in provided]
            extra = sorted(provided - set(placeholders))
            if missing:
                raise CaseSpecError(
                    f"request.path_params missing Contract path parameter(s) {missing}: {self.source}"
                )
            if extra:
                raise CaseSpecError(
                    f"request.path_params contains unknown Contract path parameter(s) {extra}: {self.source}"
                )
            raw_url = operation.path
            for name in placeholders:
                raw_url = raw_url.replace("{" + name + "}", str(path_params[name]))
        else:
            raw_url = raw_url if raw_url is not None else raw_path
            method = raw_method

        if not isinstance(raw_url, str) or not raw_url.strip():
            raise CaseSpecError(f"request endpoint must resolve to non-empty text: {self.source}")
        if not isinstance(method, str) or not method.strip():
            raise CaseSpecError(f"request method must resolve to non-empty text: {self.source}")

        api_name = request.pop("api_name", self.name)
        headers = request.pop("headers", request.pop("header", {}))
        if headers is None:
            headers = {}
        if not isinstance(headers, dict):
            raise CaseSpecError(f"request.headers must be a mapping: {self.source}")

        base_info = {
            "api_name": api_name,
            "url": raw_url,
            "method": method.upper(),
            "header": headers,
        }
        if operation is not None and operation.service:
            base_info["service"] = operation.service
        test_case: dict[str, Any] = {
            "case_id": self.case_id,
            "case_name": self.name,
            "level": self.level,
            "tags": list(self.tags),
            "risks": list(self.risks),
            "requires": list(self.requires),
            "execution": self.execution,
            "validation": [dict(item) for item in self.assertions],
        }
        if self.operation_id is not None:
            test_case["operation_id"] = self.operation_id
        if self.operations:
            test_case["operations"] = list(self.operations)
        if self.extract:
            test_case["extract"] = dict(self.extract)
        if self.poll is not None:
            test_case["poll"] = dict(self.poll)
        if self.cleanup:
            test_case["cleanup"] = list(self.cleanup)
        if self.workflow:
            test_case["workflow"] = dict(self.workflow)
        if self.hooks:
            test_case["hooks"] = {name: list(values) for name, values in self.hooks.items()}
        if self.metadata:
            test_case["metadata"] = dict(self.metadata)

        # endpoint/path_params/service 已在 Contract 适配边界消费；其余字段继续沿用 ApiRunner 支持的
        # json/params/data/request_options 等通用请求参数，不复制网络层。
        for key, value in request.items():
            test_case[key] = value
        return base_info, test_case


def _parse_case(raw: Any, *, source: Path) -> CaseSpec:
    """把 YAML 中单条 mapping 转成 CaseSpec。"""
    if not isinstance(raw, dict):
        raise CaseSpecError(f"each case must be a mapping: {source}")
    forbidden = _CONTROL_FLOW_KEYS.intersection(raw)
    if forbidden:
        names = ", ".join(sorted(forbidden))
        raise CaseSpecError(
            f"YAML case must not contain control flow keys ({names}); use Python Workflow: {source}"
        )

    case_id = _non_empty_text(raw.get("id"), field_name="id", source=source)
    name = _non_empty_text(raw.get("name"), field_name="name", source=source)
    level = _non_empty_text(raw.get("level"), field_name="level", source=source)

    execution = str(raw.get("execution", "declarative")).strip()
    if execution not in _EXECUTION_MODES:
        raise CaseSpecError(
            f"execution must be one of {sorted(_EXECUTION_MODES)}, actual={execution!r}: {source}"
        )

    operation_id = raw.get("operation_id")
    if operation_id is not None:
        operation_id = _non_empty_text(operation_id, field_name="operation_id", source=source)
    operations = _text_tuple(raw.get("operations"), field_name="operations", source=source)

    request = raw.get("request", {} if execution == "workflow" else None)
    if not isinstance(request, dict):
        raise CaseSpecError(f"request must be a mapping: {source}")
    path_params = request.get("path_params")
    if path_params is not None and not isinstance(path_params, dict):
        raise CaseSpecError(f"request.path_params must be a mapping: {source}")

    if execution == "declarative":
        if operation_id is not None:
            if any(field in request for field in ("method", "path", "url")):
                raise CaseSpecError(
                    f"Contract-bound case must not declare request.method/path/url; "
                    f"resolve endpoint from operation_id={operation_id!r}: {source}"
                )
        else:
            endpoint = request.get("url", request.get("path"))
            method = request.get("method")
            if not isinstance(endpoint, str) or not endpoint.strip():
                raise CaseSpecError(f"standalone request requires path or url: {source}")
            if not isinstance(method, str) or not method.strip():
                raise CaseSpecError(f"standalone request requires method: {source}")
            if path_params is not None:
                raise CaseSpecError(
                    f"request.path_params requires operation_id and Contract path template: {source}"
                )

    assertions = raw.get("assertions")
    if not isinstance(assertions, list):
        raise CaseSpecError(f"assertions must be a list: {source}")
    if not all(isinstance(item, dict) for item in assertions):
        raise CaseSpecError(f"every assertion must be a mapping: {source}")

    extract = raw.get("extract", {})
    if not isinstance(extract, dict):
        raise CaseSpecError(f"extract must be a mapping: {source}")
    poll = raw.get("poll")
    if poll is not None and not isinstance(poll, dict):
        raise CaseSpecError(f"poll must be a mapping: {source}")
    workflow = raw.get("workflow", {})
    if not isinstance(workflow, dict):
        raise CaseSpecError(f"workflow must be a mapping: {source}")
    raw_hooks = raw.get("hooks", {})
    if not isinstance(raw_hooks, dict):
        raise CaseSpecError(f"hooks must be a mapping: {source}")
    hooks: dict[str, tuple[str, ...]] = {}
    for stage, names in raw_hooks.items():
        if stage not in {"before_case", "after_response", "teardown"}:
            raise CaseSpecError(f"unsupported hook stage {stage!r}: {source}")
        hooks[stage] = _text_tuple(names, field_name=f"hooks.{stage}", source=source)

    metadata = raw.get("metadata", {})
    if not isinstance(metadata, dict):
        raise CaseSpecError(f"metadata must be a mapping: {source}")

    return CaseSpec(
        case_id=case_id,
        name=name,
        level=level,
        operation_id=operation_id,
        operations=operations,
        tags=_text_tuple(raw.get("tags"), field_name="tags", source=source),
        risks=_text_tuple(raw.get("risks"), field_name="risks", source=source),
        requires=_text_tuple(raw.get("requires"), field_name="requires", source=source),
        cleanup=_text_tuple(raw.get("cleanup"), field_name="cleanup", source=source),
        execution=execution,
        request=request,
        extract=extract,
        assertions=tuple(assertions),
        poll=poll,
        workflow=workflow,
        hooks=hooks,
        metadata=metadata,
        source=source,
    )


def load_case_specs(file_path: str | Path) -> list[CaseSpec]:
    """加载一份 V2 YAML Test Specification。"""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"YAML testcase file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise CaseSpecError(f"YAML testcase must be UTF-8: {path}") from exc
    except yaml.YAMLError as exc:
        raise CaseSpecError(f"Invalid YAML syntax in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise CaseSpecError(f"V2 YAML top-level mapping required: {path}")
    if data.get("version") != 2:
        raise CaseSpecError(f"YAML version must be 2: {path}")
    raw_cases = data.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise CaseSpecError(f"YAML cases must be a non-empty list: {path}")
    return [_parse_case(item, source=path) for item in raw_cases]
