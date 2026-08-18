"""YAML 测试用例可调用的动态数据函数库。

YAML 本身只能保存静态数据，本模块通过 :class:`DebugTalk` 暴露随机字符串、
时间、Hash、环境变量和上下文读取等函数，使用例可以使用 ``${random_string(8)}``、
``${future_date(7)}`` 等表达式。普通 ``${token}`` 变量由 VariableContext 负责，
DebugTalk 主要负责“值如何动态计算”。
"""
from __future__ import annotations

# datetime 提供可重复理解的日期/时间测试数据，不依赖第三方库。
import datetime
# hashlib 保留基线 DSL 的摘要计算兼容能力。
import hashlib
# os.environ 仅用于显式 CI Secret/历史兼容；普通项目配置优先走 YAML config()。
import os
# random/string 用于生成无业务耦合的动态测试值。
import random
import string
# time 提供秒/毫秒时间戳，常用于测试数据唯一标识。
import time

from core.variable_context import VariableContext


class DebugTalk:
    """为 YAML DSL 提供可白名单调用的动态测试数据函数。"""

    def __init__(
        self,
        context: VariableContext | None = None,
        runtime_config: dict | None = None,
    ) -> None:
        """绑定当前测试的变量上下文和一次运行的最终 YAML 配置。

        ``runtime_config`` 由 :class:`ApiRunner` 注入，来源就是 ConfigManager 已合并完成的
        ``config.yaml + env.<name>.yaml``。项目级账号、域名或其他静态参数可以直接保存在
        所选环境 YAML 中，不要求每次运行前通过终端重复注入。
        """
        # VariableContext 只保存接口运行时变量，例如 token/resource_id 等跨接口动态数据。
        self.context = context or VariableContext()
        # 环境配置单独保存，避免把 password 复制进 VariableContext 的 debug snapshot。
        self.runtime_config = runtime_config or {}

    # config() 是“环境 YAML -> 用例 DSL”的通用桥梁，不能在这里写任何具体项目字段。
    def config(self, section: str, key: str):
        """读取当前环境 YAML 中的必填配置值，供 ``${config(a,b)}`` 使用。

        Args:
            section: 顶层配置段，例如 ``project`` 或 ``credentials``。
            key: 配置字段，例如 ``username``、``region`` 或其他项目参数。

        Raises:
            RuntimeError: 配置缺失、为空或仍是 ``CHANGE_ME`` 占位值。
        """
        # 顶层 section 必须是映射，避免拼写错误时返回神秘的 None。
        # section/key 都由 YAML Case 显式传入，因此同一框架可读取任意新项目的环境配置。
        values = self.runtime_config.get(str(section))
        if not isinstance(values, dict):
            raise RuntimeError(
                f"Required runtime config {section}.{key} is not configured; "
                "edit the selected environment YAML before running this test"
            )
        # 读取具体字段；字符串会额外拒绝空白和交付包中的 CHANGE_ME 占位值。
        # 不把读取值写入日志；凭据等敏感配置仅在请求组装阶段使用并由 sanitizer 处理。
        value = values.get(str(key))
        if value is None or (isinstance(value, str) and (not value.strip() or value.strip() == "CHANGE_ME")):
            raise RuntimeError(
                f"Required runtime config {section}.{key} is not configured; "
                "edit the selected environment YAML before running this test"
            )
        # 保留 YAML 原始类型，例如整数端口不会被这里强制转换成字符串。
        return value

    def env(self, name: str) -> str:
        """读取必需的通用 OS 环境变量，保留历史 DSL 与其他项目兼容能力。

        新项目优先使用 ``${config(section,key)}`` 读取环境 YAML；本方法继续保留给
        CI Secret、临时凭据或历史用例等确实需要 OS 环境变量的数据。返回值本身不记录
        日志，后续请求中的敏感字段仍由 :mod:`utils.sanitizer` 脱敏。

        Args:
            name: 调用方明确声明的通用环境变量名称。

        Raises:
            RuntimeError: 环境变量不存在或值为空。
        """
        # 变量名来自用例显式声明，框架不会枚举或输出整个进程环境。
        value = os.environ.get(str(name))
        if value is None or value == "":
            raise RuntimeError(
                f"Required environment variable {name!r} is not set; "
                "configure it before running the selected test environment"
            )
        # 返回值只交给调用方，不在 DebugTalk 内部记录，减少意外敏感信息扩散。
        return value

    def random_string(self, length=8) -> str:
        """生成由英文字母和数字组成的随机字符串。"""
        # 字母数字集合适用于资源名、描述后缀等通用场景，避免引入 URL/SQL 特殊字符。
        return "".join(random.choices(string.ascii_letters + string.digits, k=int(length)))

    def invalid_password(self) -> str:
        """生成与真实凭据完全解耦的错误密码，供鉴权异常用例使用。

        本函数故意不读取 ``runtime_config`` 中的真实密码，也不基于真实密码做拼接。这样即使
        异常请求失败并进入 Pytest/Requests traceback，测试数据本身也不会携带真实凭据片段。
        固定前缀用于识别“这是自动化故意构造的错误值”，随机后缀避免长期复用同一字符串。
        """

        # 24 位随机后缀足够避免不同运行之间重复，同时不依赖任何外部状态或敏感配置。
        suffix = self.random_string(24)
        # 返回值只由固定测试前缀和随机字符串组成，不接触真实登录密码。
        return f"__api_autotest_invalid__{suffix}"

    def random_int(self, min_val=1, max_val=99999) -> int:
        """生成指定闭区间内的随机整数。"""
        return random.randint(int(min_val), int(max_val))

    # 时间函数只负责生成值，不决定字段名或具体业务含义。
    def timestamp(self) -> int:
        """返回当前秒级 Unix 时间戳。"""
        return int(time.time())

    def timestamp_ms(self) -> int:
        """返回当前毫秒级 Unix 时间戳。"""
        return int(time.time() * 1000)

    def today_str(self) -> str:
        """返回 ``YYYY-MM-DD`` 格式的当前日期。"""
        return datetime.date.today().strftime("%Y-%m-%d")

    def now_str(self) -> str:
        """返回 ``YYYY-MM-DD HH:MM:SS`` 格式的当前时间。"""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def future_date(self, days=7) -> str:
        """返回从今天起指定天数后的日期字符串。"""
        return (datetime.date.today() + datetime.timedelta(days=int(days))).strftime("%Y-%m-%d")

    # 摘要函数用于兼容某些签名/测试数据计算，但不作为密码学安全方案宣传。
    def md5(self, params) -> str:
        """返回参数字符串的 MD5 十六进制摘要；仅用于测试数据计算。"""
        return hashlib.md5(str(params).encode("utf-8")).hexdigest()

    def sha1(self, params) -> str:
        """返回参数字符串的 SHA1 十六进制摘要；仅用于测试数据计算。"""
        return hashlib.sha1(str(params).encode("utf-8")).hexdigest()

    def get_extract_data(self, node_name, index=None):
        """兼容旧 YAML，从当前 VariableContext 读取已经提取的变量。

        ``index`` 用于历史列表语法，采用从 1 开始的索引；新 YAML 更推荐直接
        使用 ``${variable}``，只有兼容旧用例时才需要该函数。
        """
        # 所有读取都来自当前测试自己的 VariableContext，不访问模块级全局变量。
        data = self.context.get(node_name)
        # 历史 index 采用 1-based；越界时回退首项以保持基线项目兼容行为。
        if index is not None and isinstance(data, list):
            idx = int(index) - 1
            return data[idx] if 0 <= idx < len(data) else data[0]
        return data
