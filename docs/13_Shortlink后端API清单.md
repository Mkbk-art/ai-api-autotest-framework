# Shortlink 后端接口清单（Stage 5 Contract 输入）

> 来源：用户此前提供的 Shortlink 后端源码 ZIP。  
> 提取方式：一次性人工/AI 辅助源码核查，不在 Framework Core 中实现 Spring/Java 源码解析器。  
> 用途：作为 `Static Contract Manifest` 的真实输入样例，并用于后续 Coverage Index / Contract Diff。  
> 当前清单共识别 **43 个映射入口**：External API surface 27 个、Project 内部 API 15 个、页面路由 1 个。

## 1. 为什么分层统计

Shortlink 的 Admin 层很多接口会继续调用 Project 内部 `/api/short-link/v1/**` 接口。
如果把 Admin 和 Project 的镜像接口全部当成“用户可见 API”直接计算 Coverage Gap，会重复计数并夸大未覆盖率。

因此 V1 建议保留全部源码入口，但区分：

- `external_gateway`：经 Gateway/Admin 暴露给 API 使用者；
- `external_direct`：直接面向短域名访问者，例如短链跳转；
- `internal_service`：Admin/Feign 等服务内部调用的 Project API；
- `page_internal`：页面/错误页路由，不作为默认 API Coverage 分母。

默认 API Coverage Scope：
`external_gateway + external_direct`。

## 2. External API Surface（27）

| # | Operation ID | Method | Path | 说明 | Request | Response |
|---:|---|---|---|---|---|---|
| 1 | `shortlinkGroupCreate` | `POST` | `/api/short-link/admin/v1/group` | 新增短链接分组 | `ShortLinkGroupSaveReqDTO` | `Result<Void>` |
| 2 | `shortlinkGroupList` | `GET` | `/api/short-link/admin/v1/group` | 查询短链接分组集合 | `-` | `Result<List<ShortLinkGroupRespDTO>>` |
| 3 | `shortlinkGroupUpdate` | `PUT` | `/api/short-link/admin/v1/group` | 修改短链接分组名称 | `ShortLinkGroupUpdateReqDTO` | `Result<Void>` |
| 4 | `shortlinkGroupDelete` | `DELETE` | `/api/short-link/admin/v1/group` | 删除短链接分组 | `query: gid` | `Result<Void>` |
| 5 | `shortlinkGroupSort` | `POST` | `/api/short-link/admin/v1/group/sort` | 排序短链接分组 | `List<ShortLinkGroupSortReqDTO>` | `Result<Void>` |
| 6 | `shortlinkRecycleSave` | `POST` | `/api/short-link/admin/v1/recycle-bin/save` | 保存到回收站 | `RecycleBinSaveReqDTO` | `Result<Void>` |
| 7 | `shortlinkRecyclePage` | `GET` | `/api/short-link/admin/v1/recycle-bin/page` | 分页查询回收站短链接 | `ShortLinkRecycleBinPageReqDTO` | `Result<Page<ShortLinkPageRespDTO>>` |
| 8 | `shortlinkRecycleRecover` | `POST` | `/api/short-link/admin/v1/recycle-bin/recover` | 恢复短链接 | `RecycleBinRecoverReqDTO` | `Result<Void>` |
| 9 | `shortlinkRecycleRemove` | `POST` | `/api/short-link/admin/v1/recycle-bin/remove` | 移除回收站短链接 | `RecycleBinRemoveReqDTO` | `Result<Void>` |
| 10 | `shortlinkCreate` | `POST` | `/api/short-link/admin/v1/create` | 创建短链接 | `ShortLinkCreateReqDTO` | `Result<ShortLinkCreateRespDTO>` |
| 11 | `shortlinkBatchCreate` | `POST` | `/api/short-link/admin/v1/create/batch` | 批量创建短链接 | `ShortLinkBatchCreateReqDTO` | `void` |
| 12 | `shortlinkUpdate` | `POST` | `/api/short-link/admin/v1/update` | 修改短链接 | `ShortLinkUpdateReqDTO` | `Result<Void>` |
| 13 | `shortlinkPage` | `GET` | `/api/short-link/admin/v1/page` | 分页查询短链接 | `ShortLinkPageReqDTO` | `Result<Page<ShortLinkPageRespDTO>>` |
| 14 | `shortlinkStats` | `GET` | `/api/short-link/admin/v1/stats` | 查询单短链指定时间监控数据 | `ShortLinkStatsReqDTO` | `Result<ShortLinkStatsRespDTO>` |
| 15 | `shortlinkStatsGroup` | `GET` | `/api/short-link/admin/v1/stats/group` | 查询分组监控数据 | `ShortLinkGroupStatsReqDTO` | `Result<ShortLinkStatsRespDTO>` |
| 16 | `shortlinkStatsAccessRecord` | `GET` | `/api/short-link/admin/v1/stats/access-record` | 分页查询单短链访问记录 | `ShortLinkStatsAccessRecordReqDTO` | `Result<Page<ShortLinkStatsAccessRecordRespDTO>>` |
| 17 | `shortlinkStatsGroupAccessRecord` | `GET` | `/api/short-link/admin/v1/stats/access-record/group` | 分页查询分组访问记录 | `ShortLinkGroupStatsAccessRecordReqDTO` | `Result<Page<ShortLinkStatsAccessRecordRespDTO>>` |
| 18 | `shortlinkUrlTitle` | `GET` | `/api/short-link/admin/v1/title` | 根据 URL 获取网站标题 | `query: url` | `Result<String>` |
| 19 | `shortlinkUserGet` | `GET` | `/api/short-link/admin/v1/user/{username}` | 查询用户信息 | `path: username` | `Result<UserRespDTO>` |
| 20 | `shortlinkUserGetActual` | `GET` | `/api/short-link/admin/v1/actual/user/{username}` | 查询无脱敏用户信息 | `path: username` | `Result<UserActualRespDTO>` |
| 21 | `shortlinkUserHasUsername` | `GET` | `/api/short-link/admin/v1/user/has-username` | 查询用户名是否存在 | `query: username` | `Result<Boolean>` |
| 22 | `shortlinkUserRegister` | `POST` | `/api/short-link/admin/v1/user` | 注册用户 | `UserRegisterReqDTO` | `Result<Void>` |
| 23 | `shortlinkUserUpdate` | `PUT` | `/api/short-link/admin/v1/user` | 修改用户 | `UserUpdateReqDTO` | `Result<Void>` |
| 24 | `shortlinkUserLogin` | `POST` | `/api/short-link/admin/v1/user/login` | 用户登录 | `UserLoginReqDTO` | `Result<UserLoginRespDTO>` |
| 25 | `shortlinkUserCheckLogin` | `GET` | `/api/short-link/admin/v1/user/check-login` | 检查用户登录状态 | `query: username, token` | `Result<Boolean>` |
| 26 | `shortlinkUserLogout` | `DELETE` | `/api/short-link/admin/v1/user/logout` | 用户退出登录 | `query: username, token` | `Result<Void>` |
| 27 | `shortlinkRedirect` | `GET` | `/{short-uri}` | 短链接跳转 | `path: short-uri` | `HTTP redirect` |

## 3. Project Internal Service Surface（15）

| # | Operation ID | Method | Path | 说明 | Request | Response |
|---:|---|---|---|---|---|---|
| 1 | `projectShortlinkRecycleSave` | `POST` | `/api/short-link/v1/recycle-bin/save` | Project 保存到回收站 | `RecycleBinSaveReqDTO` | `Result<Void>` |
| 2 | `projectShortlinkRecyclePage` | `GET` | `/api/short-link/v1/recycle-bin/page` | Project 分页查询回收站 | `ShortLinkRecycleBinPageReqDTO` | `Result<Page<ShortLinkPageRespDTO>>` |
| 3 | `projectShortlinkRecycleRecover` | `POST` | `/api/short-link/v1/recycle-bin/recover` | Project 恢复短链接 | `RecycleBinRecoverReqDTO` | `Result<Void>` |
| 4 | `projectShortlinkRecycleRemove` | `POST` | `/api/short-link/v1/recycle-bin/remove` | Project 移除回收站短链接 | `RecycleBinRemoveReqDTO` | `Result<Void>` |
| 5 | `projectShortlinkCreate` | `POST` | `/api/short-link/v1/create` | Project 创建短链接 | `ShortLinkCreateReqDTO` | `Result<ShortLinkCreateRespDTO>` |
| 6 | `projectShortlinkCreateByLock` | `POST` | `/api/short-link/v1/create/by-lock` | Project 通过分布式锁创建短链接 | `ShortLinkCreateReqDTO` | `Result<ShortLinkCreateRespDTO>` |
| 7 | `projectShortlinkBatchCreate` | `POST` | `/api/short-link/v1/create/batch` | Project 批量创建短链接 | `ShortLinkBatchCreateReqDTO` | `void` |
| 8 | `projectShortlinkUpdate` | `POST` | `/api/short-link/v1/update` | Project 修改短链接 | `ShortLinkUpdateReqDTO` | `Result<Void>` |
| 9 | `projectShortlinkPage` | `GET` | `/api/short-link/v1/page` | Project 分页查询短链接 | `ShortLinkPageReqDTO` | `Result<Page<ShortLinkPageRespDTO>>` |
| 10 | `projectShortlinkCount` | `GET` | `/api/short-link/v1/count` | Project 查询分组短链接数量 | `query: requestParam(List<String>)` | `Result<List<GroupShortLinkCountQueryRespDTO>>` |
| 11 | `projectShortlinkStats` | `GET` | `/api/short-link/v1/stats` | Project 单短链监控数据 | `ShortLinkStatsReqDTO` | `Result<ShortLinkStatsRespDTO>` |
| 12 | `projectShortlinkStatsGroup` | `GET` | `/api/short-link/v1/stats/group` | Project 分组监控数据 | `ShortLinkGroupStatsReqDTO` | `Result<ShortLinkStatsRespDTO>` |
| 13 | `projectShortlinkStatsAccessRecord` | `GET` | `/api/short-link/v1/stats/access-record` | Project 单短链访问记录 | `ShortLinkStatsAccessRecordReqDTO` | `Result<Page<ShortLinkStatsAccessRecordRespDTO>>` |
| 14 | `projectShortlinkStatsGroupAccessRecord` | `GET` | `/api/short-link/v1/stats/access-record/group` | Project 分组访问记录 | `ShortLinkGroupStatsAccessRecordReqDTO` | `Result<Page<ShortLinkStatsAccessRecordRespDTO>>` |
| 15 | `projectShortlinkUrlTitle` | `GET` | `/api/short-link/v1/title` | Project 根据 URL 获取网站标题 | `query: url` | `Result<String>` |

## 4. 页面路由（不进入默认 API Coverage 分母）

| # | Operation ID | Method | Path | 说明 | Request | Response |
|---:|---|---|---|---|---|---|
| 1 | `shortlinkNotfoundPage` | `REQUEST` | `/page/notfound` | 短链接不存在页面 | `-` | `String / page` |

## 5. 主要 DTO 字段


### `UserLoginReqDTO`

- `username: string`
- `password: string`

### `UserLoginRespDTO`

- `token: string`

### `UserRegisterReqDTO`

- `username: string`
- `password: string`
- `realName: string`
- `phone: string`
- `mail: string`

### `UserUpdateReqDTO`

- `username: string`
- `password: string`
- `realName: string`
- `phone: string`
- `mail: string`

### `ShortLinkGroupSaveReqDTO`

- `name: string`

### `ShortLinkGroupUpdateReqDTO`

- `gid: string`
- `name: string`

### `ShortLinkGroupSortReqDTO`

- `gid: string`
- `sortOrder: integer`

### `RecycleBinSaveReqDTO`

- `gid: string`
- `fullShortUrl: string`

### `RecycleBinRecoverReqDTO`

- `gid: string`
- `fullShortUrl: string`

### `RecycleBinRemoveReqDTO`

- `gid: string`
- `fullShortUrl: string`

### `ShortLinkCreateReqDTO`

- `domain: string`
- `originUrl: string`
- `gid: string`
- `createdType: integer`
- `validDateType: integer`
- `validDate: datetime`
- `describe: string`

### `ShortLinkBatchCreateReqDTO`

- `originUrls: list[string]`
- `describes: list[string]`
- `gid: string`
- `createdType: integer`
- `validDateType: integer`
- `validDate: datetime`

### `ShortLinkUpdateReqDTO`

- `originUrl: string`
- `fullShortUrl: string`
- `originGid: string`
- `gid: string`
- `validDateType: integer`
- `validDate: datetime`
- `describe: string`

### `ShortLinkPageReqDTO`

- `gid: string`
- `orderTag: string`
- `pagination: current/size (inherited)`

### `ShortLinkRecycleBinPageReqDTO`

- `gidList: list[string]`
- `pagination: current/size (inherited)`

### `ShortLinkStatsReqDTO`

- `fullShortUrl: string`
- `gid: string`
- `startDate: string`
- `endDate: string`
- `enableStatus: integer`

### `ShortLinkGroupStatsReqDTO`

- `gid: string`
- `startDate: string`
- `endDate: string`

### `ShortLinkStatsAccessRecordReqDTO`

- `fullShortUrl: string`
- `gid: string`
- `startDate: string`
- `endDate: string`
- `enableStatus: integer`
- `pagination: current/size (inherited)`

### `ShortLinkGroupStatsAccessRecordReqDTO`

- `gid: string`
- `startDate: string`
- `endDate: string`
- `pagination: current/size (inherited)`

### `ShortLinkCreateRespDTO`

- `gid: string`
- `originUrl: string`
- `fullShortUrl: string`

### `ShortLinkPageRespDTO`

- `id`
- `domain`
- `shortUri`
- `fullShortUrl`
- `originUrl`
- `gid`
- `validDateType`
- `enableStatus`
- `validDate`
- `createTime`
- `describe`
- `favicon`
- `totalPv`
- `todayPv`
- `totalUv`
- `todayUv`
- `totalUip`
- `todayUip`

### `ShortLinkStatsRespDTO`

- `pv`
- `uv`
- `uip`
- `daily`
- `localeCnStats`
- `hourStats`
- `topIpStats`
- `weekdayStats`
- `browserStats`
- `osStats`
- `uvTypeStats`
- `deviceStats`
- `networkStats`

## 6. 当前 18 条测试资产与 Operation 的人工预映射

> 这是 Stage 5 实现前的人工核对结果，不等同于框架已经自动生成 Coverage Index。
> Stage 5 完成后应由代码生成并验证。


### `shortlinkUserLogin`

- `shortlink.auth.login.success`
- `shortlink.auth.login.invalid_password`
- `shortlink.auth.login.redis_state`

### `shortlinkGroupList`

- `shortlink.group.query.success`
- `shortlink.group.query.unauthorized`

### `shortlinkCreate`

- `shortlink.link.create.success`
- `shortlink.link.create.invalid_url`
- `shortlink.link.create.db_persistence`
- `shortlink.link.create.unauthorized`
- `shortlink.link.recycle.db_lifecycle (workflow relation)`
- `shortlink.link.recycle.goto_cache_lifecycle (workflow relation)`

### `shortlinkPage`

- `shortlink.link.page.contains_created`

### `shortlinkRedirect`

- `shortlink.redirect.success`
- `shortlink.redirect.recycled`
- `shortlink.redirect.redis_state`
- `shortlink.redirect.notfound`

### `shortlinkStats`

- `shortlink.statistics.query.success`
- `shortlink.statistics.db_persistence`

### `shortlinkRecycleSave`

- `shortlink.link.recycle.db_lifecycle (workflow relation)`
- `shortlink.link.recycle.goto_cache_lifecycle (workflow relation)`

### `shortlinkRecycleRemove`

- `shortlink.link.recycle.db_lifecycle (workflow relation)`
- `shortlink.link.recycle.goto_cache_lifecycle (workflow relation)`

## 7. 当前可见的 Coverage 基线

按默认 External API Surface 统计：

- External Operations：**27**
- 当前测试资产明确引用的 External Operations：**8**
- 人工预估 Operation Coverage：**8/27 ≈ 29.6%**

当前明确关联的 Operation：

- `shortlinkGroupList` — GET /api/short-link/admin/v1/group
- `shortlinkRecycleSave` — POST /api/short-link/admin/v1/recycle-bin/save
- `shortlinkRecycleRemove` — POST /api/short-link/admin/v1/recycle-bin/remove
- `shortlinkCreate` — POST /api/short-link/admin/v1/create
- `shortlinkPage` — GET /api/short-link/admin/v1/page
- `shortlinkStats` — GET /api/short-link/admin/v1/stats
- `shortlinkUserLogin` — POST /api/short-link/admin/v1/user/login
- `shortlinkRedirect` — GET /{short-uri}

这个数字的意义不是“框架覆盖差”，而是证明 Stage 5 的价值：
当前 18 条用例为了代表性验证框架，只覆盖了若干核心接口；Contract 建立后可以准确看到哪些 API 尚无测试资产。

## 8. Stage 5 暴露出的一个通用建模问题

普通声明式 Case 通常只对应一个 `operation_id`，但一个 Python Workflow 可能跨多个 API Operation。

当前 Shortlink 两个 lifecycle Workflow 已在 YAML 的 `metadata.operations` 中保存：
- `shortlinkCreate`
- `shortlinkRecycleSave`
- `shortlinkRecycleRemove`

Stage 5 不应把这个做成 Shortlink 特例。建议将“Workflow -> 多 Operation”正式提升为通用测试资产关系，
例如一等字段 `operations` / `operation_ids`，由 Coverage Engine 统一消费。

## 9. Contract 获取方式的通用边界

### 模式 A：项目已有 OpenAPI 3.x

客户配置：

```yaml
contract:
  provider: openapi
  source: path/to/openapi.yaml
```

Framework：
`OpenAPIProvider -> ApiContract`

### 模式 B：项目没有 OpenAPI，但有后端源码

不在 Core 中做源码解析器。

一次性流程：

```text
后端源码
→ 人工 / AI 辅助提取 Method + Path + Request + Response
→ 评审
→ static contract.yaml
→ StaticManifestProvider
→ ApiContract
```

客户配置：

```yaml
contract:
  provider: static_manifest
  source: testcases/<project>/contract/contract.yaml
```

### 模式 C：没有源码，但有接口文档

```text
接口文档 / Postman / Apifox / Wiki
→ 整理成 Static Manifest
→ StaticManifestProvider
→ ApiContract
```

### 模式 D：已有框架定义的 Static Manifest

直接配置 `static_manifest` Provider，无需转换。

## 10. 不做的事情

Stage 5 不建设：
- Spring Controller 通用解析器；
- Java DTO 静态分析平台；
- FastAPI/NestJS/Gin/.NET 源码扫描器；
- 每次测试运行时实时解析源码。

这些如果未来多个真实项目都证明有长期需求，再作为独立可插拔 Contract Acquisition Tool 评估，
而不是进入 Framework Core。
