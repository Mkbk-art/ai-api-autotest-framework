"""CaseSpec 的统一执行器。

CaseExecutor 负责项目上下文生命周期与 ApiRunner 之间的桥接。普通 YAML Runtime 和
复杂 Python Workflow 都使用同一执行器，因此 Workflow 不需要重新实现 HTTP 请求、
变量提取和统一断言。
"""
from __future__ import annotations

from contextlib import ExitStack
from typing import Any

from contracts.model import ApiContract
from core.case_registry import CaseRegistry
from core.case_spec import CaseSpec
from core.context_provider import CaseHookRegistry, ContextProviderError, ContextProviderRegistry


class CaseExecutor:
    """执行 CaseSpec，并管理 requires Provider 与项目 Hook 生命周期。"""

    def __init__(
        self,
        *,
        runner: Any,
        registry: CaseRegistry,
        contract: ApiContract | None = None,
        providers: ContextProviderRegistry | None = None,
        hooks: CaseHookRegistry | None = None,
    ) -> None:
        self.runner = runner
        self.registry = registry
        self.contract = contract
        self.providers = providers or ContextProviderRegistry()
        self.hooks = hooks or CaseHookRegistry()
        self._stack = ExitStack()
        self._entered = False
        self._active_contexts: set[str] = set()
        self._resolving_contexts: list[str] = []

    def __enter__(self) -> "CaseExecutor":
        self._entered = True
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            return bool(self._stack.__exit__(exc_type, exc, tb))
        finally:
            self._entered = False
            self._active_contexts.clear()
            self._resolving_contexts.clear()

    def _require_entered(self) -> None:
        if not self._entered:
            raise RuntimeError("CaseExecutor must be used as a context manager")

    def ensure_context(self, name: str) -> None:
        """确保指定上下文只初始化一次，并检测 Provider 循环依赖。"""
        self._require_entered()
        if name in self._active_contexts:
            return
        if name in self._resolving_contexts:
            chain = " -> ".join([*self._resolving_contexts, name])
            raise ContextProviderError(f"context provider cycle detected: {chain}")

        self._resolving_contexts.append(name)
        try:
            spec = self.providers.get_spec(name)
            # Declared dependencies are the single inspectable relation used by
            # Stage 6; resolving them here also keeps runtime order consistent
            # with the dependency graph. Legacy providers simply expose none.
            for dependency in spec.requires:
                self.ensure_context(dependency)
            result = spec.provider(self)
            # Provider 可以返回 contextmanager；ExitStack 让 setup/cleanup 在整个 CaseExecutor
            # 生命周期内保持一致，也允许 Workflow 在多个原子 Case 之间共享同一上下文。
            if hasattr(result, "__enter__") and hasattr(result, "__exit__"):
                self._stack.enter_context(result)
            self._active_contexts.add(name)
        finally:
            self._resolving_contexts.pop()

    def _run_hooks(self, case: CaseSpec, stage: str, response: Any) -> None:
        for name in case.hooks.get(stage, ()):
            self.hooks.run(name, self, case, response)

    def _run_teardown(self, case: CaseSpec, response: Any) -> None:
        self._run_hooks(case, "teardown", response)

    def _operation_for_case(self, case: CaseSpec):
        """解析 Contract-bound Case 的当前 Operation；standalone Case 返回 None。"""
        if case.operation_id is None:
            return None
        if self.contract is None:
            raise RuntimeError(
                f"Contract-bound case {case.case_id!r} requires an ApiContract before HTTP execution"
            )
        try:
            return self.contract.get_operation(case.operation_id)
        except KeyError as exc:
            raise RuntimeError(
                f"Contract-bound case {case.case_id!r} references unknown operation "
                f"{case.operation_id!r}"
            ) from exc

    def build_runner_parts(
        self, case_or_id: CaseSpec | str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """把稳定 Case 解析成 ApiRunner 输入，供普通执行和 Python 编排复用。"""
        case = self.registry.get(case_or_id) if isinstance(case_or_id, str) else case_or_id
        return case.to_runner_parts(self._operation_for_case(case))

    def execute(
        self,
        case_or_id: CaseSpec | str,
        *,
        overrides: dict[str, Any] | None = None,
        defer_teardown: bool = False,
    ) -> Any:
        """执行一条 Case，并返回真实 HTTP Response。

        Args:
            case_or_id: CaseSpec 或 Registry 中的稳定 case_id。
            overrides: Workflow 临时传入的 case-scope 动态变量。
            defer_teardown: 为复杂 Workflow 延迟当前 Case 的 teardown 到 Executor 关闭时。
        """
        self._require_entered()
        case = self.registry.get(case_or_id) if isinstance(case_or_id, str) else case_or_id
        for provider_name in case.requires:
            self.ensure_context(provider_name)

        # 临时输入仅写 case scope，避免覆盖 provider 准备的 scenario/session 状态。
        self.runner.context.clear("case")
        for key, value in (overrides or {}).items():
            self.runner.context.set(key, value, scope="case")

        response: Any = None
        teardown_scheduled = False
        teardown_completed = False
        self._run_hooks(case, "before_case", None)
        try:
            base_info, test_case = self.build_runner_parts(case)
            if case.poll is not None:
                response = self.runner.run_polling(base_info, test_case)
            else:
                response = self.runner.run(base_info, test_case)
            self._run_hooks(case, "after_response", response)
            if defer_teardown:
                # 只有主步骤成功后才延迟 teardown；如果执行中途抛错，finally 会立即清理部分资源。
                self._stack.callback(self._run_teardown, case, response)
                teardown_scheduled = True
            else:
                self._run_teardown(case, response)
                teardown_completed = True
            return response
        finally:
            # 写操作即使在响应断言阶段失败，也可能已经在 SUT 中产生资源。只要当前 Case 声明了
            # teardown，就必须在异常路径执行一次，避免测试失败同时污染后续回归环境。
            if not teardown_scheduled and not teardown_completed and case.hooks.get("teardown"):
                self._run_teardown(case, response)
            # case scope 只属于本次原子调用；scenario/provider 状态继续供后续 Workflow 步骤使用。
            self.runner.context.clear("case")
