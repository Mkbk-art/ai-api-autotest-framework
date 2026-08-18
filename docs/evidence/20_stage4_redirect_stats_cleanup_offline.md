# Stage 4 Redirect / Statistics / Cleanup 离线交付验证

验证日期：2026-08-13。

本批次沙箱验证结果：

```text
pytest -q tests
=> 81 passed

pytest -q
=> 87 passed

python run.py --env shortlink-local --collect-only
=> 6 tests collected
   Auth / Group / Create / Page / Redirect / Statistics

python run.py --env test --level smoke
=> 2 passed, 4 deselected

python run.py --env test --level core
=> 2 passed, 4 deselected

python run.py --env test --level regression
=> 2 passed, 4 deselected

python -m compileall -q core utils testcases tests mock_server run.py
=> PASS

literal secret scan
=> PASS
```

本批次离线契约测试覆盖：

- Redirect 直接请求 `http://nurl.ink:8001/<short_uri>`，并设置 `allow_redirects=False`；
- 创建原始链接固定为 `https://github.com/`；
- Stats 即时成功、延迟成功和 15 秒边界超时；
- Cleanup 严格按 `recycle-bin/save -> recycle-bin/remove` 顺序调用；
- password repr / helper 签名安全；
- Stage 4 Python/YAML 高密度注释规范。

边界：沙箱无法访问用户 Windows 本机 Project:8001、Gateway:8000 和 Redis Stream Consumer，因此 Redirect / Stats / Cleanup 的真实网络结果仍需用户本机 6 条 smoke 验收。
