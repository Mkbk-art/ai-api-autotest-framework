"""通用 Java HashMod 分片键计算工具。

当前真实 SUT 使用 ShardingSphere ``HASH_MOD``，因此框架工具层提供可复用的 Java
``String.hashCode`` / HashMod 计算函数。函数本身不包含任何具体表名、Key 前缀或业务字段，
其他 Java 项目若采用相同分片算法也可以直接复用。
"""
from __future__ import annotations


def java_string_hashcode(value: str) -> int:
    """精确复刻 Java ``String.hashCode()`` 的 32 位有符号结果。"""
    # Java String.hashCode 只接受字符串；其他类型显式拒绝，避免 Python 隐式转换改变路由结果。
    if not isinstance(value, str):
        raise TypeError(f"Java hash value must be str, actual={type(value).__name__}")
    # Java String 基于 UTF-16 code unit 计算；Python Unicode code point 不能直接替代。
    result = 0
    # big-endian 只用于稳定拆分 16 位 code unit，不影响 Java 数学语义。
    encoded = value.encode("utf-16-be")
    # 每两个字节对应一个 Java char。
    for index in range(0, len(encoded), 2):
        # 读取当前 UTF-16 code unit。
        code_unit = int.from_bytes(encoded[index : index + 2], "big")
        # Java int 每一步都保留 32 位溢出语义。
        result = (31 * result + code_unit) & 0xFFFFFFFF
    # Python int 无符号溢出，需要手工恢复 Java int 的负数区间。
    if result & 0x80000000:
        result -= 0x100000000
    # 返回与 Java String.hashCode() 一致的有符号整数。
    return result


def java_hash_mod(value: str, shard_count: int) -> int:
    """按常见 ShardingSphere HASH_MOD 语义计算 ``0..shard_count-1`` 后缀。"""
    # 分片数量必须为正，否则取模本身没有合法语义。
    if int(shard_count) <= 0:
        raise ValueError("shard_count must be positive")
    # 工具只返回数字后缀，不知道调用项目最终使用什么表名前缀。
    return abs(java_string_hashcode(value)) % int(shard_count)
