# Stage 5 V3.0 完整离线验证证据

## 1. 版本范围

本证据对应“Stage 4.5 Sentinel 小修复 + Stage 5 MySQL/Redis 深层校验”的一次性交付版本。
真实 SaaS / MySQL / Redis 只有用户 Windows 本机运行后才能标记真实通过；本文件只记录代码、
算法、collection、Mock/框架回归和交付包一致性验证。

## 2. Stage 4.5 真实失败根因纳入本版本

用户 V2.11 `--level core` 最近一次真实结果：

```text
5 passed, 1 failed, 6 deselected
```

唯一失败的 E6 在 `create_shortlink_from_yaml()` 前置 Create 即得到 HTTP 200 + `B100000`，
未进入 recycle save / redirect / remove。对照 Java Sentinel 配置确认 Create QPS=1。
V3.0 只对“测试数据准备型 Create”处理已知 `B100000` 有界重试；正常 Create Smoke 不重试。

## 3. 登录信息 YAML 化

`config/env.shortlink-local.yaml` 现在统一提供：

```text
shortlink.username/password/create_retry
mysql.host/port/database/username/password/charset
redis.host/port/db/password
```

真实登录 YAML 使用 `${config(shortlink,username)}` / `${config(shortlink,password)}`；fixture
读取同一份 `runtime_config`。短链接真实测试不再要求终端导出登录变量。

本地 MySQL/Redis 纯数字密码也可直接写成 YAML 数值；配置解析会转为字符串，并通过
`repr=False` 避免连接配置对象直接展示密码。

## 4. Stage 5 功能范围

固定 6 条 Regression：

```text
MySQL 3
- Create -> t_link_x / t_link_goto_x 物理分片
- recycle save/remove -> enable_status/del_flag/del_time 状态迁移
- Redirect/Stats -> t_link_access_stats 最终落库

Redis 3
- Login Hash token field + TTL
- Create goto cache + recycle save 删除
- Redirect UV/UIP 去重 Set
```

MySQL/Redis Probe 只读；业务状态变化继续由真实 API 触发。

## 5. Java 源码与真实日志契约核对

Stage 5 实现已对照用户提供的 Java 项目源码：

```text
t_link      : shardingColumn=gid, HASH_MOD, sharding-count=16
t_link_goto : shardingColumn=full_short_url, HASH_MOD, sharding-count=16
```

Redis Key 也与 `RedisCacheConstant` / `RedisKeyConstant` 保持一致。真实 SQL 日志样例：

```text
0Ly9iC -> t_link_6
onkw7W -> t_link_5
tSUBMP -> t_link_1
nurl.ink:8001/2rHMXI -> t_link_goto_11
```

均可被 Python 的 Java `String.hashCode()` + HASH_MOD 实现复现。

## 6. TDD 与定向回归

本版本保留 Stage 5 的 config DSL、Sentinel 重试、Infrastructure Probe、Regression collection
单元/集成测试；最终又补充“YAML 纯数字 MySQL/Redis 密码”测试，先得到 RED，再修改解析逻辑转为 GREEN。

## 7. 最终工作树完整验证

框架测试：

```text
117 passed in 27.33s
```

默认离线全量：

```text
123 passed in 25.87s
```

当前 Linux 沙箱自动注入第三方 `ddtrace` pytest 插件；完整测试中嵌套启动子 Pytest 时出现过
一次外部插件导致的间歇性等待。使用 `PYTEST_ADDOPTS='-p no:ddtrace'` 排除该沙箱外部插件后，
项目完整命令稳定为 123 passed。项目 requirements 不包含 ddtrace，用户 Windows 环境无需添加该参数。

真实 shortlink collection：

```text
Smoke      6/18 selected
Core       6/18 selected
Regression 6/18 selected
```

编译与扫描：

```text
python -m compileall -q core utils testcases tests -> PASS
旧 ${env(SHORTLINK_TEST_...)} 运行时 DSL -> 0
运行时固定 GitHub / DEFAULT_ORIGIN_URL -> 0
已知真实登录值扫描 -> 0
Python/YAML 高密度中文注释守护 -> 2 passed
```

## 8. 沙箱依赖安装限制

交付包已经在 `requirements.txt` 声明 `PyMySQL>=1.1` 与 `redis>=5.0`。当前沙箱无法解析外网
PyPI 域名，因此无法在这里下载新增第三方驱动；连接工厂采用 lazy import，Stage 1~4 的离线
回归不依赖它们。用户本机需执行：

```bash
python -m pip install -r requirements-dev.txt -c constraints.txt
```

然后再运行真实 Stage 5 Regression。

## 9. 真实验收边界

V3.0 发布时：

```text
Stage 4 Smoke       已真实 6/6
Stage 4.5 Core      最近真实 5/6；Sentinel 修复后待复验
Stage 5 Regression 编码/离线验证完成；真实 MySQL/Redis 待用户本机 6/6
```

只有用户本机完成 Core 与 Regression 后，计划书才能把 Stage 4.5/5 升级为真实环境完成。
