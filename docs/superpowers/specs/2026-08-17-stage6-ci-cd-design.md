# Stage 6 CI/CD 与报告归档设计

## 1. 目标

Stage 6 的目标不是把当前短链接 SaaS 写死进 CI，而是让 **AI 辅助接口自动化测试框架**具备可复用的持续集成能力：

- GitHub Actions 在云端验证框架自身、Mock/Demo 套件和静态质量；
- Jenkins 在用户可访问真实 SUT 的执行节点上，通过框架统一 `run.py` 参数运行任意项目环境；
- JUnit、Allure Results、run.json 与日志作为测试证据归档；
- CI 层只负责调度，不重新实现环境选择、层级选择或业务请求逻辑。

## 2. 架构边界

### 2.1 GitHub Actions：公共框架 CI

GitHub 托管 Runner 无法访问用户 Windows 本机的 `127.0.0.1` 服务，因此公共 workflow 不直接运行 `shortlink-local`。它只执行不依赖真实业务系统的能力：

1. 安装锁定后的开发依赖；
2. 执行 `tests/` 框架测试；
3. 通过 `python run.py --env test --level smoke` 执行 Mock/Demo 主链；
4. 执行 `compileall`；
5. 无论成功失败都上传 JUnit / Allure Results / run.json 等 CI 产物。

公共 workflow 不出现短链接业务 URL、Redis Key、表名或 `shortlink-local`。

### 2.2 Jenkins：真实环境执行入口

Jenkins 可以部署在用户本机或能访问目标测试环境的节点。Jenkinsfile 只提供两个业务无关参数：

- `ENV_NAME`：环境配置名称，默认 `test`；
- `LEVEL`：`smoke/core/regression`。

流水线最终只调用：

```text
python run.py --env <ENV_NAME> --level <LEVEL>
```

所以以后接入订单、支付等新项目，只需要新增对应环境 YAML 与 testcase suite，不修改 Jenkinsfile。

## 3. 报告与 Artifact

Stage 6 统一保留：

- JUnit XML：CI 平台识别通过/失败数量；
- Allure Results：供后续生成/展示详细报告；
- `run.json`：记录本次环境、层级、pytest 参数和退出码；
- 日志：在失败时辅助定位。

GitHub Actions 使用 artifact 上传；Jenkins 使用 `junit` 与 `archiveArtifacts`。Jenkins 不强依赖 Allure 插件，先归档原始 Allure Results，避免 CI 能力绑定可选插件。

## 4. 可复用约束

1. `.github/workflows/api-test.yml` 不允许出现当前 SUT 业务词汇；
2. `Jenkinsfile` 不写死任何具体项目环境；
3. CI 不直接拼接 pytest 的业务 suite 选择逻辑，业务执行统一走 `run.py`；
4. CI 只消费 `requirements-dev.txt + constraints.txt`，避免本地/CI 依赖漂移；
5. 测试失败时仍然归档已有报告和日志；
6. 新增/修改 YAML 继续使用高密度中文注释。

## 5. 验收标准

- CI 契约测试可离线验证 workflow/Jenkinsfile 的关键结构；
- framework tests 与默认 Mock 全量保持通过；
- GitHub workflow 能在托管 Runner 上独立执行框架测试和 Demo smoke；
- Jenkinsfile 可参数化选择环境和层级，并在 Windows/Linux Agent 上调用统一 Runner；
- 产物归档配置在失败时仍执行；
- 公共 CI 配置不包含短链接业务硬编码。
