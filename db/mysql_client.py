"""通用 MySQL 只读客户端。

Stage 5 的目标不是为某个业务系统编写 ORM，而是给统一断言引擎提供可复用的数据查询
能力。连接信息从 ``data_sources.mysql.<source>`` YAML 节点读取；业务表名和查询条件
完全由测试 YAML 声明。为避免测试代码绕过真实 API 修改被测系统，本客户端只允许
``SELECT`` / ``WITH`` 查询。
"""
from __future__ import annotations

# dataclass 用于把命名数据源配置封装为不可变对象；password 使用 repr=False 避免调试输出泄露。
from dataclasses import dataclass, field
# Mapping/Sequence 让客户端兼容普通 dict、ConfigManager 输出和参数化 SQL 列表。
from typing import Any, Callable, Mapping, Sequence


# Connector 是可注入的数据库连接工厂；单元测试用 Fake Connector，因此不需要真实 MySQL。
Connector = Callable[..., Any]


def _secret_text(value: Any, *, path: str, allow_none: bool = False) -> str | None:
    """把 YAML 中的密码标量规范化为字符串，同时避免 bool 被当作整数密码。"""
    # Redis 等数据源允许 password: null；MySQL 默认仍要求明确配置。
    if value is None and allow_none:
        return None
    # Python 中 bool 是 int 子类，因此必须先排除，避免 True 被误当成密码 "True"。
    if isinstance(value, bool) or value is None:
        raise RuntimeError(f"Required runtime config {path} is not configured")
    # YAML 未加引号的纯数字密码会被解析成 int；驱动层统一转换为字符串。
    if isinstance(value, int):
        return str(value)
    # 字符串需要拒绝空白和交付包占位符，防止连接时报更模糊的认证错误。
    if isinstance(value, str) and value.strip() and value.strip() != "CHANGE_ME":
        return value.strip()
    # 错误信息只包含配置路径，不回显密码原值。
    raise RuntimeError(f"Required runtime config {path} is not configured")


def _required_text(values: Mapping[str, Any], key: str, *, path: str) -> str:
    """读取普通必填文本配置并拒绝空值/占位符。"""
    # host/database/username 等普通文本字段统一使用同一验证规则。
    value = values.get(key)
    # 去除前后空格后返回，避免环境 YAML 的无意空格进入连接参数。
    if isinstance(value, str) and value.strip() and value.strip() != "CHANGE_ME":
        return value.strip()
    # 明确告诉用户缺失的是哪个命名数据源字段。
    raise RuntimeError(f"Required runtime config {path}.{key} is not configured")


def _source_mapping(runtime_config: Mapping[str, Any], kind: str, source: str) -> Mapping[str, Any]:
    """读取 ``data_sources.<kind>.<source>``，错误时给出明确 YAML 路径。"""
    # 第一级固定使用 data_sources，使数据库/缓存连接与具体项目配置解耦。
    data_sources = runtime_config.get("data_sources")
    # 没有 data_sources 说明当前环境根本没有配置数据源能力。
    if not isinstance(data_sources, Mapping):
        raise RuntimeError("Required runtime config data_sources is not configured")
    # kind 当前可为 mysql/redis；函数本身不写业务项目名称。
    kind_values = data_sources.get(kind)
    # 对应类型没有配置时给出层级化错误。
    if not isinstance(kind_values, Mapping):
        raise RuntimeError(f"Required runtime config data_sources.{kind} is not configured")
    # source 允许 default/reporting/readonly 等任意命名连接。
    source_values = kind_values.get(source)
    # source 不存在时不能回退到其他连接，避免测试误查错误数据库。
    if not isinstance(source_values, Mapping):
        raise RuntimeError(
            f"Required runtime config data_sources.{kind}.{source} is not configured"
        )
    # 返回只读 Mapping 给 Settings 解析。
    return source_values


@dataclass(frozen=True)
class MySQLSettings:
    """一个命名 MySQL 数据源的不可变连接配置。"""

    # 连接主机。
    host: str
    # TCP 端口。
    port: int
    # 默认数据库名。
    database: str
    # 数据库用户名。
    username: str
    # 密码不参与 repr，降低 fixture/异常对象打印时的泄露风险。
    password: str = field(repr=False)
    # 默认使用 utf8mb4，兼容常见业务文本。
    charset: str = "utf8mb4"
    # 连接超时只控制建立连接，不等同于 SQL 执行超时。
    connect_timeout: int = 5

    @classmethod
    def from_runtime_config(
        cls,
        runtime_config: Mapping[str, Any],
        *,
        source: str = "default",
    ) -> "MySQLSettings":
        """从通用环境 YAML 的命名 MySQL 数据源创建设置对象。"""
        # 先定位 data_sources.mysql.<source> 节点。
        values = _source_mapping(runtime_config, "mysql", source)
        # path 只用于错误提示，不包含任何真实凭据值。
        path = f"data_sources.mysql.{source}"
        # 所有字段在一个地方完成类型规范化，MySQLClient 后面只消费干净 Settings。
        return cls(
            host=_required_text(values, "host", path=path),
            port=int(values.get("port", 3306)),
            database=_required_text(values, "database", path=path),
            username=_required_text(values, "username", path=path),
            password=str(_secret_text(values.get("password"), path=f"{path}.password")),
            charset=str(values.get("charset", "utf8mb4")),
            connect_timeout=int(values.get("connect_timeout", 5)),
        )


class MySQLClient:
    """为 YAML 数据库断言提供通用、只读、参数化的 MySQL 查询接口。"""

    def __init__(self, settings: MySQLSettings, connector: Connector | None = None) -> None:
        """保存数据源设置；真实驱动仅在真正执行查询时懒加载。"""
        # Settings 已经完成配置验证；Client 不再读取业务环境节点。
        self.settings = settings
        # connector 允许单元测试注入 Fake，也允许未来按需适配兼容驱动。
        self._connector = connector

    @classmethod
    def from_runtime_config(
        cls,
        runtime_config: Mapping[str, Any],
        *,
        source: str = "default",
        connector: Connector | None = None,
    ) -> "MySQLClient":
        """从命名数据源直接创建客户端，便于断言引擎按 source 懒加载。"""
        # AssertionEngine 只需要传 runtime_config + source，不关心具体连接字段。
        return cls(
            MySQLSettings.from_runtime_config(runtime_config, source=source),
            connector=connector,
        )

    @staticmethod
    def _ensure_read_only(sql: str) -> None:
        """只允许 SELECT/WITH，防止测试 YAML 直接写业务数据库。"""
        # 忽略前导空白并统一小写后检查 SQL 起始关键字。
        normalized = str(sql).lstrip().lower()
        # INSERT/UPDATE/DELETE/DDL 都在建立连接之前被拒绝。
        if not (normalized.startswith("select") or normalized.startswith("with")):
            raise ValueError("MySQLClient only allows read-only SELECT/WITH SQL")

    def _connect(self):
        """建立一次短生命周期连接；没有注入 connector 时懒加载 PyMySQL。"""
        # 单元测试优先使用注入 connector，不要求本机安装/启动 MySQL。
        if self._connector is not None:
            return self._connector(
                host=self.settings.host,
                port=self.settings.port,
                user=self.settings.username,
                password=self.settings.password,
                database=self.settings.database,
                charset=self.settings.charset,
                connect_timeout=self.settings.connect_timeout,
            )

        # 只有真正触发 db_* YAML 断言时才导入 PyMySQL，Smoke/Core 不会无意义连接数据库。
        try:
            import pymysql
        except ImportError as exc:
            # 依赖缺失给出可操作错误，而不是模糊 ModuleNotFoundError。
            raise RuntimeError(
                "PyMySQL is required for MySQL YAML assertions; install project dependencies"
            ) from exc

        # 每次断言创建短连接，查询完成立即关闭，避免测试套件长期占用连接。
        return pymysql.connect(
            host=self.settings.host,
            port=self.settings.port,
            user=self.settings.username,
            password=self.settings.password,
            database=self.settings.database,
            charset=self.settings.charset,
            connect_timeout=self.settings.connect_timeout,
            # DictCursor 让 fetch_one 结果更适合项目级调试；fetch_scalar 同样兼容 tuple/list。
            cursorclass=pymysql.cursors.DictCursor,
            # 只读 SELECT 不需要显式事务提交。
            autocommit=True,
        )

    def fetch_one(self, sql: str, params: Sequence[Any] | None = None) -> Any:
        """执行只读查询并返回第一行；无记录时返回 ``None``。"""
        # 在任何连接动作前验证只读约束，防止恶意/误写 SQL 到达数据库。
        self._ensure_read_only(sql)
        # 连接只在本次查询生命周期中存在。
        connection = self._connect()
        try:
            # 参数必须通过 execute 的 params 传入，不在客户端层字符串拼接业务值。
            with connection.cursor() as cursor:
                cursor.execute(sql, tuple(params or ()))
                return cursor.fetchone()
        finally:
            # 即使 execute/fetch 抛异常也必须关闭连接。
            connection.close()

    def fetch_scalar(self, sql: str, params: Sequence[Any] | None = None) -> Any:
        """返回第一行第一列，适合 ``db_eq``/``db_gte`` 这类 YAML 断言。"""
        # 复用 fetch_one 的只读检查、参数绑定和连接释放逻辑。
        row = self.fetch_one(sql, params)
        # 无记录明确返回 None，由 AssertionEngine 决定 eq/gte 是否失败。
        if row is None:
            return None
        # DictCursor 返回 Mapping，第一列就是第一个 value。
        if isinstance(row, Mapping):
            return next(iter(row.values()), None)
        # Fake Driver 或其他兼容 connector 可能返回 tuple/list。
        if isinstance(row, (list, tuple)):
            return row[0] if row else None
        # 标量 Fake 结果直接返回，方便单元测试注入。
        return row
