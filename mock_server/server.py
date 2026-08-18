"""受控本地 Mock HTTP 服务。

本模块模拟登录、资源发布、接口调用、错误鉴权、非 JSON 和慢响应等场景，用于
在真实短链接 SaaS 接入前验证测试框架本身。Mock 返回值是受控测试数据，不代表
真实业务接口、数据库或缓存已经完成验证。
"""
from __future__ import annotations

import json
import threading
import time
from urllib.parse import parse_qs, urlparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class _State:
    def __init__(self) -> None:
        self.token = "token-demo"
        self.next_interface_id = 1
        self.interfaces: dict[int, dict[str, Any]] = {}
        self.next_call_id = 1
        self.lock = threading.Lock()


class MockApiServer:
    """可作为上下文管理器启动/停止的线程化本地 Mock API Server。"""

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        """初始化监听地址；port=0 时由操作系统自动选择空闲端口。"""
        self.host = host
        self.port = port
        self._state = _State()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        """返回运行中的 Mock Server 根地址。"""
        if self._server is None:
            raise RuntimeError("MockApiServer is not running")
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def start(self) -> "MockApiServer":
        """启动后台 HTTP 线程，并返回自身以支持 with 语法。"""
        if self._server is not None:
            return self
        state = self._state

        class Handler(BaseHTTPRequestHandler):
            server_version = "MockApi/1.0"

            def log_message(self, _format: str, *_args: Any) -> None:
                return

            def _json_body(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0") or 0)
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    value = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return {}
                return value if isinstance(value, dict) else {}

            def _write_body(self, status: int, body: bytes, content_type: str) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    # Expected when a timeout test closes the client socket first.
                    return

            def _send(self, status: int, payload: dict[str, Any]) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self._write_body(status, body, "application/json; charset=utf-8")

            def _send_text(self, status: int, text: str) -> None:
                self._write_body(status, text.encode("utf-8"), "text/plain; charset=utf-8")

            def _authorized(self) -> bool:
                return self.headers.get("Authorization") == f"Bearer {state.token}"

            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path == "/health":
                    self._send(200, {"status": "ok"})
                    return
                if parsed.path == "/api/v1/plain":
                    self._send_text(200, "plain-response")
                    return
                if parsed.path == "/api/v1/slow":
                    params = parse_qs(parsed.query)
                    try:
                        delay = float(params.get("delay", ["0.1"])[0])
                    except (TypeError, ValueError):
                        delay = 0.1
                    time.sleep(max(0.0, min(delay, 2.0)))
                    self._send(200, {"success": True, "delay": delay})
                    return
                self._send(404, {"msg": "not found"})

            def do_POST(self) -> None:  # noqa: N802
                body = self._json_body()
                if self.path == "/api/v1/auth/login":
                    if body.get("username") == "demo_user" and body.get("password") == "demo_password":
                        self._send(
                            200,
                            {
                                "success": True,
                                "msg": "登录成功",
                                "data": {"access_token": state.token, "userId": 1},
                            },
                        )
                    else:
                        self._send(401, {"success": False, "msg": "用户名或密码错误"})
                    return

                if self.path == "/api/v1/interface/publish":
                    if not self._authorized():
                        self._send(401, {"success": False, "msg": "未登录或Token已过期"})
                        return
                    if not body.get("name"):
                        self._send(400, {"success": False, "msg": "接口名称不能为空"})
                        return
                    with state.lock:
                        interface_id = state.next_interface_id
                        state.next_interface_id += 1
                        state.interfaces[interface_id] = body
                    self._send(
                        200,
                        {"success": True, "msg": "发布成功", "data": {"interfaceId": interface_id}},
                    )
                    return

                if self.path == "/api/v1/interface/call":
                    if not self._authorized():
                        self._send(401, {"success": False, "msg": "鉴权失败"})
                        return
                    try:
                        interface_id = int(body.get("interface_id"))
                    except (TypeError, ValueError):
                        self._send(400, {"success": False, "msg": "interface_id 无效"})
                        return
                    if interface_id not in state.interfaces:
                        self._send(404, {"success": False, "msg": "接口不存在"})
                        return
                    with state.lock:
                        call_id = state.next_call_id
                        state.next_call_id += 1
                    self._send(
                        200,
                        {
                            "success": True,
                            "call_status": "success",
                            "data": {"callId": call_id, "responseTime": 12},
                        },
                    )
                    return

                self._send(404, {"msg": "not found"})

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        """安全关闭 HTTP Server 和后台线程。"""
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._server = None
        self._thread = None

    def __enter__(self) -> "MockApiServer":
        """进入 with 代码块时自动启动服务。"""
        return self.start()

    def __exit__(self, exc_type, exc, traceback) -> None:
        """离开 with 代码块时无论测试是否失败都关闭服务。"""
        self.stop()
