# 声明式 Case 与 Python Workflow 边界

## 1. 为什么需要这个边界

YAML 的目标不是把 Python 参数换一个文件保存，而是减少普通 API 自动化中的重复执行代码。

如果一条测试既需要完整 YAML，又要再写一个只负责 `parametrize + ApiRunner.run()` 的 `test_xx.py`，说明执行模型没有真正做到声明式驱动。

因此当前规则是：

> **普通场景只写 YAML；真正存在程序控制流的场景才写 Python Workflow。**

## 2. YAML-only Case

满足以下条件时优先使用声明式 Case：

1. 有一个主要 API Operation；
2. method/path/header/query/body 可以声明；
3. 前置可以由已有 Context Provider 提供；
4. 响应变量可以通过 extract 获取；
5. 验证可以由统一 AssertionEngine 表达；
6. 可以包含 MySQL/Redis 只读校验；
7. 可以包含通用有界 polling；
8. 没有业务分支、循环和复杂状态补偿。

常见例子：

```text
登录成功/失败
权限不足
参数为空/非法
CRUD
查询不存在资源
创建后数据库存在
Redis TTL
异步状态最终到达预期
```

## 3. Context Provider 不是 Workflow

一条 Page Case 需要“先有一个已创建资源”，不代表 Page 测试本身是复杂流程。

它仍然可以写：

```yaml
requires:
  - project.created_resource
```

Provider 负责准备和 cleanup；Page Case 仍然只描述 Page API 的输入和预期。

## 4. Python Workflow

出现以下任一情况时使用 Python：

- 多个 API 状态迁移构成测试主体；
- if/else；
- 循环；
- 复杂等待策略；
- 异常补偿；
- 多资源事务生命周期；
- 不同中间状态需要不同 cleanup；
- 失败后必须基于到达状态选择恢复路径。

Python 负责“步骤怎么走”，YAML 仍负责“原子 API/断言是什么”。

## 5. Shortlink 当前验证样本

18 条 Case 中：

```text
16 Declarative
2 Workflow
```

保留的两条 Workflow 都属于回收存储生命周期：

```text
Create
↓
观察 Create 状态
↓
Recycle Save
↓
观察 MySQL/Redis 中间状态
↓
Recycle Remove
↓
观察最终状态
↓
异常路径 cleanup
```

这只是第一个真实 SUT 的结果，不是框架规定“任何项目必须 16:2”。

## 6. DSL 防膨胀原则

V2 YAML 明确拒绝：

```text
if
else
for
while
try
finally
```

如果未来一个需求必须靠这些控制流才能表达，应进入 Python Workflow，而不是继续扩展 YAML 语法。
