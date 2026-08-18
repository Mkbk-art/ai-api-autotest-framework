# Stage 4 Create/Page 离线交付验证

验证日期：2026-08-13。

```text
pytest -q tests
=> 70 passed

pytest -q
=> 76 passed

python run.py --env shortlink-local --collect-only
=> 4 tests collected (Auth / Group / Create / Page)

python run.py --env test --level smoke
=> 2 passed, 4 deselected

python run.py --env test --level core
=> 2 passed, 4 deselected

python run.py --env test --level regression
=> 2 passed, 4 deselected

python -m compileall -q core utils testcases tests mock_server run.py
=> PASS
```

说明：`shortlink-local` 在模型沙箱仅执行 collect-only，不发送真实本地网络请求；真实 HTTP
成功链必须由用户 Windows 环境完成。默认 `test` 环境继续使用受控 Mock Server。
