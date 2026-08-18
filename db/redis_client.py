"""通用 Redis 只读客户端。

客户端只封装 YAML 断言常用的 key/hash/set 读取操作；它不知道登录、订单、短链接、UV 等任何
业务概念。Key 的完整值由测试项目自己的 YAML/运行时上下文提供，因此更换被测系统时无需
修改本模块。
"""
from __future__ import annotations

# dataclass 用于不可变连接设置，password 使用 repr=False 避免对象打印泄露。
from dataclasses import dataclass, field
# Callable 用于 Fake redis factory 注入，Mapping 用于通用 runtime_config。
from typing import Any, Callable, Mapping

# 复用 MySQL 模块中的通用命名数据源/必填字段/秘密标量解析规则。
from db.mysql_client import _required_text, _secret_text, _source_mapping


# RedisFactory 与 redis.Redis 构造器保持兼容，单元测试可注入纯内存 Fake。
RedisFactory = Callable[..., Any]


@dataclass(frozen=True)
class RedisSettings:
    """一个命名 Redis 数据源的不可变连接配置。"""

    # Redis 地址。
    host: str
    # Redis TCP 端口。
    port: int
    # Redis logical DB 编号。
    db: int = 0
    # 无密码时允许 None；真实密码不参与 repr。
    password: str | None = field(default=None, repr=False)
    # socket_timeout 控制单次网络读写等待。
    socket_timeout: float = 5.0
    # protocol 显式控制 RESP 线协议；默认 2 兼容 Redis 5.x 及不支持 HELLO 的代理。
    protocol: int = 2

    @classmethod
    def from_runtime_config(
        cls,
        runtime_config: Mapping[str, Any],
        *,
        source: str = "default",
    ) -> "RedisSettings":
        """从 ``data_sources.redis.<source>`` 创建 Redis 设置。"""
        # 使用与 MySQL 相同的命名数据源结构，便于不同项目统一环境配置。
        values = _source_mapping(runtime_config, "redis", source)
        # path 只用于错误提示。
        path = f"data_sources.redis.{source}"
        # Redis 常见本地环境不启用 requirepass，因此 password 可显式为 null。
        raw_password = values.get("password")
        # 非空密码仍走同一秘密标量规范化，不在错误中回显真实值。
        password = _secret_text(raw_password, path=f"{path}.password", allow_none=True)
        # 构造后 RedisClient 不再关心 YAML 原始类型。
        return cls(
            host=_required_text(values, "host", path=path),
            port=int(values.get("port", 6379)),
            db=int(values.get("db", 0)),
            password=password,
            socket_timeout=float(values.get("socket_timeout", 5)),
            # Redis 数据源可按环境选择 RESP2/RESP3；未声明时使用兼容性更好的 RESP2。
            protocol=int(values.get("protocol", 2)),
        )


class RedisClient:
    """为统一断言引擎提供通用 Redis 读取操作。"""

    def __init__(self, settings: RedisSettings, factory: RedisFactory | None = None) -> None:
        """保存设置并延迟创建真实 redis-py 客户端。"""
        # Settings 已经完成命名数据源配置解析。
        self.settings = settings
        # factory 用于 Fake Client 注入和离线单元测试。
        self._factory = factory
        # 同一个 Assertions 实例内复用一个底层 Redis client，减少重复 TCP 初始化。
        self._client = None

    @classmethod
    def from_runtime_config(
        cls,
        runtime_config: Mapping[str, Any],
        *,
        source: str = "default",
        factory: RedisFactory | None = None,
    ) -> "RedisClient":
        """从环境 YAML 的命名 Redis 数据源创建客户端。"""
        # AssertionEngine 只指定 source，不需要知道 host/db/password 等连接细节。
        return cls(
            RedisSettings.from_runtime_config(runtime_config, source=source),
            factory=factory,
        )

    def _raw(self):
        """首次读取时创建 redis-py 客户端，并启用字符串解码。"""
        # 已建立客户端直接复用。
        if self._client is not None:
            return self._client
        # 单元测试/兼容场景优先使用外部注入 factory。
        if self._factory is not None:
            self._client = self._factory(
                host=self.settings.host,
                port=self.settings.port,
                db=self.settings.db,
                password=self.settings.password,
                socket_timeout=self.settings.socket_timeout,
                # protocol 显式透传，避免 redis-py 主版本升级改变默认线协议。
                protocol=self.settings.protocol,
                # decode_responses=True 让 YAML expected 可以直接按字符串比较。
                decode_responses=True,
            )
            return self._client
        # 只有用例真正执行 redis_* 断言时才导入 redis-py。
        try:
            import redis
        except ImportError as exc:
            # 给用户明确安装提示。
            raise RuntimeError(
                "redis-py is required for Redis YAML assertions; install project dependencies"
            ) from exc
        # 创建通用 Redis client；不在这里拼任何业务 Key。
        self._client = redis.Redis(
            host=self.settings.host,
            port=self.settings.port,
            db=self.settings.db,
            password=self.settings.password,
            socket_timeout=self.settings.socket_timeout,
            # 显式协议版本保证同一环境在 redis-py 不同主版本下行为一致。
            protocol=self.settings.protocol,
            decode_responses=True,
        )
        return self._client

    def exists(self, key: str) -> bool:
        """判断普通 Redis Key 是否存在。"""
        # Redis EXISTS 返回整数计数，这里统一转为 bool 供 AssertionEngine 使用。
        return bool(self._raw().exists(key))

    def get(self, key: str) -> Any:
        """读取 String Key；不存在时返回 ``None``。"""
        # 业务 Key 和 expected 都由 YAML 提供，Client 只执行 GET。
        return self._raw().get(key)

    def hexists(self, key: str, field: str) -> bool:
        """判断 Hash field 是否存在。"""
        # field 可能是 token/session id，调用层错误信息需要注意脱敏。
        return bool(self._raw().hexists(key, field))

    def ttl(self, key: str) -> int:
        """返回 Key 剩余 TTL 秒数，语义与 Redis TTL 命令一致。"""
        # -1/-2 等特殊值保持 Redis 原语义，由 YAML 区间断言判断是否符合预期。
        return int(self._raw().ttl(key))

    def scard(self, key: str) -> int:
        """返回 Set 成员数量。"""
        # 通用 Set cardinality 可用于 UV、在线用户、标签集合等多种项目场景。
        return int(self._raw().scard(key))
