# AI 辅助接口自动化测试框架项目计划书

> **版本**：V3.2.6
> **更新日期**：2026-08-18
> **当前阶段**：项目定位严格保持“AI 辅助接口自动化测试框架”。Stage 4/4.5/5 已完成真实 SUT 验收；GitHub Actions 已真实绿色，Jenkins Build #10 已完成 `env=test + smoke` 的 2/2 Mock 主链、JUnit 与 Artifacts。V3.2.6 新增框架通用外部环境 YAML 覆盖能力；真实 SUT Jenkins smoke 待最终执行。
> **文档用途**：记录项目背景、仓库核查结论、技术路线、阶段任务、验收标准、风险约束和后续交付物，作为后续开发、AI 协作、项目移交、简历整理和面试准备的统一依据。

---

## 0. 本次版本更新说明

本版本在原计划书基础上，根据对以下仓库的联网源码核查结果进行重构：

```text
https://github.com/zed123214/api-autotest-framework
```

核查基于仓库 `main` 分支及当前最新提交：

```text
commit: e0ac76720265609d63249fed630016821659b679
日期：2026-05-12
```

本次更新不改变已经确认的项目方向，但对实施顺序和验收方式进行重要校正。

### 0.1 保留不变的内容

- 项目名称：AI 辅助接口自动化测试框架
- 求职方向：测试开发
- 基线仓库：`zed123214/api-autotest-framework`
- 真实被测系统：用户已有短链接 SaaS
- 技术主线：Pytest + Requests + YAML + Allure + MySQL / Redis + CI/CD + AI
- 暂不建设完整测试平台前端
- 暂不混入 Selenium / POM / UI 自动化
- AI 功能先做轻量、真实、可演示版本

### 0.2 本次新增或调整的内容

1. 增加基线仓库静态审查结论。
2. 将“直接跑通项目”调整为“先审查、修复 P0、再跑通”。
3. 增加 YAML 路径、JSON 请求、请求头覆盖、依赖顺序等阻断问题。
4. 明确 MySQL、Redis、数据库断言目前均为 Demo，不能写成已实现能力。
5. 增加配置未生效、HTTPS 校验关闭、重试未实现、上下文并发污染等风险。
6. 增加框架自身单元测试和受控 Mock 服务验证阶段。
7. 增加“计划能力”和“已验证能力”双状态管理。
8. 调整 8 周排期和 P0 / P1 / P2 优先级。
9. 增加开源许可证和二次开发归属说明。
10. 明确任何简历能力必须先通过代码、测试、报告或 CI 证据验证。

### 0.3 V2.2 本次推进结果

本版本在阶段 1 稳定基线之上完成阶段 2 核心加固：

1. 将共享 `extract.yaml` 运行时状态迁移为内存 `VariableContext`；
2. 支持 `session / scenario / case` 三层变量作用域及实例隔离；
3. 保持 `${get_extract_data(name)}` 兼容，并新增 `${name}` 直接变量替换；
4. 完善统一断言引擎，兼容旧 DSL 并新增状态码、存在性、集合、数值、响应头和耗时断言；
5. 未实现的数据库 / Redis 断言改为明确失败，避免“假校验”；
6. 增加非 JSON、真实超时、连接失败和 Allure Header 脱敏回归测试；
7. 修复 Runner 对 Allure 插件存在/不存在环境的兼容性测试；
8. 框架自身测试由 31 条增加到 50 条，全量测试由 37 条增加到 56 条；
9. 当前核心目录测试覆盖率为 78%；
10. `smoke / core / regression` 继续保持独立执行，每层均为 2 passed / 4 deselected。

### 0.4 V2.3 本次推进结果

本版本完成阶段 3 正式架构重构，并同步纠正计划书中所有与实际代码不一致的阶段状态：

1. 将上游遗留的 `base/ + common/ + testcase/` 正式迁移为 `core/ + utils/ + testcases/`；
2. 将 `RequestBase` 的实现类重命名为职责更明确的 `ApiRunner`；
3. `core/` 集中配置、用例加载、HTTP 请求、上下文、提取、断言与用例编排；
4. `utils/` 集中 DebugTalk、日志、脱敏、JsonPath、路径和 Allure 兼容层；
5. `testcases/demo/` 明确标记为 Mock 演示用例，不冒充真实短链接业务；
6. 删除旧 `base/`、`common/`、`testcase/` 正式源码入口和无用 `YamlContext` 运行态兼容对象；
7. 新增 `THIRD_PARTY_NOTICES.md`、`.env.example`、`pyproject.toml`、`requirements-dev.txt` 和 `constraints.txt`；
8. 所有 Python 模块均补充模块顶部用途说明，框架公共类/函数和 fixture 补充 docstring；
9. 新增 Stage 3 架构与代码说明规范自动化测试；
10. 框架自身测试由 50 条增加到 57 条，全量测试由 56 条增加到 63 条；
11. Stage 3 核心源码覆盖率为 79%；
12. `collect-only` 仍准确收集 6 条 Demo 业务用例，`smoke/core/regression` 均保持 2 passed / 4 deselected；
13. Stage 3 完成后，项目下一步正式切换到阶段 4：读取并接入真实短链接 SaaS 的启动方式和 API 契约。

### 0.5 V2.4 本次推进结果

本版本开始执行阶段 4，并根据真实短链接 SaaS 源码和本地运行证据实时修正原阶段计划：

1. 已读取并梳理真实短链接 SaaS 多模块源码，确认系统由 Gateway、Admin、Project、Aggregation、Nacos、MySQL、Redis、ShardingSphere 等组件构成；
2. 已确认真实登录接口、Header 鉴权、分组查询、短链接创建、分页查询、短链跳转、统计查询和回收站清理等核心契约；
3. 第一条真实 E2E 链路由原“登录 -> 创建 -> 查询 -> 跳转 -> 统计”修正为“登录 -> 查询分组 gid -> 创建 -> 查询确认 -> 跳转 -> 轮询统计 -> 清理”；
4. 已确认访问统计通过 Redis Stream 异步消费后落库，统计自动化必须使用轮询等待最终一致性，不能访问后立即断言；
5. 已确认用户/分组/短链接等核心表使用 ShardingSphere 分片，Stage 5 直接 MySQL 校验需要基于真实物理表或分片算法设计，不能简单查询逻辑表；
6. 已通过浏览器 Network 和手工请求定位首个真实业务缺陷：旧 Nginx 前端构建包调用 `/stats` 时遗漏 `enableStatus`，导致后端返回 `data:null`；手工补充 `enableStatus=0` 后成功获得 PV/UV/UIP、浏览器、OS、设备和网络统计；
7. 已确认当前 Vue 源码已经包含 `enableStatus`，但 Nginx 部署的是旧构建包，属于“源码与部署版本不一致”问题；
8. 已额外发现并修正前端 `networkStats` 使用 `item.device` 而非后端真实字段 `item.network` 的字段契约错误；
9. 已生成修正后的 Nginx `dist-link`、完整 Nginx 包和同步修正的 Vue 源码包，并对最终 ZIP 解压后的静态 JS 语法和关键参数传递进行验证；
10. 当前尚未把真实 SaaS 接入自动化框架，因此“真实业务自动化”仍为进行中能力，不提前标记为已实现。

### 0.6 V2.5 本次推进结果

本版本把 Stage 4 从“契约分析”推进到第一批真实业务自动化代码，并保持能力状态与验证证据分离：

1. 新增 `config/env.shortlink-local.yaml`，真实本地环境固定通过 Gateway `http://127.0.0.1:8000`，且 `use_mock: false`；
2. 在 Pytest collection 阶段隔离 `testcases/demo/` 与 `testcases/shortlink/`：Mock 环境不收集真实用例，真实环境不收集 Demo，避免请求打错目标；
3. `DebugTalk` 新增 `${env(NAME)}` 必需环境变量读取能力，真实测试用户名/密码不写入 YAML、源码和 Git；
4. 新增真实登录 `test_auth.py + auth.yaml`，按源码契约调用 `/api/short-link/admin/v1/user/login`，断言 HTTP 200、业务码 `"0"` 并提取 `token`；
5. 新增真实分组 `test_group.py + group.yaml`，独立 fixture 先完成登录，再发送 Gateway 所需 `username + token` Header，提取首个 `gid`；
6. 登录前置逻辑封装到 `testcases/shortlink/support.py`，不依赖其他测试函数执行顺序，并有离线单元测试保护真实请求路径、JSON 契约和 VariableContext 写入；
7. `shortlink-local` collect-only 已验证只收集 Auth + Group 2 条真实业务用例；`test` 环境仍只收集 Stage 3 的 6 条 Demo；
8. Stage 4 首批代码加入后，沙箱框架自身测试已验证 64 passed、离线全量回归已验证 70 passed；该证据只证明框架/契约代码未破坏，不等价于用户本地真实 SaaS 网络调用已通过；
9. 用户已确认后端系统和 Nacos 可正常启动，并已提供专用测试账号；凭据只在本地通过 `SHORTLINK_TEST_USERNAME/SHORTLINK_TEST_PASSWORD` 注入；
10. 下一验收点是用户 Windows + Python 3.11 执行 `python run.py --env shortlink-local --level smoke`；成功后才把 Auth/Group 标记为“真实环境已验证”，随后继续创建短链链路。

### 0.7 V2.6 本次推进结果

本版本继续推进 Stage 4 第二批真实业务自动化，并根据用户首次真实运行结果修正状态：

1. 用户 Windows 环境已真实执行 `python run.py --env shortlink-local --level smoke`，Python Requests 成功到达 Gateway `:8000` 登录接口并收到 HTTP 200，证明 Runner -> Gateway 网络和路由链真实连通；
2. 该次登录业务失败的直接原因是 Shell 中密码环境变量值被误写，后端返回非零业务码；框架正确执行了业务码和 token 断言，没有把 HTTP 200 误判为成功，因此“正确凭据登录成功”仍待复验；
3. 修复 `shortlink_credentials` 使用普通 dict 导致 Pytest fixture setup 失败时可能打印密码的问题：新增 `ShortlinkCredentials`，password 字段 `repr=False`；鉴权 fixture 也不再把 token 放进返回值；
4. 新增真实创建 `test_create.py + create.yaml`，fixture 独立完成登录和 Group/gid 前置，调用 `/api/short-link/admin/v1/create` 创建永久短链；
5. 创建结果统一保存 `short_url`（带 scheme）、`full_short_url`（不带 scheme）和 `short_uri`，解决 Java create 响应与 Page/Stats/数据库标识语义不同的问题；
6. 新增 `shortlink_created_context` fixture，为后续 Page/Redirect/Stats 在同一测试 function scope 内独立准备“登录 -> gid -> 创建短链”，继续保持测试文件顺序独立；
7. 新增真实分页 `test_page.py + page.yaml`，按 gid 分页后在 `records` 中精确匹配当前测试刚创建的 `fullShortUrl`，并验证 gid、originUrl 和 `enableStatus=0`；
8. `shortlink-local --collect-only` 现在稳定收集 4 条真实业务用例：Auth、Group、Create、Page；Stage 3 Mock 环境仍只收集原 6 条 Demo；
9. Stage 4 第二批加入后，沙箱框架自身测试已验证 70 passed，默认离线全量回归 76 passed；Mock smoke/core/regression 仍分别为 2 passed / 4 deselected；
10. 当前下一验收点为用户使用正确 OS 环境变量执行四条真实 smoke；成功后再进入 302 Host Header、Redis Stream 统计轮询和回收站清理。

### 0.8 V2.7 本次推进结果

本版本根据用户真实 `4 passed` 证据、Windows hosts 配置和代码注释要求继续推进 Stage 4：

1. 用户修正 OS 环境变量后，已在 Windows 真实短链接系统中验证 Auth + Group + Create + Page 四条 smoke 为 `4 passed`，因此四项正式标记为“真实环境已验证”；
2. 创建案例和 fixture 创建数据统一固定 `originUrl=https://github.com/`，唯一性继续由 `api-autotest-<timestamp>` 描述字段保证；
3. 凭据安全继续加固：`ShortlinkCredentials.password` 使用 `repr=False`，`authenticate_shortlink()` 只接收凭据对象而不暴露独立 password 形参，降低 Pytest fixture/helper traceback 泄密风险；
4. 用户 Windows hosts 已确认存在 `127.0.0.1 nurl.ink`，因此 Redirect 不再采用 `127.0.0.1:8001 + Host Header` 绕过方案，而是直接请求 `http://nurl.ink:8001/<short_uri>`；虽然 TCP 最终仍到 `127.0.0.1:8001`，HTTP Host/serverName 保持 `nurl.ink`，可与数据库 `fullShortUrl` 逻辑身份一致；
5. Redirect 设置 `allow_redirects=False`，真实验收要求第一跳 HTTP 302 且 `Location=https://github.com/`；
6. 新增 Statistics 有界轮询：Redirect 后通过 Gateway/Admin `/stats` 携带 `fullShortUrl/gid/enableStatus=0/当天日期范围`，每 1 秒查询一次、最多 15 秒，成功条件为 `pv/uv/uip >= 1`；
7. 接入真实回收站清理：`shortlink_created_context` 使用 yield fixture，在测试 Teardown 阶段执行 `recycle-bin/save -> recycle-bin/remove`；Create 测试自身也使用 `finally` 清理，避免 smoke 反复运行残留大量 `api-autotest-*` 数据；
8. Stage 4 的 Python 业务文件和 YAML 用例全面补充高密度中文解释，并新增 `test_stage4_comment_quality.py` 自动守护模块 docstring 和最低注释密度，防止后续版本再次退化为“只有代码没有说明”；
9. `shortlink-local --collect-only` 当前应收集 6 条真实用例：Auth、Group、Create、Page、Redirect、Statistics；Cleanup 作为 fixture Teardown/业务 helper 自动执行，不额外增加测试顺序依赖；
10. 本版本沙箱验证：框架自身测试 `81 passed`，默认离线全量回归 `87 passed`；Redirect hosts 契约、Stats 即时/延迟/超时、Cleanup save/remove 顺序、GitHub Create URL、凭据 repr 与注释规范均有离线测试；
11. Redirect/Statistics/Cleanup 目前只标记“已编码并离线验证”，必须等待用户本机执行 6 条真实 smoke 后，才能把完整 Stage 4 E2E 标记为真实环境已通过。


### 0.9 V2.8 Redirect YAML 主链纠正

本版本根据用户对 Redirect 用例可读性和 YAML 驱动一致性的复核，对上一版“专用 helper 旁路请求”进行结构性纠正：

1. 删除 `request_shortlink_redirect()` 专用网络 helper，避免 Redirect 绕过 `ApiRunner.run()`；
2. `redirect.yaml` 现在真正声明完整 `http://nurl.ink:8001/${short_uri}`、GET、`request_options.allow_redirects=false` 和 302/Location 断言；
3. `ApiRunner` 新增绝对/相对 URL 统一解析：相对 `/api/...` 仍拼接当前环境 Gateway host，完整 `http://`/`https://` URL 直接访问目标服务；
4. URL 本身也进入动态变量替换，因此 fixture 写入 VariableContext 的 `short_uri` 可以直接驱动 YAML URL；
5. `ApiRunner` 新增受控 `request_options` 入口，当前只允许真实需要的 `allow_redirects`，防止任意 Requests 参数无约束透传；
6. `test_redirect.py` 现在唯一网络入口为 `request_base.run(base_info, test_case)`，形成真正的 `YAML -> ApiRunner -> RequestClient -> Requests -> Assertions` 主链；
7. Statistics 触发访问时也复用同一份 `redirect.yaml` + `ApiRunner.run()`，不再维护第二套 Redirect 实现；
8. 新增回归测试证明绝对 URL + `${short_uri}` + `allow_redirects=false` 可以完整透传，同时普通相对 URL 仍保持原有 Gateway 拼接行为；
9. 本版本沙箱验证更新为框架自身 `83 passed`、默认离线全量 `89 passed`、`shortlink-local --collect-only` 仍为 6 条；
10. 该重构只改变框架执行路径，不把 Redirect/Statistics/Cleanup 提前标记为真实通过，最终状态仍等待用户 Windows 本机 6 条 smoke 验收。

### 0.10 V2.9 Create 单一数据源纠正与真实环境证据更新

本版本根据用户真实运行日志修正 Stage 4 的测试数据配置重复问题，并保持“代码能力”和“真实验收状态”分离：

1. 用户已在 Windows 真实环境单独验证 Redirect，用例可以正常执行，因此 Redirect 主链正式标记为真实环境已验证；
2. 用户单独执行 Statistics 时，曾真实完成 Login -> Group -> Create -> Redirect 302，并调用 `/stats` 得到 HTTP 200，但业务码为 `B000001`，因此 Statistics 仍未通过；
3. 真实 Project 日志已证明 GitHub 作为 originUrl 时，`createShortLink()` 会同步调用 `getFavicon()`，Jsoup 外部连接偶发超时会拖累 Create，属于真实被测系统的外部依赖稳定性问题；
4. 进一步发现 `create.yaml` 的 `originUrl` 与 Python `DEFAULT_ORIGIN_URL` 重复维护，导致用户修改 YAML 后，Page/Redirect/Statistics fixture 仍可能继续使用 Python 写死的 GitHub；
5. 本版本删除固定 `DEFAULT_ORIGIN_URL`，新增 `create_shortlink_from_yaml()`，Page/Redirect/Statistics 的前置 Create 与 `test_create.py` 统一读取 `testcases/shortlink/yaml/create.yaml`；
6. `create.yaml` 成为 Stage 4 原始 URL 唯一配置源；当前按用户本地修改保留 `https://www.doubao.com/`，以后更换站点只需修改这一行；
7. `redirect.yaml` 的 Location 断言由固定 GitHub 改为 `${origin_url}`，该变量来自真实 Create 响应并写入 VariableContext，因此 Redirect 自动跟随本次创建的原始 URL；
8. `test_create.py` 不再断言固定 GitHub，而是从当前 YAML Case 读取 expected originUrl，避免 Python 再维护第二份期望；
9. 新增回归测试证明“前置 Create 读取 create.yaml”和“Redirect 使用 `${origin_url}`”两个单一数据源契约；
10. 本版本离线验证为框架自身 `83 passed`、默认全量 `89 passed`、compileall PASS、`shortlink-local --collect-only` 仍为 6 条；下一步重新真实验证 Statistics，并继续定位 `/stats` 的 `B000001`，不把该错误误归因于 originUrl 重复配置。

### 0.11 V2.10 Stage 4 完成与 Stage 4.5 第一批异常测试

本版本根据用户最新完整真实运行证据，正式关闭 Stage 4 Happy Path，并开始异常/边界测试：

1. 用户在 Windows 本机执行 `python run.py --env shortlink-local --level smoke`，六条真实业务用例最终为 `6 passed in 9.65s`；
2. Redirect 真实返回 HTTP 302，Statistics 在真实 Redis Stream 异步链路中先查询一次 `/stats`，约 1 秒后再次轮询并达到 PV/UV/UIP 条件，Cleanup 真实执行 `recycle-bin/save -> recycle-bin/remove`；
3. 因此 Stage 4 的 Login/Group/Create/Page/Redirect/Statistics/Cleanup 全部升级为“真实环境已验证”；
4. Stage 4.5 只补精选异常/边界，不扩张 Happy Path Smoke；第一批为“错误密码登录”和“Group 缺 token”；
5. 错误密码用例通过 `${invalid_password()}` 生成与真实密码完全解耦的动态错误值，验证 HTTP 200 但业务 code 非 0，并且不能产生 token；
6. Group 缺 token 用例不依赖登录 fixture，只发送 username，按 Gateway `TokenValidateGatewayFilterFactory` 契约验证 HTTP 401、`status=401` 和 `Token validation error`；
7. 两条异常用例继续统一走 `YAML -> ApiRunner -> RequestClient -> Assertions`，并使用 `core` marker，确保现有 6 条 Smoke 数量和语义不变；
8. Stage 4.5 第一批已完成 TDD 红绿验证、YAML 契约测试、ApiRunner 请求展开测试和注释质量守护；当前沙箱结果为 framework `92 passed`、默认离线全量 `98 passed`、Smoke collection `6/8`、Core collection `2/8`、compileall PASS；真实通过状态仍等待用户本机执行 `--level core`；
9. Stage 4 真实 6 passed 证据固化在 `docs/evidence/34_stage4_real_smoke_6_passed.md`；V2.10 离线验证固化在 `docs/evidence/35_stage45_v210_offline_verification.md`；
10. **从 V2.10 起的当前唯一执行路线**为：Stage 4.5 完成 6 条精选异常/边界 -> Stage 5 MySQL + Redis 深层一致性校验 -> Stage 6 CI/CD -> Stage 7 AI 辅助 -> Stage 8 README/简历/面试收尾。本文后部早期版本形成的阶段 5～9 详细能力池仅保留历史设计参考，若编号与本条冲突，以本条当前路线为准。

### 0.12 V2.11 Stage 4.5 六条异常/边界一次性交付

根据用户明确要求，本版本废弃“先交付 E1/E2、再分批交付 E3～E6”的中间交付方式，直接形成 Stage 4.5 完整候选版：

1. 保留 V2.10 已实现的 E1 错误密码登录与 E2 Group 缺 token；
2. 新增 E3 Create 缺 token，请求体保持合法，仅省略 token，验证 Gateway HTTP 401；
3. 新增 E4 Create 非法 originUrl，在真实登录/gid 前置下发送 `not-a-valid-url`，验证 HTTP 200 + 非零业务码，且不能返回 `fullShortUrl`；
4. 新增 E5 不存在 shortUri，使用随机短码直接访问 Project:8001，关闭自动重定向并验证第一跳 302 到 `/page/notfound`；
5. 新增 E6 回收后再次访问：通过 `create.yaml` 创建真实短链，真实调用 `recycle-bin/save` 进入回收站，再访问同一 shortUri 验证 notfound，最后在 `finally` 中调用 `recycle-bin/remove` 清理；
6. 断言引擎新增 `header_contains`，用于兼容 Servlet 对相对 `sendRedirect` 可能返回相对或绝对 Location 的差异；
7. `cleanup_shortlink()` 内部拆出 `save_shortlink_to_recycle_bin()` 与 `remove_shortlink_from_recycle_bin()`，常规 Happy Path 行为不变，E6 可以观察中间回收状态；
8. `pytest.ini` 注册 `negative/unauthorized/invalid_input/notfound/recycle` 业务 marker；
9. Collection 守护更新为真实 shortlink 总计 12 条，其中 Smoke 固定 6 条、Core 固定 6 条；新增 YAML loader 检查覆盖全部 12 个真实业务测试模块；
10. 六条异常全部继续经过 `YAML -> ApiRunner -> RequestClient -> Assertions` 主链，新改 Python/YAML 继续通过高密度中文注释质量守护；
11. 当前工作树离线结果为 framework `107 passed`、默认离线全量 `113 passed`、Smoke `6/12 selected`、Core `6/12 selected`、compileall PASS；这些只证明代码/契约/分层，不冒充真实 SaaS 结果。用户 Windows 一次执行 `python run.py --env shortlink-local --level core` 得到 6 条真实 PASS 后，Stage 4.5 才正式封板并进入 Stage 5。

### 0.13 V3.0 Stage 4.5 Sentinel 修复与 Stage 5 MySQL/Redis 深层校验

根据用户“不要单独出小修复版，直接合并进入第五阶段”的要求，本版本一次完成 Stage 4.5 小修复与 Stage 5：

1. 用户真实执行 V2.11 Core 得到 `5 passed, 1 failed, 6 deselected`；前五条异常/边界真实通过，E6 在真正进入回收站逻辑之前，其前置 Create 返回 HTTP 200 + `B100000`；
2. 对照 Java Sentinel 配置确认 Create 资源 QPS=1，E4 Create 与 E6 前置 Create 在同一秒连续执行会触发限流，因此该失败不是 Recycle/Redirect/YAML 逻辑错误；
3. `create_shortlink_from_yaml()` 只对源码确认的 `B100000` 做有界重试，次数和间隔来自 `env.shortlink-local.yaml -> shortlink.create_retry`；普通 `test_create.py` 仍严格单次请求，其他 HTTP/业务错误立即失败；
4. 真实短链接 username/password 已从终端 `export` 迁移到 `config/env.shortlink-local.yaml`；登录 YAML 和 fixture 统一读取同一 `runtime_config`，用户以后只修改 YAML；
5. 新增 Stage 5 MySQL/Redis 依赖 `PyMySQL` 与 `redis-py`，连接只在对应 regression fixture 被请求时懒建立，Smoke/Core collection 不连接基础设施；
6. 根据 Java ShardingSphere 5.3.2 配置复刻 `HASH_MOD`：Python 实现 Java `String.hashCode()` 的 UTF-16/32 位有符号语义，再按 `abs(hashCode) % 16` 定位 `t_link_x` 与 `t_link_goto_x`；
7. 新增 3 条 MySQL Regression：Create 物理分片持久化、Recycle/Remove 状态迁移、Redis Stream Statistics 最终落库；数据库探针只有参数化 SELECT，不直接写业务表；
8. 新增 3 条 Redis Regression：Login Hash + TTL、Create goto cache 与 Recycle 删除、Redirect UV/UIP Set；Redis 探针只读，不主动改变业务状态；
9. Redis Stream 不采用“队列中必须残留消息”的瞬时断言，而通过 Redirect 同步 UV/UIP、Stats API 最终一致性以及 MySQL access_stats 最终落库形成稳定因果证据；
10. 真实 shortlink collection 固定为 18 条：Smoke 6、Core 6、Regression 6；Stage 5 不继续扩张业务接口数量；
11. Stage 5 的代码、分片算法、配置解析、fixture 和 collection 已完成 TDD/离线回归；当前最终工作树验证为 framework `117 passed`、默认离线全量 `123 passed`、Smoke/Core/Regression 均为 `6/18 selected`、compileall PASS；真实 MySQL/Redis 通过状态仍必须等待用户 Windows 本机执行 `--level regression`，不能由沙箱离线测试冒充。

### 0.14 V3.1 回归项目原始定位：Stage 5 通用 YAML 数据源断言重构

用户重新提供最初项目计划书后，本版本明确纠正 V3.0 中“Stage 5 逐渐短链接专用化”的架构偏移。**项目名称与定位从未改变：本项目是 AI 辅助接口自动化测试框架，短链接 SaaS 只是当前真实被测系统（SUT）。** 后续阶段编号可以根据真实实施过程调整，但以下边界作为当前唯一规范：

1. `core/` 只保留通用 CaseLoader、ApiRunner、RequestClient、VariableContext、Extractor、AssertionEngine，不允许出现短链接表名、Redis Key、gid、shortUri 或业务码；
2. 正式建立原计划书中的通用 `db/` 层：`MySQLClient` / `RedisClient` 从 `data_sources.<kind>.<source>` 读取命名数据源，懒连接并提供只读查询能力；
3. Stage 5 的重点从“短链接专用 MySQL/Redis Probe”纠正为**统一断言引擎的 YAML 数据源规则**：`db_exists/db_eq/db_gte` 与 `redis_exists/redis_eq/redis_hfield_exists/redis_ttl_between/redis_scard_gte`；
4. `ApiRunner` 在当前响应完成 extract 后再动态解析 validation，因此当前接口刚提取出的 id/token 等变量可直接驱动同一 Case 的数据库或缓存断言；
5. 新增 YAML `poll` 作为通用最终一致性能力，只有 Case 显式声明时才有界重试断言；网络错误和普通业务请求不自动重试；
6. `CaseLoader` 将 YAML `level` 与 `tags` 自动转换为 Pytest marker，使 smoke/core/regression 和业务标签真正回到数据驱动层；
7. 当前短链接接入文件按业务域收敛为 4 个 Python + 4 个 YAML：Auth、Link、Redirect、Statistics；YAML 与 Python 放在同一 `testcases/shortlink/` 项目目录下，不再“一 Case 一文件”；
8. 短链接特有的 ShardingSphere 表前缀、Redis Key 前缀、Gateway Header、回收路径、Sentinel B100000 等全部限制在 `config/env.shortlink-local.yaml`、`testcases/shortlink/support.py` 和项目 YAML；
9. Java `String.hashCode/HASH_MOD` 数学算法保留为无业务表名的通用 `utils/sharding.py`，其他采用相同算法的 Java SUT 可以复用；
10. V3.0 中 `infrastructure.py + test_stage5_mysql.py + test_stage5_redis.py` 的短链接专用架构被本版本正式替代，不再作为当前方案；6 条 Regression 逻辑仍保留，但分布在真实业务域 YAML，通过统一断言执行；
11. 登录测试账号继续从环境 YAML `${config(section,key)}` 读取，不要求终端 `export`；该能力是 DebugTalk 的通用配置读取，不在通用模块中写死 `shortlink` section；
12. 当前新增架构守护测试扫描 `core/db/utils`，若出现短链接业务 token 则直接失败；这条约束用于保证未来接入订单/支付等项目时原则上只新增 `config/env.<project>.yaml + testcases/<project>/`，而不修改框架核心；
13. 原计划书后续主线继续保留：Stage 5 数据库/缓存多维断言 -> CI/CD 与报告归档 -> AI 接口文档生成 YAML / 失败日志分析 -> 工程质量、README、简历和面试材料。**短链接测试数量不再作为框架进度本身。**
14. 公共 Pytest collection 不再判断 `shortlink-local/demo` 等具体名称；环境 YAML 通过 `test_selection.include_suites` 声明本次收集的 `testcases/<suite>/`，新项目无需修改公共 `conftest.py`；
15. `pytest.ini` 只保留 smoke/core/regression 等框架级层级，具体项目的 `tags` 由根 `conftest.py` 在 collection 前扫描 YAML 动态注册，并继续启用 strict-markers；
16. Stage 5 增加架构/注释守护：公共 `core/db/utils/conftest.py/pytest.ini` 出现当前 SUT 业务 token 会失败，本次修改的通用 Python 与环境 YAML 也进入高密度中文注释自动检查。
17. V3.1 最终交付 ZIP 已在全新目录重新解压验证：框架测试 `100 passed`、默认 Mock 全量 `106 passed`；当前 SUT collection 仍为 Smoke/Core/Regression 各 `6/18 selected`，`test` 环境只收集 6 条 Demo，compileall、旧凭据依赖扫描与公共框架业务硬编码扫描均通过；真实基础设施结果仍等待用户本机。

### 0.15 V3.1.1 真实 Core 完成与 Redis RESP 协议兼容修复

用户在 Windows 本机使用 V3.1 完成两次真实验收后，本版本只修复通用 Redis Client 的协议兼容问题，不改变短链接业务 YAML 断言语义：

1. `python run.py --env shortlink-local --level core` 真实结果为 `6 passed, 12 deselected in 5.58s`，因此 Stage 4.5 六条异常/边界用例正式关闭为“真实环境已验证”；E6 的前置 Create 有界重试路径也已在真实运行中成功跨过临时限流并完成 Recycle -> Redirect notfound -> Remove；
2. `python run.py --env shortlink-local --level regression` 真实结果为 `3 passed, 3 failed, 12 deselected`；Create MySQL 物理分片、Recycle/Remove MySQL 状态迁移、Statistics MySQL 最终持久化三条真实通过；
3. 三条失败全部来自 Redis 连接握手，错误一致为 `unknown command HELLO ... 3`，发生在 `redis_hfield_exists/redis_ttl_between/redis_eq/redis_scard_gte` 真正读取业务 Key 之前，因此不能把它们误判成 Redis Key、TTL、UV/UIP 业务规则错误；
4. 根因是项目依赖原先声明 `redis>=5.0` 且 `RedisClient` 未显式指定线协议；redis-py 8 默认使用 RESP3 并发送 `HELLO 3`，而当前本地 Redis/兼容代理不支持该命令；
5. `RedisSettings` 新增通用 `protocol` 字段，从 `data_sources.redis.<source>.protocol` 读取；默认值为 2，兼容 Redis 5.x/不支持 HELLO 的代理，明确支持 RESP3 的项目可以在自己的环境 YAML 配置 `protocol: 3`；
6. `RedisClient` 对 Fake factory 与真实 `redis.Redis(...)` 都显式透传 protocol，避免客户端主版本升级再次偷偷改变连接行为；
7. `env.shortlink-local.yaml` 当前 Redis 数据源显式声明 `protocol: 2`，`env_template.yaml` 同步提供通用说明；这个字段属于数据源配置，不包含短链接业务知识；
8. 依赖范围收敛为 `redis>=5.0,<9`，并加入 constraints，减少未来未经验证主版本漂移；
9. 新增 TDD 回归证明：未声明 protocol 时默认 RESP2，项目可以显式覆盖为 RESP3；修复后 framework `101 passed`、默认离线全量 `107 passed`、Smoke/Core/Regression collection 均保持 `6/18 selected`、compileall PASS；
10. 当前真实状态：Stage 4.5 Core 6/6 已关闭；Stage 5 MySQL 3/3 已真实通过；Stage 5 Redis 连接兼容修复已完成，3 条 Redis Regression 仍需用户本机重新运行后才能标记真实通过。


### 0.16 V3.2.2 Stage 5 真实关闭与 Stage 6 CI/CD 平台验收进行中

用户确认 V3.1.1 修复后的 Regression 已在 Windows 真实环境通过，因此 Stage 5 正式关闭。本版本进入 Stage 6，并继续坚持“AI 辅助接口自动化测试框架是主体，真实 SUT 只是接入对象”的架构边界：

1. Stage 5 当前真实状态更新为完成：Stage 4 Smoke 6/6、Stage 4.5 Core 6/6、Stage 5 Regression 6/6 均已由用户本机真实环境验证；MySQL 物理分片/状态迁移/统计落库与 Redis Hash/TTL/goto cache/UV-UIP Set 均完成真实验收；
2. 新增 `.github/workflows/api-test.yml` 作为**公共框架 CI**：GitHub 托管 Runner 只运行 `tests/`、`env=test` Mock smoke 与 compileall，不尝试访问开发者本机真实 SUT；
3. GitHub Actions 当前使用官方主版本 `actions/checkout@v6`、`actions/setup-python@v6`、`actions/upload-artifact@v7`，Python 显式固定 3.11，并通过 `requirements-dev.txt + constraints.txt` 安装与本地一致的依赖集合；
4. workflow 在 push、pull_request、workflow_dispatch 时触发，并通过 `if: always()` 保存 framework JUnit、Demo run 的 JUnit/Allure Results/run.json 与日志；
5. 新增根目录 `Jenkinsfile` 作为**可访问真实 SUT 节点的参数化 Pipeline**，只暴露 `ENV_NAME` 与 `LEVEL` 两个框架级参数，不写死当前短链接环境；
6. Jenkinsfile 同时兼容 Windows `bat` 与 Linux `sh`，通过统一 `python run.py --env <ENV_NAME> --level <LEVEL>` 执行，关闭同一 Job 并发以降低共享测试环境互相污染风险；
7. Jenkins `post { always { ... } }` 使用 JUnit 记录测试结果，并通过 `archiveArtifacts` 保存 `reports/runs/**/*` 与 `logs/**/*`；当前不强制依赖 Jenkins Allure 插件，原始 Allure Results 先作为标准 Artifact 保留；
8. 新增 `tests/integration/test_ci_contract.py`，TDD RED 阶段先因 workflow/Jenkinsfile 缺失得到 3 failures，配置创建后 3/3 GREEN；该测试同时禁止公共 CI 写死 `shortlink-local`、本地域名、业务表名和 Redis Key；
9. 新增 `docs/10_CI-CD接入说明.md`，说明 GitHub Actions/Jenkins/Artifact 的职责、真实本地 SUT 的网络限制、Windows/Linux Agent 和参数化执行方式；
10. 当前工作树验证：framework tests `104 passed`、默认 Mock 全量 `110 passed`、`python run.py --env test --level smoke` 为 `2 passed / 4 deselected`，当前真实 SUT Smoke/Core/Regression collection 均为 `6/18 selected`，compileall PASS；
11. Stage 6 当前代码与离线契约已完成；用户已将仓库首次 push 到 GitHub，`API Autotest Framework CI` 云端 Run 为绿色且成功生成 Artifact，因此 **GitHub Actions 真实平台验收已完成**；Jenkins 真实 Pipeline Run 仍属于待完成的平台验收项；
12. 用户新增交付规则：若后续只是修改单个文件，只交付该文件的替换版，不重新压缩整个项目；只有多文件阶段性改造才生成完整项目包；项目计划书每次修改仍必须同步更新。
13. 用户已完成第二次 push（清理 `.idea/` 后），GitHub Actions 再次绿色且 Artifact 正常生成；因此 GitHub Actions 公共框架 CI 已获得**连续两次真实云端成功证据**，当前 Stage 6 唯一剩余平台验收项切换为 Jenkins Pipeline。


### 0.17 V3.2.3 Jenkins Windows 首次真实 Pipeline 排障与编码隔离修复

Jenkins 已在用户 Windows 本机完成安装并创建 `Pipeline script from SCM` Job。当前真实平台证据进一步更新如下：

1. Jenkins 能从公开 GitHub 仓库读取根目录 `Jenkinsfile`，说明 Job 的 SCM URL、`main` 分支、Script Path 与 Pipeline-as-Code 配置均已正确建立；
2. 第一次 Build 在 Checkout 阶段因 `github.com:443` 临时连接失败而中止；第二次 Build 已成功执行 `git fetch` 并 checkout `main` 最新提交，因此该网络失败按真实证据判定为瞬时连接问题，不修改 Jenkinsfile，也不增加 Git 凭据；
3. 第二次 Build 进入 `Install Dependencies` 后，Jenkins Windows Service 调用到系统可见的 `D:\Anaconda3\python.exe`，pip 在中文 Windows 区域设置下使用 CP936/GBK 解码 UTF-8 的 `requirements-dev.txt`，触发 `UnicodeDecodeError: 'gbk' codec can't decode ...`；
4. GitHub 仓库中的 `requirements-dev.txt`、`requirements.txt` 与 `constraints.txt` 均为 UTF-8，且包含中文说明，因此失败根因是 Jenkins Service 的 Python 默认文本编码环境，而不是依赖声明本身错误；
5. Jenkinsfile 的定向修复是在 Pipeline 进程树内设置 `PYTHONUTF8=1`，不修改整台 Windows 的全局编码；Python 官方说明该变量会启用 UTF-8 Mode，适合避免 Windows ANSI Code Page 造成的 UTF-8 文本读取问题；
6. 同一次定向修复把 Jenkins 当前找到的系统 Python 仅作为“创建 Workspace 虚拟环境”的引导解释器：每次 Build 重新创建 `.venv`，依赖安装和 `run.py` 执行均改用 `.venv` 内解释器，避免 Jenkins 将测试依赖直接安装进用户 Anaconda Base；
7. Jenkinsfile 仍只消费通用 `ENV_NAME` / `LEVEL` 和统一 `run.py`，未新增短链接环境名、域名、表名或 Redis Key；Windows/Linux 双平台分支继续保留；
8. 修复前定向契约检查对 `PYTHONUTF8`、`.venv`、Windows/Unix 虚拟环境解释器均为 false；修复后全部为 true，既有 `tests/integration/test_ci_contract.py` 保持 `3 passed`；
9. 当前 Jenkins 真实平台状态仍为**验收进行中**：Checkout 已真实成功，下一步需用户提交新的 Jenkinsfile 后再次 Build，目标先完成 `ENV_NAME=test / LEVEL=smoke` 的 Mock Pipeline，再进入真实 SUT 参数化验证。


### 0.18 V3.2.4 Jenkins Mock Pipeline 真实绿色验收

用户已在 Jenkins Windows 本机对修复后的 Jenkinsfile 完成再次真实 Build，Stage 6 平台证据更新如下：

1. Jenkins 成功从 GitHub `main` 分支 checkout 提交 `c3c056af762c18e57513998fab1c0414fd62a79e`，提交信息为 `fix: isolate Jenkins Python environment`；
2. `Install Dependencies` 阶段成功识别 Python 3.12.3，并在 Jenkins Workspace 内重新创建 `.venv`，随后使用 `.venv\Scripts\python.exe` 升级 pip 和安装 `requirements-dev.txt -c constraints.txt`；
3. 上一轮 CP936/GBK 解码错误未再出现，证明 `PYTHONUTF8=1` 与 Workspace 虚拟环境隔离修复在真实 Jenkins Windows Service 中生效；
4. `Run API Tests` 阶段通过统一入口执行 `.venv\Scripts\python.exe run.py --env "test" --level "smoke" --run-id "jenkins-10"`；
5. Pytest 共收集 6 条 Demo 用例，按 smoke 层级选择 2 条、deselect 4 条，最终 `2 passed, 4 deselected in 0.85s`；
6. Jenkins 成功生成 `reports/runs/jenkins-10/junit.xml`，`post` 阶段正常执行 JUnit 结果记录与 Artifact 归档，Pipeline 最终状态为 `SUCCESS`；
7. 因此 Stage 6 的 **GitHub Actions 公共 CI** 与 **Jenkins 本机 Mock CI** 均已获得真实绿色平台证据；
8. Stage 6 尚保留最后一项增强验收：在不把真实账号密码提交到公共 GitHub 的前提下，通过 Jenkins 参数化方式执行当前真实短链接 SUT 的 `smoke`，确认 Jenkins 节点对真实 Gateway/Project 服务的访问与私有环境 YAML 注入方式；完成后即可正式关闭 Stage 6 并进入 Stage 7 AI。


---

## 1. 项目基本信息

### 1.1 项目名称

**AI 辅助接口自动化测试框架**

建议最终仓库名称：

```text
ai-api-autotest-framework
```

### 1.2 项目定位

本项目面向测试开发岗位求职场景。

目标不是简单学习、Fork 或包装一个 GitHub 项目，而是：

1. 审查并理解一个开源接口自动化框架；
2. 修复其真实存在的运行和设计问题；
3. 重构为具备清晰架构和测试保障的自有框架；
4. 接入用户已有的短链接 SaaS 真实业务系统；
5. 建立真实接口、数据库、缓存、报告和 CI/CD 能力；
6. 加入轻量但可验证的 AI 用例生成与失败分析能力；
7. 最终形成可运行、可演示、可写简历、可在面试中讲清楚个人贡献的测试开发项目。

### 1.3 用户背景

用户当前目标：**寻找测试开发方向工作**。

当前已了解或正在学习的技术：

- Pytest
- Allure
- Selenium
- POM
- CI/CD

用户已有真实项目：

> 一个可运行的短链接 SaaS 开发平台，为企业和个人用户提供短链接创建、管理、分享、访问分析和跟踪能力。

该系统将作为本自动化测试框架的真实被测系统。

### 1.4 项目最终关系

```text
短链接 SaaS 真实业务系统
            ↑
      接口与数据验证
            ↑
AI 辅助接口自动化测试框架
            ↑
审查、修复并重构开源基线
            ↑
Pytest + Requests + YAML + Allure
+ MySQL / Redis + CI/CD + AI
```

---

## 2. 基线仓库选择与核查结论

### 2.1 基线仓库

```text
https://github.com/zed123214/api-autotest-framework.git
```

### 2.2 继续选择该仓库的原因

该仓库仍然适合作为学习和改造基线：

- 技术栈贴合测试开发方向；
- 具备 Pytest、Requests、YAML、Allure、Jenkins 等基本元素；
- 目录规模较小，适合源码阅读；
- 已有请求封装、YAML 加载、变量提取、断言和日志模块；
- 问题边界较清晰，适合展示“审查—修复—重构—验证”的完整能力；
- MIT License 允许使用、修改和分发，但必须保留许可证和版权声明。

### 2.3 仓库成熟度判断

联网核查确认：

- 仓库当前规模较小；
- 当前仅有 2 次提交；
- 最新提交日期为 2026-05-12；
- 第二次提交主要是 README 文档名称调整；
- MySQL / Redis 明确为 Demo；
- 示例接口、账号、Token 和数据库配置均为模拟数据。

因此，该仓库应被定位为：

> **展示型、教学型接口自动化框架骨架，而不是经过长期真实业务迭代验证的成熟框架。**

后续不能默认 README 或代码注释中的能力已经可靠实现，必须逐项验证。

### 2.4 当前可继承的骨架能力

可以作为学习和重构参考：

- `run.py` 的 Pytest 统一启动入口；
- `pytest.ini` 中的 marker 定义；
- YAML 数据结构示例；
- `RequestBase` 请求编排思路；
- `RequestClient` 基础 Session 封装；
- JsonPath / 正则变量提取；
- `DebugTalk` 动态函数调用思路；
- Allure 请求与响应附件；
- 日志滚动输出；
- Jenkins Pipeline 示例结构。

这些内容可以借鉴，但不应原样照搬。

### 2.5 已确认问题清单

#### P0：阻断运行或导致测试结果失真的问题

| 编号 | 问题 | 影响 | 处理要求 |
|---|---|---|---|
| P0-01 | 测试文件拼接 YAML 路径时重复加入 `testcase/` | YAML 文件可能找不到，Pytest 可能收集到 0 条参数用例 | 修正路径并加入文件不存在时的明确失败 |
| P0-02 | `RequestBase` 传入 `json`，`RequestClient` 又使用 `json_body` 再传 `json` | JSON 请求可能发生重复关键字 `TypeError` | 统一请求参数命名并增加单元测试 |
| P0-03 | YAML 中 `testCase.header` 不会覆盖 `baseInfo.header` | 无 Token、错误 Token 等负向用例逻辑失真 | 实现请求头合并、覆盖和删除语义 |
| P0-04 | `core` 用例依赖 `smoke` 登录结果 | 单独执行 `--core` 时拿不到 Token | 消除跨测试文件执行顺序依赖 |
| P0-05 | 调用接口依赖发布接口生成的 `interface_id` | 执行顺序变化时链路失败 | 使用场景 fixture 或单链路编排 |
| P0-06 | `--regression` 当前可能没有对应 marker 用例 | 命令执行成功但没有真实测试 | 重新定义 marker 语义并校验收集数量 |
| P0-07 | YAML 加载失败只记日志并返回空列表 | “0 用例执行”可能被误判为成功 | 对必需文件和非法结构直接抛出异常 |
| P0-08 | 默认 host 硬编码为 `localhost:8080` | 环境配置和 Jenkins 环境变量不生效 | 建立真实配置加载优先级 |
| P0-09 | 自定义 Allure 结果路径时 HTML 目录推导不可靠 | 结果目录与报告目录可能混用 | 独立配置 `allure-results` 与 `allure-report` |
| P0-10 | Jenkins 归档 `reports/*.xml`，但运行命令未生成 JUnit XML | Jenkins 可能找不到测试结果 | 增加 `--junitxml` 或调整 Pipeline |

#### P1：工程可靠性问题

| 编号 | 问题 | 影响 | 处理要求 |
|---|---|---|---|
| P1-01 | 注释称支持重试，但代码没有真实重试适配器 | 网络波动时不稳定 | 使用 `HTTPAdapter + Retry`，限定可重试状态和方法 |
| P1-02 | 所有 HTTPS 请求强制 `verify=False` | 安全性差，隐藏证书问题 | 默认开启校验，仅测试环境可显式关闭 |
| P1-03 | Header 直接写日志和 Allure | Token 等敏感信息泄露 | 增加统一脱敏器 |
| P1-04 | 上下文变量通过共享 `extract.yaml` 追加写入 | 重复键、污染、并发冲突 | 改为内存上下文，文件仅作可选调试输出 |
| P1-05 | 已安装 `pytest-xdist`，但上下文机制不支持并发 | 并行执行结果不可信 | 明确并发边界，后续设计隔离上下文 |
| P1-06 | 依赖只设置最低版本 | 环境不可复现 | 生成锁定版本或 constraints 文件 |
| P1-07 | 配置模板与实际代码脱节 | 配置看似存在但不生效 | 建立统一 `ConfigManager` |
| P1-08 | 日志模块参数硬编码 | 配置中的级别、保留时间、大小无效 | 日志初始化读取配置 |
| P1-09 | 请求报告未完整记录耗时、重试、异常上下文 | 排障价值不足 | 统一请求结果模型和 Allure 附件 |
| P1-10 | 框架核心模块没有自身单元测试 | 修改后容易引入回归 | 为 loader、context、request、assertion 建立测试 |

#### P2：功能缺口

| 编号 | 当前状态 | 目标状态 |
|---|---|---|
| P2-01 | MySQLClient 固定返回模拟数据 | 真实连接、参数化查询、事务和关闭机制 |
| P2-02 | RedisClient 为内存字典 | 真实 Redis 连接和 key 校验 |
| P2-03 | `db` 断言只打印日志 | 实现 `db_eq`、`db_exists`、`db_count` 等真实断言 |
| P2-04 | 断言类型有限 | 增加 exists、contains、in、gt、lt、schema、response_time 等 |
| P2-05 | 无真实多环境命令 | 支持 `--env test --level smoke` |
| P2-06 | 无 AI 能力代码 | 实现 YAML 草稿生成和失败分析 |

### 2.6 能力声明规则

项目中的能力分为三种状态：

| 状态 | 含义 | 是否可写入简历为“已实现” |
|---|---|---|
| 计划中 | 仅在计划书或 TODO 中定义 | 否 |
| 已编码未验证 | 已有代码，但没有完整运行证据 | 否 |
| 已验证 | 有自动化测试、运行结果、Allure 或 CI 证据 | 是 |

任何功能只有达到“已验证”状态，才允许写入最终简历或面试材料。

---

## 3. 最终目标与项目边界

### 3.1 项目一句话描述

基于 Pytest + Requests + YAML + Allure 设计并实现接口自动化测试框架，接入自研短链接 SaaS 系统作为真实被测服务，支持数据驱动、上下文变量管理、统一断言、MySQL / Redis 数据校验、CI/CD 分层执行，并引入大模型能力实现接口文档生成 YAML 用例草稿和失败日志智能分析。

> 上述描述是最终目标。项目未完成前，应根据已验证进度使用阶段性描述，不能提前全部写入简历。

### 3.2 最终交付能力

#### 框架基础能力

- YAML 数据驱动；
- Requests Session 请求封装；
- Pytest 参数化；
- 多环境配置；
- 上下文变量提取、替换和隔离；
- 请求头合并与用例级覆盖；
- 统一断言引擎；
- JsonSchema 校验；
- 日志和敏感信息脱敏；
- Allure 报告；
- 框架核心单元测试。

#### 真实业务测试能力

- 用户注册和登录；
- Token 获取、刷新、失效和权限验证；
- 短链接创建、查询、编辑、启停和删除；
- 短链接跳转；
- 链接过期；
- 访问统计；
- 企业 / 个人用户权限；
- 异常参数；
- 合法范围内的安全边界验证。

#### 数据校验能力

- MySQL 真实查询；
- Redis 真实查询；
- 接口响应与数据库一致性验证；
- 访问统计异步入库等待；
- 测试数据准备和清理。

#### 工程化能力

- GitHub Actions；
- Jenkins Pipeline；
- smoke / core / regression 分层；
- JUnit 与 Allure 报告归档；
- 失败日志归档；
- 环境变量和凭据管理；
- 依赖锁定；
- 代码检查和测试质量门禁。

#### AI 增强能力

- 根据接口文档生成 YAML 用例草稿；
- 推荐正常流、异常流和边界场景；
- 分析失败请求、响应、断言和 SQL 结果；
- 输出可能原因和排查路径；
- 输入日志脱敏；
- AI 输出 Schema 校验和人工审核。

### 3.3 明确不做或暂缓的内容

当前项目暂不做：

- 完整测试平台前端；
- 复杂权限管理后台；
- Selenium / POM / UI 自动化混合；
- 移动端自动化；
- 性能测试平台；
- 复杂 RAG 知识库；
- 多智能体系统；
- 自动向生产环境执行测试；
- 未经授权的攻击或漏洞利用。

---

## 4. 目标架构与目录结构

### 4.1 推荐目录

```text
ai-api-autotest-framework/
├── README.md
├── LICENSE
├── THIRD_PARTY_NOTICES.md
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── constraints.txt
├── pytest.ini
├── run.py
├── .env.example
├── config/
│   ├── config.yaml
│   ├── env.dev.yaml
│   ├── env.test.yaml
│   └── env.stage.yaml
├── core/
│   ├── config_manager.py
│   ├── case_loader.py
│   ├── request_client.py
│   ├── api_runner.py
│   ├── variable_context.py
│   ├── assertion_engine.py
│   ├── extractor.py
│   ├── schema_validator.py
│   └── result_model.py
├── utils/
│   ├── logger.py
│   ├── sanitizer.py
│   ├── yaml_util.py
│   ├── jsonpath_util.py
│   ├── random_util.py
│   ├── time_util.py
│   └── wait_util.py
├── db/
│   ├── mysql_client.py
│   └── redis_client.py
├── ai/
│   ├── client.py
│   ├── testcase_generator.py
│   ├── failure_analyzer.py
│   ├── output_validator.py
│   └── prompt_templates/
│       ├── generate_yaml_case.md
│       └── analyze_failure.md
├── testcases/
│   ├── shortlink/
│   │   ├── test_auth.py
│   │   ├── test_link.py
│   │   ├── test_redirect.py
│   │   └── test_statistics.py
│   └── yaml/
│       ├── auth.yaml
│       ├── shortlink.yaml
│       ├── redirect.yaml
│       └── statistics.yaml
├── tests/
│   ├── unit/
│   │   ├── test_case_loader.py
│   │   ├── test_variable_context.py
│   │   ├── test_request_client.py
│   │   ├── test_assertion_engine.py
│   │   └── test_sanitizer.py
│   └── integration/
│       ├── test_mock_flow.py
│       └── test_shortlink_flow.py
├── schemas/
│   ├── create_shortlink_schema.json
│   └── statistics_schema.json
├── mock_server/
│   └── app.py
├── reports/
│   ├── allure-results/
│   ├── allure-report/
│   └── junit/
├── logs/
├── docs/
│   ├── 01_项目背景与开源基线说明.md
│   ├── 02_基线源码审查报告.md
│   ├── 03_框架执行流程.md
│   ├── 04_YAML用例规范.md
│   ├── 05_上下文变量机制.md
│   ├── 06_断言引擎设计.md
│   ├── 07_短链接业务测试设计.md
│   ├── 08_CI-CD接入说明.md
│   ├── 09_AI用例生成与失败分析.md
│   └── 10_面试讲解稿.md
└── .github/
    └── workflows/
        ├── unit-test.yml
        └── api-test.yml
```

### 4.2 目录职责

| 目录 | 职责 |
|---|---|
| `core/` | 框架核心能力，不包含具体短链接业务 |
| `utils/` | 通用工具、脱敏、等待、随机数据等 |
| `db/` | MySQL / Redis 真实连接和查询 |
| `ai/` | AI 客户端、Prompt、生成和分析能力 |
| `testcases/` | 真实短链接业务测试 |
| `tests/unit/` | 框架自身单元测试 |
| `tests/integration/` | Mock 和真实测试环境集成验证 |
| `schemas/` | JSON Schema 文件 |
| `mock_server/` | 阶段 1、2 使用的受控被测服务 |
| `reports/` | Allure 与 JUnit 输出 |
| `docs/` | 架构、规范、审查和面试材料 |

### 4.3 架构原则

- 框架核心与业务用例分离；
- 配置、凭据和代码分离；
- 请求执行、变量提取和断言分离；
- 测试数据准备与断言分离；
- AI 能力与主测试执行链路解耦；
- AI 不可用时，普通接口自动化仍可正常运行；
- 单接口用例和端到端业务链路均不依赖测试文件执行顺序；
- 所有失败必须能够在日志、Allure 或 JUnit 中定位。

---

## 5. 短链接 SaaS 测试范围

### 5.1 核心模块

1. 用户认证；
2. 企业 / 个人空间；
3. 短链接管理；
4. 短链接跳转；
5. 访问统计；
6. 权限与安全；
7. 异常与边界场景；
8. 数据库与缓存一致性。

### 5.2 第一条真实端到端链路

```text
准备独立测试用户
↓
登录获取 Token
↓
创建短链接
↓
提取 link_id / short_code / short_url
↓
查询短链接详情
↓
访问短链接并校验跳转
↓
等待统计数据落库
↓
查询访问统计
↓
校验 MySQL 记录
↓
校验 Redis 缓存（若业务使用）
↓
清理本次测试数据
```

### 5.3 主要测试场景

#### 用户认证

- 注册成功；
- 登录成功；
- 密码错误；
- 用户名为空；
- Token 缺失；
- Token 错误；
- Token 过期；
- 刷新 Token；
- 退出登录后 Token 失效。

#### 短链接管理

- 创建永久短链接；
- 创建带过期时间的短链接；
- 查询列表；
- 查询详情；
- 修改标题或描述；
- 启用；
- 禁用；
- 删除；
- 自定义短链 Code；
- 重复 Code；
- 批量创建（若业务支持）。

#### 短链接跳转

- 正常 301 / 302 跳转；
- 短链不存在；
- 短链禁用；
- 短链过期；
- 短链删除；
- 原始 URL 非法；
- 重定向响应头校验。

#### 访问统计

- 单次访问后 PV 增加；
- UV 规则；
- IP、浏览器、设备和地区维度；
- 时间维度；
- 异步统计最终一致性；
- 统计接口与数据库记录一致性。

#### 权限

- 用户只能管理自己的链接；
- 企业成员角色权限；
- 普通成员无权删除企业链接；
- 管理员可以管理企业链接；
- 跨租户访问失败；
- 个人 / 企业配额限制。

#### 安全与边界

- 空 URL；
- 非法 URL；
- 超长 URL；
- 特殊字符；
- XSS 字符串输入后的安全处理；
- SQL 注入字符串输入后的参数化验证；
- `javascript:`、`file:` 等危险协议拦截；
- 内网地址 / SSRF 风险防护验证；
- 高频创建限流。

> 安全测试仅用于合法授权环境中的防护验证，不进行攻击利用。

---

## 6. 阶段实施计划

## 阶段 0：项目目标和基线确认

### 阶段目标

确定求职方向、项目定位、开源基线、真实被测系统和技术边界。

### 已完成内容

- 项目名称已确定；
- 基线仓库已确定；
- 短链接 SaaS 被测系统已确定；
- 技术主线已确定；
- 暂不做测试平台前端；
- 暂不混入 UI 自动化；
- AI 能力采用轻量可演示路线。

### 当前状态

**已完成。**

---

## 阶段 1：基线仓库审查与 P0 修复

### 阶段目标

不盲目运行和照搬代码，先确认基线仓库的真实行为，修复阻断运行和造成结果失真的问题。

### 1.1 已完成：联网静态审查

已审查：

```text
README.md
run.py
pytest.ini
requirements.txt
base/apiutil.py
base/debugtalk.py
common/request_client.py
common/yaml_loader.py
common/extractor.py
common/assertion.py
common/mysql_client.py
common/redis_client.py
common/logger.py
testcase/conftest.py
testcase/api_platform/*.py
testcase/yaml/*.yaml
config/*.template
Jenkinsfile.example
LICENSE
提交记录
```

已形成第 2.5 节问题清单。

### 1.2 已执行：建立可复现基线

1. 克隆仓库并记录 commit SHA；
2. 建立 Python 3.11 虚拟环境；
3. 安装依赖；
4. 记录操作系统、Python、Pytest、Allure 版本；
5. 执行 `pytest --collect-only`；
6. 执行原始 smoke / core / regression 命令；
7. 保存原始错误日志，不直接覆盖证据。

### 1.3 P0 修复顺序

#### P0-01：修复 YAML 路径

要求：

- 使用可靠的项目根路径；
- 文件不存在时直接使测试收集失败；
- 增加 YAML 文件路径单元测试；
- `pytest --collect-only` 收集数量必须与 YAML 用例数量一致。

#### P0-02：修复 JSON 请求参数

要求：

- 对外统一使用 `json`；
- 避免 `json` 与 `json_body` 双重传递；
- 覆盖 JSON、form、params 和 file 四类请求测试；
- 请求体进入日志前进行脱敏。

#### P0-03：实现用例级 Header 覆盖

建议语义：

```yaml
baseInfo:
  header:
    Content-Type: application/json
    Authorization: Bearer ${token}

testCase:
  - case_name: 无Token
    header:
      Authorization: null
```

要求：

- 基础 Header 与用例 Header 合并；
- 用例 Header 同名键覆盖基础值；
- `null` 表示删除该 Header；
- 增加无 Token 和错误 Token 测试。

#### P0-04：消除 marker 与依赖冲突

不再依赖以下隐含顺序：

```text
先执行 test_login.py
再执行 test_publish_api.py
再执行 test_call_api.py
```

采用以下方式之一：

- session fixture 创建登录上下文；
- scenario fixture 显式完成前置步骤；
- 单个端到端测试函数内部完成链路；
- API helper 创建前置资源。

要求：

- `pytest -m smoke` 可独立执行；
- `pytest -m core` 可独立执行；
- `pytest -m regression` 可独立执行；
- 改变测试文件顺序不影响结果。

#### P0-05：接通真实配置加载

配置优先级：

```text
命令行参数
>
环境变量
>
env.{name}.yaml
>
config.yaml 默认值
```

目标命令：

```bash
python run.py --env test --level smoke
python run.py --env stage --level regression
```

#### P0-06：修复报告输出

要求：

- Allure 原始结果和 HTML 报告分离；
- 每次运行生成唯一 run_id；
- 生成 JUnit XML；
- 命令退出码保持 Pytest 真实退出码；
- 0 条用例执行视为失败；
- 没有安装 Allure CLI 时仍保留原始结果。

### 1.4 阶段产出

- `docs/02_基线源码审查报告.md`；
- 原始运行日志；
- P0 修复提交；
- 框架基础单元测试；
- 第一版可运行 Mock smoke 测试；
- Allure Results 与 JUnit 已纳入运行链；Allure CLI HTML 作为本地展示工具链补验项；
- JUnit XML；
- 修复前后对比说明。

### 1.5 验收标准

- 不再出现 YAML 路径错误；
- JSON 请求能够真实发送；
- 用例级 Header 覆盖生效；
- smoke / core / regression 均能独立收集和执行；
- 配置文件和环境变量真实生效；
- 0 用例执行不会被判定为成功；
- Allure 与 JUnit 均能生成；
- 所有 P0 修复均有自动化测试或运行证据。

### 当前状态

```text
联网静态审查：已完成
隔离基线重建与原始问题复现：已完成
P0 修复：已完成并通过自动化测试
Mock 分层执行与 JUnit：已完成
用户本地 Python 3.11.15 + allure-pytest 2.16.0：已确认插件可加载
Allure CLI HTML 可视化：仍需在安装 CLI 的本地环境补验
阶段整体验收：已完成；HTML 可视化作为非阻断补验项
```

---

## 阶段 2：受控 Mock 验证与框架测试保障

### 阶段目标

在接入真实短链接系统前，先用可控 Mock 服务证明框架基础能力正确，避免把框架 Bug 和业务系统 Bug 混在一起。

### 具体任务

1. 建立轻量 Mock 服务；
2. 提供登录、资源创建、资源查询、错误鉴权等接口；
3. 为以下模块编写单元测试：
   - YAML loader；
   - ConfigManager；
   - VariableContext；
   - Header merge；
   - RequestClient；
   - Extractor；
   - AssertionEngine；
   - Sanitizer；
4. 建立 Mock 端到端链路；
5. 验证随机执行顺序；
6. 验证失败报告内容；
7. 验证异常响应、非 JSON 响应、超时和连接失败。

### 阶段产出

- `mock_server/`；
- `tests/unit/`；
- `tests/integration/test_mock_server.py`；
- `tests/integration/test_error_paths.py`；
- 单元测试报告；
- 覆盖率报告；
- Mock Allure 报告。

### 验收标准

- 核心模块单元测试全部通过；
- Mock 主链路可重复执行；
- 不依赖文件执行顺序；
- 失败时 Allure 能展示请求、响应和断言差异；
- 敏感 Header 在日志和报告中被隐藏；
- 框架改动具备回归保护。

### 当前状态

**已完成阶段 2 功能与自动化验收。**

已验证结果：

```text
框架自身测试：50 passed
业务 Mock 用例：6 passed
全量测试：56 passed
smoke：2 passed, 4 deselected
core：2 passed, 4 deselected
regression：2 passed, 4 deselected
核心目录覆盖率：78%
```

已完成：

- 受控 Mock 登录 / 发布 / 调用主链路；
- 内存 `VariableContext` 与作用域隔离；
- `Extractor`、`DebugTalk`、`RequestBase` 统一使用注入上下文；
- 旧 YAML 动态变量表达式兼容；
- 统一断言引擎增强；
- 非 JSON 响应验证；
- 真实请求超时验证；
- 连接失败验证；
- Allure 请求 Header 脱敏附件验证；
- Runner 对 Allure 插件存在 / 不存在环境的兼容验证；
- 覆盖率 XML 生成。

Allure CLI HTML 页面展示仍属于本地工具链补验，不阻断阶段 3。

---

## 阶段 3：重构为自己的框架仓库

### 阶段目标

在 Stage 2 已验证行为稳定的前提下，把教学型基线遗留结构迁移为正式个人项目架构，同时不混入新的真实业务功能，确保“架构变化、测试行为不变”。

### 实际完成内容

1. 正式目录迁移：

```text
Stage 2                         Stage 3
base/apiutil.py          ->     core/api_runner.py
base/debugtalk.py        ->     utils/debugtalk.py
common/config_manager.py ->     core/config_manager.py
common/request_client.py ->     core/request_client.py
common/variable_context.py ->   core/variable_context.py
common/extractor.py      ->     core/extractor.py
common/assertion.py      ->     core/assertion_engine.py
common/yaml_loader.py    ->     core/case_loader.py
common/logger.py         ->     utils/logger.py
common/sanitizer.py      ->     utils/sanitizer.py
common/jsonpath_util.py  ->     utils/jsonpath_util.py
common/project_paths.py  ->     utils/project_paths.py
common/allure_compat.py  ->     utils/allure_compat.py
testcase/                ->     testcases/
```

2. 将 `RequestBase` 实现类重命名为 `ApiRunner`，使“用例执行编排器”的职责更清楚；
3. `testcases/demo/` 专门保存受控 Mock Demo，和未来 `testcases/shortlink/` 真实业务用例分离；
4. 删除旧 `base/`、`common/`、`testcase/` 正式入口，不保留两套 import 路径；
5. 删除 Stage 2 已不再使用的 `YamlContext` 全局兼容运行态；
6. 所有 Python 模块顶部补充模块作用说明；
7. 框架公共类、公共函数和 Pytest fixture 补充 docstring，关键逻辑增加“为什么这样设计”的注释；
8. 配置 YAML 增加字段用途和安全边界说明；
9. 新增 `THIRD_PARTY_NOTICES.md`，明确 MIT 上游来源与个人重构边界；
10. 新增 `.env.example`，为真实短链接、MySQL、Redis 后续配置保留安全入口；
11. 新增 `pyproject.toml`、`requirements-dev.txt`、`constraints.txt`，开始收敛工程元数据和依赖范围；
12. README 更新为 Stage 3 正式架构、执行链和已验证/未实现能力。

### 自动化验收

```text
Stage 3 架构规范测试：7 passed
框架自身测试：57 passed
Demo 业务用例：6 passed
全量测试：63 passed
collect-only：6 tests collected
smoke：2 passed, 4 deselected
core：2 passed, 4 deselected
regression：2 passed, 4 deselected
核心源码覆盖率：79%
```

### 阶段产出

- 正式 `core/`、`utils/`、`testcases/` 目录；
- `THIRD_PARTY_NOTICES.md`；
- `.env.example`；
- `pyproject.toml`、`requirements-dev.txt`、`constraints.txt`；
- Stage 3 README；
- `tests/unit/test_stage3_structure.py`；
- Stage 3 collect/marker/JUnit/coverage 证据；
- Stage 3 设计与实施文档；
- 同步更新的 V2.3 项目计划书。

### 当前状态

**已完成。**

Allure Results/JUnit 运行链继续保留；Allure CLI HTML 页面属于本地展示工具链，不作为 Stage 3 架构完成的阻断条件。

---

## 阶段 4：接入短链接 SaaS 真实接口

### 阶段目标

把框架从 Mock 验证升级为真实业务质量保障项目。

### 前置条件

必须具备：

- 短链接 SaaS 可运行环境；
- 接口文档或可核查的 Controller / OpenAPI；
- 独立测试账号；
- 测试环境数据库访问方式；
- Redis 访问方式（若业务使用）；
- 测试数据清理权限；
- 禁止直接使用生产环境。

### 具体任务

1. 读取真实接口定义并形成真实 API 契约表；
2. 确认 Gateway/Admin/Project/Nacos/MySQL/Redis 的本地运行方式和健康状态；
3. 建立独立 `env.shortlink-local.yaml`（或最终确认的等价环境名），与 Mock `env.test.yaml` 分离；
4. 实现真实登录并提取 token，按真实系统要求发送 `username` + `token` Header；
5. 查询当前用户分组并提取 `gid`；
6. 创建永久短链接并提取 `shortUrl / fullShortUrl / shortUri`；
7. 通过分页查询确认创建结果，而不是只依赖 create 响应；
8. 使用用户已配置的 `nurl.ink -> 127.0.0.1` hosts 映射，直接访问 `http://nurl.ink:8001/<short_uri>` 验证 302 和 `Location`；
9. 访问后轮询 `/stats`，等待 Redis Stream 消费完成并验证 PV/UV/UIP 等统计；
10. 使用真实回收站业务接口清理本次测试数据；
11. 为每次运行生成 `test_run_id`，保证数据可识别、可清理；
12. 将本次发现的 `enableStatus` 部署版本缺陷沉淀为真实回归用例；
13. 真实主链路稳定后，再设计 ShardingSphere/MySQL 与 Redis 一致性断言。

### 阶段产出

当前已产出：

- `config/env.shortlink-local.yaml`；
- Auth / Group / Create / Page / Redirect / Statistics 六组真实 Python + YAML 用例；
- `testcases/shortlink/support.py`：鉴权、Group、Create、Redirect、Stats polling、RecycleBin Cleanup helper；
- `testcases/shortlink/conftest.py`：function-scope 独立前置链和 yield Teardown 自动清理；
- `tests/unit/test_stage4_comment_quality.py`：Stage 4 Python/YAML 注释规范守护；
- `docs/08_阶段4真实SaaS接入.md`。

已继续产出：

- `docs/evidence/34_stage4_real_smoke_6_passed.md`：用户 Windows 真实 `6 passed in 9.65s`；
- 第一条完整真实 E2E：Login -> Group -> Create -> Page -> Redirect -> Statistics -> Cleanup；
- Redirect 302、Stats 最终一致性轮询和回收站清理的真实运行证据。

### 验收标准

- 能真实请求短链接 SaaS；
- Token、link_id、short_code 和 short_url 可正确提取；
- 主链路可重复执行；
- 不依赖历史遗留数据；
- 测试结束后可清理数据；
- 报告中不存在明文密码或 Token。

### 当前状态

**已完成。** 用户 Windows 已完整执行六条真实 Smoke，结果为 `6 passed in 9.65s`。Redirect 已真实返回 302；Statistics 已在真实 Redis Stream 最终一致性窗口中发生多次 `/stats` 查询后通过；RecycleBin Cleanup 已在 Teardown 中真实执行。Stage 4 不再继续堆 Happy Path，当前转入 Stage 4.5 精选异常/边界测试。

---

## Stage 4.5：精选异常 / 边界真实用例

### 目标

在已完成的六条 Happy Path Smoke 之外，只补 6 条高价值异常/边界场景，证明框架能验证真实业务规则而不是只验证 HTTP 200。

### 当前实现

```text
E1 错误密码登录             ✅ 已编码 + 离线验证，待真实 Core
E2 Group 缺 token           ✅ 已编码 + 离线验证，待真实 Core
E3 Create 缺 token          ✅ 已编码 + 离线验证，待真实 Core
E4 Create 非法 originUrl    ✅ 已编码 + 离线验证，待真实 Core
E5 不存在 shortUri          ✅ 已编码 + 离线验证，待真实 Core
E6 回收后再次访问           ✅ 已编码 + 离线验证，待真实 Core
```

### 完整执行原则

- 六条全部使用 `core` marker，不改变 Stage 4 的 6 条 Smoke；
- 异常网络请求继续由 YAML 驱动，不绕过 ApiRunner；
- 错误密码测试不读取、拼接或修改真实密码；
- E2/E3 的 Gateway 401 与 E1/E4 的业务失败分别建模；
- E5/E6 关闭自动重定向，验证 Project 第一跳 notfound 契约；
- E6 只通过真实回收站接口构造状态，不直接写 MySQL；
- 离线测试只能证明请求/断言契约，真实状态必须由用户本机运行后更新。

### 完成后转入

Stage 4.5 六条精选用例真实稳定后，进入 **Stage 5：MySQL + Redis 深层一致性校验**。

---

## 阶段 5：完善核心框架能力

### 5.1 RequestClient

支持：

- GET / POST / PUT / PATCH / DELETE；
- JSON / form / params / files；
- Session 复用；
- 可配置 timeout；
- 可配置 TLS 校验；
- 有限制的自动重试；
- 请求和响应耗时；
- 结构化日志；
- Allure 附件；
- 敏感数据脱敏；
- 异常分类。

重试规则：

- 只对明确允许的方法和状态码重试；
- 不默认重试有副作用的创建请求；
- 不通过重试掩盖真实业务 Bug；
- 每次重试写入报告。

### 5.2 VariableContext

目标接口：

```text
set(key, value, scope)
get(key, scope)
replace_variables(data, scope)
clear(scope)
export_debug_snapshot()
```

要求：

- 默认使用内存上下文；
- 支持 session / scenario / case 范围；
- 支持字典和列表递归替换；
- 缺失变量默认明确失败；
- 不再依赖共享 `extract.yaml` 作为运行时唯一真源；
- 并发执行时上下文隔离。

### 5.3 AssertionEngine

目标断言：

| 类型 | 说明 |
|---|---|
| `status_code` | HTTP 状态码 |
| `eq` / `ne` | 相等 / 不相等 |
| `contains` | 包含 |
| `exists` / `not_exists` | 字段存在性 |
| `in` / `not_in` | 集合判断 |
| `gt` / `gte` / `lt` / `lte` | 数值比较 |
| `json_schema` | 响应结构 |
| `response_time_lt` | 响应时间阈值 |
| `header_eq` | 响应头校验 |
| `db_eq` | 数据库值等于预期 |
| `db_exists` | 数据库记录存在 |
| `db_count` | 数据库记录数量 |
| `redis_exists` | Redis Key 存在 |
| `redis_eq` | Redis 值校验 |

要求：

- 每条断言独立记录预期和实际；
- 不支持的断言直接失败；
- SQL 使用参数化查询；
- 数据库错误与断言失败区分；
- 支持软断言汇总，但最终必须使测试失败。

### 5.4 MySQL / Redis

MySQL：

- 真实连接；
- DictCursor；
- 参数化查询；
- query / query_one / execute；
- 上下文管理器；
- 自动关闭；
- 连接信息来自环境配置；
- 密码不写日志。

Redis：

- 真实连接；
- get / exists / ttl / delete；
- 可配置 decode；
- 连接检查；
- 测试 Key 清理；
- 密码脱敏。

### 5.5 Allure 报告

每条用例至少包含：

- 用例名称；
- 所属模块和层级；
- 环境名称；
- 请求方法和 URL；
- 脱敏后的 Header；
- 请求参数；
- 响应状态码和耗时；
- 响应 Body；
- 提取变量结果；
- 每条断言结果；
- 数据库 SQL 模板和脱敏参数；
- 清理结果；
- 失败异常；
- AI 分析建议（启用时）。

### 阶段产出

- `core/` 完整实现；
- `db/` 真实实现；
- 核心模块单元测试；
- 增强版 Allure；
- 架构和设计文档。

### 验收标准

- 不再存在 Demo 数据返回；
- MySQL / Redis 校验基于真实服务；
- 所有断言类型有测试；
- TLS、重试和脱敏策略有测试；
- 框架核心失败可定位；
- 已验证能力才更新 README。

### 当前状态

**未开始。**

---

## 阶段 6：建立短链接业务用例体系

### 阶段目标

体现真实测试分析能力，而不是堆积简单 CRUD。

### 用例分层

#### smoke

每次提交或部署后快速验证：

- 登录成功；
- 创建短链接成功；
- 短链跳转成功；
- 查询统计成功。

目标执行时间：尽量控制在数分钟内。

#### core

核心业务链路：

- 注册 / 登录 / 创建 / 跳转 / 统计；
- 永久链接；
- 过期链接；
- 禁用后访问失败；
- 删除后访问失败；
- 企业成员权限；
- 数据库一致性。

#### regression

完整回归：

- 登录异常；
- Token 异常；
- 参数边界；
- 重复 Code；
- 权限和跨租户；
- 统计准确性；
- Redis 缓存一致性；
- 安全边界；
- 清理机制；
- 历史 Bug 回归用例。

### Marker 设计

```ini
[pytest]
markers =
    smoke: 快速冒烟测试
    core: 核心业务链路
    regression: 完整回归
    auth: 认证模块
    shortlink: 短链接管理
    redirect: 短链跳转
    statistics: 统计模块
    permission: 权限模块
    security: 安全边界验证
    db: 需要数据库
    redis: 需要 Redis
    ai: 需要 AI 服务
```

### 数量目标

数量不是唯一指标，以质量和可解释性为主：

- smoke：4～8 条；
- core：15～25 条；
- regression：累计 40～60 条高质量用例；
- 每个历史 Bug 至少补充 1 条回归用例。

### 阶段产出

- 完整 YAML 用例；
- Marker 和执行说明；
- 业务覆盖矩阵；
- 缺陷与回归用例映射；
- `docs/07_短链接业务测试设计.md`。

### 验收标准

- 每一层可以独立执行；
- 用例不依赖文件顺序；
- 覆盖正常、异常、边界、权限、统计和一致性；
- 失败结果可定位；
- 清理机制稳定；
- 用例数量与覆盖说明一致。

### 当前状态

**未开始。**

---

## 阶段 7：CI/CD 与报告归档

### 阶段目标

让框架在代码提交、Pull Request、手动触发和定时任务中自动运行。

### GitHub Actions

建议拆分为：

#### unit-test.yml

触发：

- push；
- pull_request。

执行：

- 安装锁定依赖；
- 运行框架单元测试；
- 生成覆盖率；
- 执行静态检查；
- 上传 JUnit / coverage。

#### api-test.yml

触发：

- 手动触发；
- 测试环境部署完成后；
- 可选定时任务。

执行：

- 选择环境；
- 健康检查；
- smoke / core / regression；
- 生成 Allure 结果；
- 上传 JUnit、日志和 Allure artifact；
- 清理测试数据。

### Jenkins

参数：

```text
ENV = dev / test / stage
LEVEL = smoke / core / regression
GENERATE_AI_ANALYSIS = true / false
```

要求：

- 使用 Jenkins Credentials；
- 不在 Jenkinsfile 中写密码；
- 生成 JUnit XML；
- Allure 插件路径正确；
- 任意测试失败时构建失败；
- 0 用例执行时构建失败；
- 失败日志可下载。

### Docker Compose 升级方案

若短链接 SaaS 支持 Docker Compose：

```text
启动 MySQL
↓
启动 Redis
↓
启动短链接服务
↓
等待健康检查
↓
初始化测试数据
↓
执行 smoke
↓
归档报告
↓
清理环境
```

### 阶段产出

- GitHub Actions workflows；
- Jenkinsfile；
- CI 截图；
- Allure artifact；
- JUnit 结果；
- `docs/08_CI-CD接入说明.md`。

### 验收标准

- push / PR 能运行框架单元测试；
- 手动触发能选择环境和用例层级；
- 失败测试能正确阻断流水线；
- Allure、JUnit 和日志可归档；
- 凭据不泄露；
- 0 用例不会显示绿色成功。

### 当前状态

**未开始。**

---

## 阶段 8：AI 辅助能力

### 阶段目标

在传统接口自动化基础稳定后，增加真实、可控、可解释的 AI 增强能力。

### 8.1 接口文档生成 YAML 用例草稿

输入：

- 接口名称；
- Method；
- Path；
- Header；
- 请求参数类型、必填和限制；
- 响应结构；
- 业务规则；
- 已知错误码。

输出：

- 正常场景；
- 必填为空；
- 类型错误；
- 长度边界；
- 权限场景；
- 业务规则场景；
- 可执行 YAML 草稿。

要求：

- AI 输出必须通过 YAML 解析；
- 必须通过内部 Schema 校验；
- 不符合框架 DSL 的输出拒绝保存；
- 人工审核后才能进入正式用例目录；
- 不自动覆盖已有用例。

### 8.2 失败日志分析

输入：

- 用例名称；
- 脱敏请求；
- 响应；
- 断言差异；
- 提取变量；
- 数据库校验结果；
- 重试信息；
- 服务端 trace_id（若有）。

输出：

- 事实摘要；
- 可能原因；
- 证据与推测区分；
- 排查优先级；
- 建议检查模块；
- 是否可能为测试脚本问题。

### 8.3 安全和可靠性要求

- Token、Cookie、密码、手机号、邮箱、数据库凭据脱敏；
- AI API Key 只从环境变量读取；
- 支持关闭 AI；
- AI 失败不能影响主测试结果生成；
- AI 输出不能替代真实断言；
- AI 分析明确标记为建议，不作为唯一根因；
- 保存模型、Prompt 版本和请求 ID；
- 控制请求长度和成本。

### 阶段产出

- `ai/testcase_generator.py`；
- `ai/failure_analyzer.py`；
- Prompt 模板；
- 输出校验器；
- AI YAML 示例；
- AI 失败分析示例；
- 脱敏测试；
- `docs/09_AI用例生成与失败分析.md`。

### 验收标准

- 可以从结构化接口说明生成可解析 YAML 草稿；
- 非法输出会被拒绝；
- 失败日志发送前完成脱敏；
- AI 不可用时普通测试正常运行；
- README 有真实演示，不夸大为“全自动测试 Agent”。

### 当前状态

**未开始。**

---

## 阶段 9：工程质量、文档、简历和面试材料

### 阶段目标

把项目整理为可维护、可复现、可展示和可讲解的完整作品。

### 工程质量

- 依赖锁定；
- Ruff 或同类静态检查；
- 统一格式；
- 类型提示；
- 单元测试；
- 覆盖率；
- Pre-commit；
- 配置校验；
- 错误码和异常分类；
- 开源许可证说明。

### README 内容

- 项目背景；
- 基线仓库与二次开发说明；
- 已验证能力；
- 未完成能力；
- 技术栈；
- 架构图；
- 目录结构；
- 快速启动；
- 环境配置；
- 执行命令；
- Allure 截图；
- CI 截图；
- AI 示例；
- 安全说明；
- Roadmap。

### 文档清单

```text
docs/01_项目背景与开源基线说明.md
docs/02_基线源码审查报告.md
docs/03_框架执行流程.md
docs/04_YAML用例规范.md
docs/05_上下文变量机制.md
docs/06_断言引擎设计.md
docs/07_短链接业务测试设计.md
docs/08_CI-CD接入说明.md
docs/09_AI用例生成与失败分析.md
docs/10_面试讲解稿.md
```

### 建议截图

- 项目目录；
- smoke 执行；
- Allure 总览；
- 失败用例详情；
- MySQL 校验；
- GitHub Actions；
- Jenkins；
- AI 用例生成；
- AI 失败分析；
- 脱敏前后单元测试结果。

### 阶段产出

- 最终 README；
- 完整 docs；
- 简历描述；
- 面试讲解稿；
- 常见问题回答；
- 演示流程；
- 项目版本标签。

### 验收标准

- 新用户按 README 能运行 Mock 测试；
- 有环境时能运行短链接 smoke；
- 所有简历描述有证据；
- 能讲清基线问题、修复方案、设计取舍和个人贡献；
- 项目中无敏感信息；
- 不把 Demo 或计划能力描述成真实实现。

### 当前状态

**未开始。**

---

## 7. 当前总进度

> V3.1 当前执行编号以本表为准；早期版本保留的后续阶段详细章节只作为历史能力池参考。

| 阶段 | 状态 | 说明 |
|---|---|---|
| 阶段 0：目标和基线确认 | 已完成 | 项目方向、仓库和边界已确定 |
| 阶段 1：基线审查与 P0 修复 | 已完成 | P0、Mock 分层、配置和 JUnit 已验证 |
| 阶段 2：上下文/断言/稳定性 | 已完成 | VariableContext、断言引擎、异常链路与框架测试 |
| 阶段 3：正式架构重构 | 已完成 | `core/ + utils/ + testcases/`，旧正式入口移除 |
| 阶段 4：短链接真实 Happy Path | **已完成** | 用户 Windows 六条真实 Smoke：`6 passed in 9.65s`，含 Redirect/Stats/Cleanup |
| 阶段 4.5：异常/边界真实用例 | **已完成** | 用户 Windows Core 6/6 真实通过，Sentinel 前置限流有界重试已获得真实运行证据 |
| 阶段 5：通用数据源断言 + 真实 SUT 验证 | **已完成** | 用户确认完整 Regression 6/6 真实通过；通用 MySQL/Redis YAML 断言与当前 SUT 深层校验均完成 |
| 阶段 6：CI/CD | **GitHub Actions + Jenkins Mock 已真实通过，真实 SUT Jenkins 验收待完成** | GitHub Actions 公共框架 CI 已连续两次绿色；Jenkins Windows `test/smoke` 已真实 SUCCESS 并生成 JUnit/Artifact；下一步只做真实短链接 SUT 参数化 smoke 验收 |
| 阶段 7：AI 辅助 | 未开始 | 用例草稿生成 + 失败分析 |
| 阶段 8：最终整理 | 未开始 | README、架构图、简历、面试材料 |

### 当前已确认事实

- 基线仓库是教学 / 展示骨架，不能把原始能力整体描述为个人原创；
- Stage 1 已完成阻断缺陷修复和可信运行入口；
- Stage 2 已完成 Mock、VariableContext、断言增强、异常链路与框架测试保障；
- Stage 3 已完成正式 `core/ + utils/ + testcases/` 架构迁移，并删除旧目录入口；
- Stage 3 基线为框架自身 57 条、全量 63 条；当前 Stage 4 Redirect YAML 主链纠正后沙箱框架自身测试为 83 passed、默认离线全量为 89 passed；
- Stage 5 已将 MySQL / Redis 直连能力收敛为通用 `db/` Client + `AssertionEngine` YAML 数据源断言，并由用户确认当前真实 SUT Regression 6/6 通过；Stage 6 GitHub Actions/Jenkins 配置已实现并通过离线契约；GitHub Actions 已获得连续绿色 Run + Artifact 真实平台证据，Jenkins Windows `ENV_NAME=test / LEVEL=smoke` 也已真实 SUCCESS 并成功记录 JUnit/归档 Artifact；当前只剩真实短链接 SUT 的 Jenkins 参数化 smoke 验收；AI 尚未实现；
- Stage 4 已完成真实 SaaS 源码和运行链路分析，确认 Gateway 鉴权、gid 前置、HTTP Host/serverName 对 fullShortUrl 的影响、Redis Stream 最终一致性和 ShardingSphere 边界；
- 已通过手工真实请求定位并验证 `enableStatus` 缺失导致统计 `data:null` 的真实缺陷，同时确认旧 Nginx 构建包与最新 Vue 源码不一致；
- Stage 4 已把登录、分组、创建、分页、302 跳转、异步统计和回收站清理作为真实 SUT 接入框架并获得 `6 passed`；Stage 4.5 Core 已真实 6/6；Stage 5 Regression 已真实 6/6；Stage 6 当前只增加可复用 CI 调度和报告归档，不继续扩张当前 SUT 用例数量。

---

## 8. 更新后的 8 周排期

> 该排期是建议节奏，不以赶进度为目标。若真实短链接环境准备较慢，应优先保证阶段质量。

### 第 1 周：基线复现、P0 修复（已完成）

任务：

- 克隆并固定 commit；
- 记录环境；
- 原始运行；
- 修复 YAML 路径；
- 修复 JSON 请求；
- 修复 Header 覆盖；
- 修复 marker 和依赖；
- 修复配置和报告。

产出：

- 原始错误日志；
- P0 修复提交；
- 基线源码审查报告；
- 第一份可信 Mock Allure 报告。

### 第 2 周：Mock 服务和框架单元测试（已完成）

任务：

- 建立受控 Mock；
- 为 loader、context、request、assertion 编写测试；
- 加入脱敏；
- 验证异常和失败报告；
- 生成覆盖率。

产出：

- `tests/unit/`；
- `mock_server/`；
- 覆盖率报告；
- Mock 端到端报告。

### 第 3 周：重构为自有仓库（已完成）

任务：

- 创建新仓库；
- 迁移稳定代码；
- 重构目录；
- 保留 MIT 许可证；
- 新增第三方说明；
- 编写 README 初版。

产出：

- `ai-api-autotest-framework`；
- 目标架构；
- 可运行基础框架。

### 第 4 周：接入短链接主链路（进行中）

任务：

- 核查真实接口：已完成；
- 配置 `shortlink-local` 真实测试环境：已完成；
- 登录与 token 提取：已编码，待用户本地真实验证；
- 查询分组与 gid 提取：已编码，待用户本地真实验证；
- 创建短链接：下一小版本；
- 分页确认：下一小版本；
- 302 跳转：待实现；
- Redis Stream 异步统计轮询：待实现；
- 数据清理：待实现。

产出：

- 第一条真实端到端链路；
- 真实业务 Allure 报告。

### 第 5 周：MySQL / Redis 和断言增强

任务：

- 实现真实 MySQL；
- 实现真实 Redis；
- 实现数据库和缓存断言；
- 实现 JsonSchema 和耗时断言；
- 补充单元测试。

产出：

- 数据一致性测试；
- 增强版断言引擎；
- 对应设计文档。

### 第 6 周：业务覆盖和 CI/CD

任务：

- 完善 smoke / core / regression；
- 补充权限、统计、异常和安全边界；
- 接入 GitHub Actions；
- 接入 Jenkins；
- 归档 JUnit / Allure。

产出：

- 高质量业务用例集；
- CI 运行证据；
- 报告 artifact。

### 第 7 周：AI 增强

任务：

- 设计 Prompt；
- 生成 YAML 草稿；
- 输出 Schema 校验；
- 失败日志分析；
- 敏感信息脱敏；
- AI 降级机制。

产出：

- AI 用例生成；
- AI 失败分析；
- README 演示。

### 第 8 周：工程质量和求职材料

任务：

- 完善 README 和 docs；
- 依赖锁定；
- 静态检查；
- 整理架构图；
- 准备简历描述；
- 准备面试讲解；
- 录制或截图演示流程。

产出：

- 项目发布版；
- 简历内容；
- 面试材料；
- 演示材料。

---

## 9. 优先级清单

### 已完成基础项（Stage 1～3）

1. 基线 commit 审查与 P0 修复；
2. YAML 路径、JSON 参数、Header 覆盖和 0 用例失败；
3. smoke / core / regression 独立执行；
4. 多环境配置和统一 Runner；
5. 受控 Mock、框架单元/集成测试和 JUnit；
6. 内存 VariableContext 与作用域隔离；
7. 敏感数据脱敏、TLS 可配置、超时/连接失败验证；
8. 统一基础断言引擎；
9. `core/ + utils/ + testcases/` 正式架构迁移；
10. 代码模块说明、第三方许可说明和基础工程元数据。

### P1：当前优先（Stage 4 真实业务接入）

1. 获取真实短链接 SaaS 启动说明和 API 契约；
2. 建立独立测试环境配置与测试账号；
3. 实现真实登录、创建短链、详情查询、跳转、统计主链路；
4. 实现 test_run_id 与测试数据清理；
5. 形成第一份真实业务 JUnit/Allure Results 证据；
6. 补充真实业务异常和边界用例。

### P2：Stage 5～7 工程能力

1. MySQL / Redis 真实校验；
2. JsonSchema 与数据库/缓存断言；
3. 有限制的 HTTP 重试；
4. GitHub Actions；
5. Jenkins 参数化；
6. 真实业务并发与资源隔离验收；
7. 更完整的依赖锁定与静态检查。

### P3：项目亮点（Stage 8～9）

1. AI 生成 YAML 用例草稿；
2. AI 失败日志分析；
3. 权限、统计和安全边界完整矩阵；
4. Docker Compose 一键测试环境（若真实 SaaS 适配）；
5. 最终 README、面试讲解和简历材料。

---

## 10. 当前下一步行动清单

Stage 6 已完成 GitHub Actions 与 Jenkins Mock 两条真实 CI 主链验证，当前只剩真实 SUT Jenkins 参数化验收：

```text
1. GitHub Actions 公共框架 CI：已完成，连续绿色并生成 Artifact
2. Jenkins Pipeline from SCM：已完成
3. Jenkins ENV_NAME=test / LEVEL=smoke：已真实 SUCCESS
4. Jenkins Workspace .venv 隔离与 UTF-8 编码修复：已真实验证生效
5. JUnit 记录与 reports/logs Artifact 归档：已真实验证
6. 下一步准备不进入 GitHub 的私有短链接环境 YAML
7. 使用 Build with Parameters 运行 ENV_NAME=<私有环境名> / LEVEL=smoke
8. 确认 Jenkins 可访问本机真实 Gateway/Project，并保留 JUnit/Artifact 证据
9. 真实 SUT Jenkins smoke 通过后关闭 Stage 6，进入 Stage 7 AI
```

Stage 6 坚持：

- GitHub Actions 公共 workflow 不直接访问开发者本机 SUT；
- Jenkinsfile 不写死当前项目环境名，真实环境通过 `ENV_NAME` 参数选择；
- CI 只调度统一 `run.py`，不复制 suite/marker/报告目录选择逻辑；
- 测试失败后仍保留 JUnit、Allure Results、run.json 与日志；
- 不把 workflow/Jenkinsfile 的离线契约测试写成“GitHub/Jenkins 平台已经真实运行通过”；
- 新项目接入原则上只新增环境 YAML 与 `testcases/<suite>/`，公共 CI 不因业务项目变化而修改。

---

## 11. 风险与约束

### 11.1 开源代码使用

基线仓库采用 MIT License。

要求：

- 保留许可证文本；
- 对实质性复用保留版权和许可声明；
- 在 README 或 `THIRD_PARTY_NOTICES.md` 中说明基线来源；
- 不把开源原始代码全部描述为个人独立原创；
- 重点展示个人完成的审查、修复、重构、真实业务接入和新增功能。

### 11.2 不盲信 README 和注释

代码注释中的“支持”不等于真实能力。

每项能力必须检查：

- 是否有真实代码；
- 是否在执行路径中被调用；
- 是否有测试；
- 是否有报告或 CI 证据；
- 是否存在 Demo / Mock 替代。

### 11.3 不提前重构

必须先理解和修复基线，再迁移目录。

否则容易：

- 混淆原始 Bug 和新 Bug；
- 失去修复前后对比；
- 难以说明个人贡献；
- 产生大量无验证重构。

### 11.4 不混入 UI 自动化

Selenium 和 POM 后续可做独立项目。

当前接口自动化项目只聚焦：

- API；
- 数据；
- 报告；
- CI/CD；
- AI 辅助。

### 11.5 敏感信息

禁止提交或发送：

- 真实 Token；
- Cookie；
- 用户密码；
- 手机号和邮箱；
- 数据库密码；
- Redis 密码；
- 企业内部域名和业务数据；
- AI API Key。

必须使用：

- 环境变量；
- `.env.example`；
- GitHub Secrets；
- Jenkins Credentials；
- 统一脱敏器。

### 11.6 测试环境安全

- 不直接在生产环境执行破坏性测试；
- 删除、禁用、限流等用例必须使用测试数据；
- 数据清理必须限制在本次 `test_run_id`；
- SQL 必须参数化；
- 安全测试必须在合法授权范围内。

### 11.7 AI 风险

- AI 输出可能不符合 DSL；
- AI 可能生成不存在的错误码和字段；
- AI 分析可能把猜测当事实；
- AI 服务可能超时或不可用；
- 日志可能包含敏感信息。

控制措施：

- Schema 校验；
- 人工审核；
- 事实和推测分栏；
- 脱敏；
- 超时和降级；
- AI 不影响主测试结论。

---

## 12. 简历描述管理

### 12.1 当前阶段可使用的描述

Stage 3 已完成后，可以使用以下阶段性描述：

> 基于 Pytest、Requests、YAML 和 Allure 对开源接口自动化骨架进行源码审查与二次重构，修复 YAML 路径、JSON 参数、请求头覆盖、跨用例依赖、配置和报告输出等问题；设计内存 VariableContext 替代共享文件状态，完善统一断言、异常链路和敏感数据脱敏，并将基线遗留的 base/common/testcase 重构为 core/utils/testcases 正式架构。当前框架自身 57 条测试、全量 63 条测试通过，核心源码覆盖率 79%，smoke/core/regression 可独立执行。

当前这段描述**不包含**真实短链接、MySQL、Redis、CI/CD 或 AI，因为这些仍未进入已验证状态。

### 12.2 暂时不能使用的描述

在功能未验证前，不得写：

- 已实现 MySQL 数据库校验；
- 已实现 Redis 缓存校验；
- 已支持稳定并发执行；
- 已完成 CI/CD；
- 已完成 AI 自动生成用例；
- 已覆盖 50 条真实业务用例；
- 已接入真实短链接系统。

### 12.3 最终目标描述

项目完成并有证据后，可使用：

> 基于 Pytest、Requests、YAML 和 Allure 设计并实现接口自动化测试框架，接入自研短链接 SaaS，覆盖认证、短链接管理、跳转、统计和权限等核心链路；设计作用域隔离的上下文变量机制和统一断言引擎，实现 MySQL / Redis 数据一致性校验、GitHub Actions / Jenkins 分层回归，并引入大模型生成 YAML 用例草稿和分析失败日志。

---

## 13. 面试讲解主线

面试时按以下顺序讲：

```text
1. 为什么做这个项目
2. 为什么选择该开源仓库
3. 为什么没有直接 Fork 后写简历
4. 源码审查发现了哪些真实问题
5. 哪些问题会导致用例不执行或结果失真
6. 如何建立 Mock 服务区分框架 Bug 和业务 Bug
7. 如何重构请求、上下文和断言模块
8. 如何接入短链接 SaaS
9. 如何做数据库、缓存和统计一致性验证
10. 如何做分层回归和 CI/CD
11. AI 功能为什么是辅助而不是替代断言
12. 个人贡献和开源基线的边界
```

重点亮点不是“用了很多工具”，而是：

- 能审查代码；
- 能发现隐蔽缺陷；
- 能设计修复方案；
- 能为框架本身建立测试；
- 能接入真实业务；
- 能将能力工程化和可验证化。

---

## 14. 最终交付物

### 代码

- 自有 GitHub 仓库；
- 框架核心代码；
- Mock 服务；
- 单元测试；
- 短链接业务用例；
- MySQL / Redis；
- CI/CD；
- AI 模块。

### 报告

- 单元测试报告；
- 覆盖率报告；
- Mock Allure；
- 短链接 Allure；
- JUnit；
- CI artifact。

### 文档

- 项目背景；
- 基线审查；
- 架构设计；
- YAML 规范；
- 上下文设计；
- 断言设计；
- 业务测试设计；
- CI/CD；
- AI 设计；
- 面试讲解。

### 求职材料

- 简历项目描述；
- 项目亮点；
- 个人职责；
- 面试问答；
- 演示截图或视频。

---

## 15. 最终验收标准

项目只有同时满足以下要求，才视为完成：

### 15.1 可运行

- 新环境按 README 可以运行 Mock 测试；
- 有测试环境时可以运行短链接 smoke；
- 依赖版本可复现；
- 退出码正确；
- 0 用例执行会失败。

### 15.2 可验证

- 核心模块有单元测试；
- 框架改动有回归测试；
- Allure 和 JUnit 可生成；
- CI 有真实成功和失败记录；
- MySQL / Redis 不是 Demo；
- AI 输出有校验和人工审核。

### 15.3 可维护

- 目录职责清晰；
- 配置统一；
- 上下文隔离；
- SQL 参数化；
- 日志脱敏；
- 数据可清理；
- 开源许可合规。

### 15.4 可展示

- README 能解释项目价值；
- 有架构图；
- 有真实报告；
- 有 CI 截图；
- 有 AI 示例；
- 能区分基线代码与个人贡献。

### 15.5 可用于求职

- 简历只写已验证能力；
- 能讲清发现的问题和修复过程；
- 能解释设计取舍；
- 能说明真实业务覆盖；
- 能展示失败排查过程；
- 不夸大、不伪造、不把 Demo 当真实实现。

---

## 16. 当前移交摘要

```text
项目名称：AI 辅助接口自动化测试框架
目标方向：测试开发求职项目
真实被测系统：用户本地短链接 SaaS
基线仓库：zed123214/api-autotest-framework
基线许可证：MIT License
当前核查 commit：e0ac76720265609d63249fed630016821659b679

已完成：
- Stage 0～3：基线审查/P0 修复、VariableContext/断言、正式架构重构
- Stage 4：真实 Happy Path，用户 Windows 6 passed in 9.65s
- Stage 4.5：6 条 Core 已由用户 Windows 真实验证为 6/6，Sentinel 前置限流有界重试已通过真实运行
- 登录凭据：当前 SUT 已迁移到 env.shortlink-local.yaml，不再要求终端 export；这是通用 `${config(section,key)}` 的真实使用示例
- Stage 5：通用 MySQL/Redis Client、YAML 数据源断言、YAML marker/poll、环境 suite 选择已实现并由用户确认真实 Regression 6/6 通过
- Stage 6：GitHub Actions 已真实绿色；Jenkins Build #10 已真实完成 SCM → .venv → Mock smoke 2/2 → JUnit → Artifacts；V3.2.6 已实现通用外部环境 YAML 覆盖，真实 SUT Jenkins smoke 待最终执行

当前真实证据边界：
- Stage 4：已真实通过
- Stage 4.5：用户 Windows 真实 Core 6/6，已完成
- Stage 5：用户确认完整 Regression 6/6 已真实通过，已完成
- Stage 6：GitHub Actions 与 Jenkins Mock Pipeline 均已真实验收；外部私有环境 YAML 机制已通过代码/契约验证；真实 SUT Jenkins smoke 待验收

下一路线：
Stage 6 真实 SUT Jenkins smoke -> Stage 7 AI -> Stage 8 项目/简历/面试收尾
```

---

**文档状态：V3.2.3。项目定位保持“AI 辅助接口自动化测试框架”，短链接仅为当前真实 SUT。Stage 4/4.5/5 已完成真实验收；Stage 6 的 GitHub Actions 已连续获得绿色 Run + Artifact 真实平台证据。Jenkins 已真实完成 SCM/Jenkinsfile 获取与代码 Checkout，当前针对 Windows Service 的 UTF-8 编码和 Python 环境隔离问题完成 Jenkinsfile 定向修复，待重新 Build 验证 Mock Pipeline 后继续真实 SUT 验收。**

---

## V3.2.5 状态更新（2026-08-18）

### Stage 6 Jenkins 本地 CI 验收：已完成 Mock 主链
本次已通过 Jenkins 页面截图与真实构建日志完成以下验收：

- **参数化入口已生效**：`ENV_NAME` 为自由字符串，`LEVEL` 可选择 `smoke / core / regression`。
- **JUnit 可视化结果已生效**：Build #10 的 `testcases.demo` 显示 2 passed、0 failed、0 skipped。
- **Artifacts 归档已生效**：Build #10 可查看 `logs/` 与 `reports/runs/jenkins-10/`。
- **真实 Jenkins Pipeline 主链已成功**：
  GitHub SCM → Checkout → Workspace `.venv` → 安装依赖 → `run.py --env test --level smoke` → Mock Smoke → JUnit → Artifacts → `SUCCESS`。
- **Python/Windows 编码问题已解决**：Jenkins 使用 Workspace 独立 `.venv`，Pipeline 内启用 Python UTF-8 Mode，避免 CP936/GBK 解码冲突。
- **当前 Jenkins Mock 验收结果**：2 passed，4 deselected。

### Stage 6 当前剩余任务
下一步仅剩 **真实 SUT 的 Jenkins 参数化验收**。为避免将本地账号、数据库密码等信息提交到公共 GitHub，采用以下原则：

1. 公共仓库继续保留安全占位配置，不提交真实凭据。
2. Jenkins 本机维护一个 **Git 仓库外的私有环境 YAML**，仍保持“凭据直接在本地 YAML 编辑”的使用习惯。
3. Pipeline 仅提供通用的“可选本地环境配置文件注入”能力，不写死 shortlink 业务概念。
4. Jenkins 不复制私有 YAML；仅把仓库外文件路径临时注入 `API_TEST_ENV_FILE`，由 ConfigManager 直接读取并递归覆盖公开命名环境。
5. 先执行真实 SUT `smoke`，通过后再评估是否需要 `core/regression` 的 Jenkins 验收。

### Stage 6 状态
- GitHub Actions 公共 CI：**已完成并真实通过**
- Jenkins Mock CI：**已完成并真实通过**
- Jenkins 参数化/JUnit/Artifacts：**已完成并真实通过**
- Jenkins 真实 SUT Smoke：**待执行**

---

## V3.2.6 状态更新（2026-08-18）

### 1. 外部私有环境 YAML 能力已实现

本版本把“真实凭据如何进入 Jenkins”收敛成框架级通用能力，而不是短链接专用脚本。稳定优先级为：

```text
CLI > env vars > external env YAML > env.<name>.yaml > config.yaml
```

### 2. 框架边界

- `core/config_manager.py` 新增可选外部 YAML 覆盖层，不理解任何具体 SUT 字段。
- `run.py` 新增 `--env-file`，同时支持 `API_TEST_ENV_FILE`；参数只传文件路径，不传真实密码值。
- Pytest collection hooks 与 fixtures 在同一运行期间读取同一个外部文件，避免 Runner/collection 配置分裂。
- 显式文件不存在时 fail-fast，不静默使用公开 YAML 的 `CHANGE_ME`。
- `Jenkinsfile` 新增通用 `ENV_FILE` 参数，只把路径临时注入测试进程，不复制私有 YAML 到 Workspace，也不归档其内容。
- CI 契约继续禁止当前 SUT 业务 token 出现在公共 Pipeline。

### 3. 真实项目作为可公开参考

当前真实项目继续位于 Project Adapter/Test Cases 层：

```text
config/env.shortlink-local.yaml
testcases/shortlink/
docs/examples/env.shortlink-local.override.example.yaml
```

这些内容可以上传 GitHub 作为“真实项目如何接入框架”的参考；真实登录密码、MySQL 密码等只填写在仓库外副本中。以后接入其他项目时沿用同一模式，不修改框架核心。

### 4. 当前 Stage 6 验收状态

- GitHub Actions 公共 CI：**已真实通过**
- Jenkins Mock CI：**Build #10 已真实 SUCCESS（2 passed / 4 deselected）**
- Jenkins 参数化/JUnit/Artifacts：**已真实通过**
- 外部私有环境 YAML：**代码与自动化契约已实现，待用户本机 Jenkins 使用真实文件验证**
- Jenkins 真实 SUT Smoke：**待执行**

### 5. 下一步

```text
ENV_NAME = <真实项目环境名>
LEVEL    = smoke
ENV_FILE = <仓库外私有覆盖 YAML 路径>
```

完成真实 SUT Jenkins smoke。通过后 Stage 6 平台验收即可收口，进入 Stage 7 AI。

---

## V3.2.7 状态更新（2026-08-18）

### Stage 6 外部环境配置能力：Jenkins Mock 回归验证通过
在引入通用 `ENV_FILE` / 外部环境 YAML 覆盖能力后，已在真实 Jenkins Windows Agent 上重新执行公共 Mock Smoke，结果为：

- GitHub SCM Checkout：成功
- Workspace 独立 `.venv` 创建：成功
- Python 3.12.3 + 依赖安装：成功
- `run.py --env test --level smoke --run-id jenkins-17`：成功
- Pytest 结果：`2 passed, 4 deselected`
- JUnit：成功生成并由 Jenkins 记录
- Artifacts：成功归档
- Pipeline 最终状态：`SUCCESS`

该次构建中 `ENV_FILE` 保持为空，因此验证的是**向后兼容性**：新增外部私有 YAML 能力后，原有公共 Mock / Demo 流程不受影响。

### Stage 6 当前剩余验收
下一步执行真实 SUT 的 Jenkins Smoke：

1. 在 Jenkins Agent 仓库外建立私有配置文件，例如：
   `C:\ProgramData\Jenkins\.jenkins\private-configs\shortlink-local.override.yaml`
2. 私有文件只覆盖需要保密或机器相关的字段，不复制整个公共环境 YAML。
3. Jenkins 参数：
   - `ENV_NAME=shortlink-local`
   - `LEVEL=smoke`
   - `ENV_FILE=C:\ProgramData\Jenkins\.jenkins\private-configs\shortlink-local.override.yaml`
4. 启动真实短链接 SUT 后执行。
5. 通过后再决定是否在 Jenkins 中继续执行 `core` / `regression`。

### 架构约束继续保持
- Jenkinsfile / Framework Core 不出现短链接业务硬编码。
- Shortlink 仅作为 `Project Adapter + Test Cases + public env example`。
- 未来接入订单、支付、用户中心等项目时复用相同 `ENV_NAME / LEVEL / ENV_FILE` 机制。
- 真实私有 YAML 永远位于 Git 仓库外，不上传 GitHub，不进入 Jenkins Artifacts。

---

## V3.2.8 状态更新（2026-08-18）

### Stage 6 Jenkins 真实 SUT Smoke：已到达真实业务认证，当前阻塞于测试账号/数据匹配
Jenkins Build #18 已验证以下链路真实可达：

- GitHub SCM Checkout：成功
- Jenkins Workspace `.venv`：成功
- 依赖安装：成功
- `ENV_NAME=shortlink-local`：成功选择短链接 Project Adapter
- 外部 `ENV_FILE` 分支：已进入，Jenkins 对仓库外文件执行存在性检查并通过 `withEnv` 注入路径
- Pytest：收集 18 条，按 smoke 选择 6 条
- Gateway：真实请求已到达 `127.0.0.1:8000`
- Admin 服务：登录请求已进入真实后端并执行 ShardingSphere 用户查询

当前业务响应为“用户不存在”，因此首条登录 Smoke 失败，另外 5 条依赖认证 fixture 的 Smoke 在 setup 阶段连锁报错。当前证据不支持修改 Framework Core；优先排查仓库外私有 YAML 中的应用登录账号密码与当前后端数据库用户数据是否一致。

### 下一步排查顺序
1. 明确区分私有 YAML 中的“短链接应用登录密码”和“MySQL 数据库连接密码”，二者用途不同。
2. 在当前后端实际连接的数据源中，仅按用户名检查测试账号是否存在、`del_flag` 是否为 0。
3. 若账号存在，核对私有 YAML 的应用登录密码是否与该账号当前密码一致。
4. 若账号不存在，确认当前后端是否连接到了与此前本地 Smoke 成功时相同的数据库/数据集，并检查 ShardingSphere 物理分片中的账号数据。
5. 修正环境/测试数据后直接重跑 Jenkins `shortlink-local + smoke`；当前不修改 Jenkinsfile、ConfigManager、ApiRunner 或 AssertionEngine。

### 架构结论
当前失败属于真实 SUT 环境/测试数据层面的业务认证阻塞。框架已正确完成项目选择、外部配置注入、用例收集、真实 HTTP 调用与断言失败报告。

---

## V3.2.9 状态更新（2026-08-18）

### Jenkins 当前构建报告隔离修复
真实 Jenkins Build #19 暴露出一个通用 CI 问题：本次实际执行的是 `ENV_NAME=test`、`LEVEL=smoke`，Pytest 结果为 `2 passed, 4 deselected`，但 Jenkins 最终状态为 `UNSTABLE`。

根因不是本次测试失败，而是 Jenkins Workspace 会跨构建保留文件，旧 Jenkinsfile 的 `post` 使用递归通配符读取 `reports/runs/**/junit.xml`。因此上一轮 Build #18 的失败 JUnit 与 Build #19 的成功 JUnit 被同时交给 Jenkins JUnit 插件，历史失败污染了当前构建状态。

V3.2.9 将 Jenkins 报告消费范围收紧为当前构建：

- JUnit：`reports/runs/jenkins-${BUILD_NUMBER}/junit.xml`
- Reports Artifact：`reports/runs/jenkins-${BUILD_NUMBER}/**`
- Logs：继续归档 `logs/**/*`

同时新增 CI 契约测试，禁止未来重新引入跨 Build 的 JUnit 全目录通配符。该修复是纯框架/CI 能力，不包含任何短链接 SUT 业务硬编码。

### Build #19 另一个重要结论
Build #19 并不是对真实短链接环境的重试。日志中的实际命令为 `run.py --env "test" --level "smoke" --run-id "jenkins-19"`，因此它只验证 Demo/Mock 2 条 Smoke。下一次真实 SUT 验收仍需明确选择：

- `ENV_NAME=shortlink-local`
- `LEVEL=smoke`
- `ENV_FILE=<Jenkins Agent 仓库外私有覆盖 YAML>`

在 V3.2.9 Jenkins 报告隔离修复推送并经过 Mock 构建验证后，再继续真实 SUT Smoke，避免旧失败报告干扰当前 Jenkins 状态判断。

