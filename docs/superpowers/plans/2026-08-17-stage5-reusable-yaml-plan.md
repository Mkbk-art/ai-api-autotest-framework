# Stage 5 Reusable YAML Data Validation Implementation Plan

**Goal:** 把 Stage 5 从短链接专用 Probe 重构为可复用的 YAML MySQL/Redis 断言能力，并把短链接 Case 按业务域收敛。

**Architecture:** 通用数据源客户端放入 `db/`；`Assertions` 负责通用 DB/Redis 规则；`ApiRunner` 在响应提取后解析断言；短链接分片表名/Key 只在项目适配层生成并写入 VariableContext；YAML 声明 level/tags/workflow。

**Tech Stack:** Python 3.11, Pytest, Requests, PyYAML, PyMySQL, redis-py.

## Global Constraints
- core/db/utils 不得出现短链接业务常量。
- Python/YAML 新增或修改保持高密度中文注释。
- MySQL 只允许 SELECT；业务数据写操作继续通过真实 API。
- 保留 6 smoke + 6 core + 6 regression 的真实测试分层。
- 不再依赖 SHORTLINK_TEST_USERNAME/PASSWORD 环境变量。

### Task 1: 通用数据源客户端
- [x] 新增 `db/mysql_client.py`、`db/redis_client.py`。
- [x] 用离线 fake driver 单元测试锁定配置、只读 SQL、通用读取接口。

### Task 2: YAML 数据源断言
- [x] 扩展 `core/assertion_engine.py` 支持 DB/Redis 规则。
- [x] 修改 `ApiRunner` 在 extract 之后再解析 validation，并增加独立 `validate()`。
- [x] 用 Fake MySQL/Redis Client 做红绿测试。

### Task 3: YAML 元数据驱动 Pytest marks / suite collection
- [x] 扩展 `core/case_loader.py`：`level`/`tags` 转为 pytest.param marks；支持按 workflow 过滤。
- [x] 根 `conftest.py` 从 YAML 动态注册业务 marker，`pytest.ini` 不再维护具体 SUT 标签。
- [x] 环境 YAML 通过 `test_selection.include_suites` 选择当前项目 suite，公共 collection hook 不写死项目/环境名称。
- [x] 单元/集成测试验证 marker/id/filter 与环境 suite 隔离。

### Task 4: 短链接适配边界
- [x] 删除 `testcases/shortlink/infrastructure.py`。
- [x] 通用 HashMod 放 `utils/sharding.py`。
- [x] 短链接 support 只依据环境 YAML 生成物理表名/Redis Key，并写入 VariableContext。

### Task 5: 用例文件收敛
- [x] 合并为 `testcases/shortlink/` 下 4 个 Python + `yaml/` 下 4 个 YAML。
- [x] 保持 18 Test Item 与 6/6/6 分层。
- [x] Stage 5 DB/Redis 断言迁移到 YAML。

### Task 6: 文档、回归、打包
- [x] 更新 README、项目计划、Stage 5 文档。
- [x] framework/default/collection/compileall/fresh-zip 全量验证。
