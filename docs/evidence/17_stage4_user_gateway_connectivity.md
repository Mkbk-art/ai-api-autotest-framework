# Stage 4 用户本地 Gateway 连通性证据（脱敏摘要）

- 用户 Windows + Python 3.11 已执行 `python run.py --env shortlink-local --level smoke`。
- Runner 成功向 `http://127.0.0.1:8000/api/short-link/admin/v1/user/login` 发送真实 POST。
- Gateway 返回 HTTP 200，证明 Python Requests -> Gateway -> 登录路由真实连通。
- 该次业务码不是成功码，原因定位为 Shell 中密码环境变量值误写；因此 token/gid 尚未获得。
- 断言引擎正确报告业务码失败与 token 缺失，没有把 HTTP 200 当作业务成功。
- 本文件不保存用户名、密码或 token 实际值。
