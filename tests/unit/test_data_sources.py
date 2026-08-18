"""通用 MySQL/Redis 数据源客户端的离线单元测试。"""
from __future__ import annotations

import pytest


def test_mysql_client_reads_named_yaml_source_and_accepts_numeric_password():
    """MySQL 连接必须来自通用 data_sources YAML，而不是短链接专用配置。"""
    from db.mysql_client import MySQLClient

    client = MySQLClient.from_runtime_config(
        {
            "data_sources": {
                "mysql": {
                    "default": {
                        "host": "127.0.0.1",
                        "port": 3306,
                        "database": "demo",
                        "username": "root",
                        "password": 123456,
                    }
                }
            }
        }
    )

    assert client.settings.database == "demo"
    assert client.settings.password == "123456"
    assert "123456" not in repr(client.settings)


def test_mysql_client_rejects_mutating_sql_before_opening_connection():
    """框架数据断言只读数据库，YAML 不能借 DB Client 绕过业务 API 写数据。"""
    from db.mysql_client import MySQLClient, MySQLSettings

    client = MySQLClient(
        MySQLSettings("127.0.0.1", 3306, "demo", "root", "secret"),
        connector=lambda **_: (_ for _ in ()).throw(AssertionError("connector must not run")),
    )

    with pytest.raises(ValueError, match="SELECT"):
        client.fetch_one("UPDATE t_demo SET value=1")


def test_mysql_client_fetch_scalar_uses_bound_params():
    """业务值必须作为参数绑定；通用 Client 不拼接具体项目数据。"""
    from db.mysql_client import MySQLClient, MySQLSettings

    executed = []

    class Cursor:
        def execute(self, sql, params):
            executed.append((sql, params))

        def fetchone(self):
            return {"value": 7}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            return None

    client = MySQLClient(
        MySQLSettings("127.0.0.1", 3306, "demo", "root", "secret"),
        connector=lambda **_: Connection(),
    )

    assert client.fetch_scalar("SELECT value FROM t_demo WHERE id=%s", [9]) == 7
    assert executed == [("SELECT value FROM t_demo WHERE id=%s", (9,))]


def test_redis_client_uses_named_source_and_exposes_generic_read_operations():
    """Redis Client 只提供通用 key/hash/set 查询，不知道短链接 Key 规则。"""
    from db.redis_client import RedisClient

    calls = []

    class RawRedis:
        def exists(self, key):
            calls.append(("exists", key))
            return 1

        def get(self, key):
            return "value-1"

        def hexists(self, key, field):
            return key == "login" and field == "token"

        def ttl(self, key):
            return 600

        def scard(self, key):
            return 2

    client = RedisClient.from_runtime_config(
        {
            "data_sources": {
                "redis": {
                    "default": {
                        "host": "127.0.0.1",
                        "port": 6379,
                        "db": 0,
                        "password": None,
                    }
                }
            }
        },
        factory=lambda **_: RawRedis(),
    )

    assert client.exists("demo") is True
    assert client.get("demo") == "value-1"
    assert client.hexists("login", "token") is True
    assert client.ttl("login") == 600
    assert client.scard("uv") == 2
    assert calls == [("exists", "demo")]



def test_redis_client_defaults_to_resp2_and_allows_yaml_protocol_override():
    """Redis 协议必须显式可配置，避免客户端主版本升级偷偷改变线协议。"""
    from db.redis_client import RedisClient

    captured = []

    class RawRedis:
        def exists(self, key):
            return 1

    def factory(**kwargs):
        captured.append(kwargs)
        return RawRedis()

    base = {
        "data_sources": {
            "redis": {
                "default": {
                    "host": "127.0.0.1",
                    "port": 6379,
                    "db": 0,
                    "password": None,
                },
                "resp3": {
                    "host": "127.0.0.1",
                    "port": 6379,
                    "db": 0,
                    "password": None,
                    "protocol": 3,
                },
            }
        }
    }

    default_client = RedisClient.from_runtime_config(base, source="default", factory=factory)
    assert default_client.exists("demo") is True
    assert captured[-1]["protocol"] == 2

    resp3_client = RedisClient.from_runtime_config(base, source="resp3", factory=factory)
    assert resp3_client.exists("demo") is True
    assert captured[-1]["protocol"] == 3

def test_generic_java_hash_mod_matches_real_java_routing_examples():
    """HashMod 工具可被任意 Java/ShardingSphere 项目复用，不绑定具体表名前缀。"""
    from utils.sharding import java_hash_mod

    assert java_hash_mod("0Ly9iC", 16) == 6
    assert java_hash_mod("onkw7W", 16) == 5
    assert java_hash_mod("tSUBMP", 16) == 1
    assert java_hash_mod("nurl.ink:8001/2rHMXI", 16) == 11
