"""基于 Requests 的统一 HTTP 客户端。

本模块负责真正的 HTTP 网络通信，包括 Session 复用、JSON/表单/查询参数/文件
转发、超时和 TLS 配置、网络异常透传、日志记录以及 Allure 请求/响应附件。
敏感 Header 和请求数据只在日志与报告副本中脱敏，真实请求仍使用原始值。
"""
from __future__ import annotations

import json as json_module
from typing import Any

import requests

from utils import allure_compat as allure
from utils.logger import logs
from utils.sanitizer import sanitize


class RequestClient:
    """封装 ``requests.Session``，提供框架统一的 HTTP 调用入口。"""

    def __init__(self, timeout: float = 30, verify: bool = True, session=None) -> None:
        """设置默认超时、TLS 策略和可注入 Session。"""
        self.timeout = timeout
        self.verify = verify
        self.session = session or requests.Session()

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, Any] | None = None,
        params: Any = None,
        data: Any = None,
        json: Any = None,
        cookies: Any = None,
        files: Any = None,
        timeout: float | None = None,
        verify: bool | None = None,
        **kwargs: Any,
    ):
        """发送底层 HTTP 请求，并保留 Requests 原生异常语义。

        每次调用可临时覆盖默认 timeout/verify。超时和连接失败会记录日志后重新抛出，
        使 Pytest 能明确区分网络失败，而不是把失败吞掉并返回伪成功结果。
        """
        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json,
                cookies=cookies,
                files=files,
                timeout=self.timeout if timeout is None else timeout,
                verify=self.verify if verify is None else verify,
                **kwargs,
            )
            logs.info("[%s] %s -> %s", method.upper(), url, response.status_code)
            return response
        except requests.exceptions.Timeout:
            logs.error("请求超时: %s %s", method, url)
            raise
        except requests.exceptions.ConnectionError:
            logs.error("连接失败: %s %s", method, url)
            raise

    def run(
        self,
        api_name: str,
        url: str,
        case_name: str,
        method: str,
        headers: dict[str, Any] | None,
        cookies: Any = None,
        files: Any = None,
        **kwargs: Any,
    ):
        """记录测试语义信息、生成 Allure 附件并调用 :meth:`request`。"""
        safe_headers = sanitize(headers or {})
        safe_payload = sanitize(kwargs.get("json", kwargs.get("data", kwargs.get("params"))))
        logs.info("接口: %s | 用例: %s", api_name, case_name)
        logs.info("请求: %s %s", method, url)
        logs.info("Header: %s", safe_headers)

        allure.attach(
            json_module.dumps(safe_headers, ensure_ascii=False, default=str),
            "请求头",
            allure.attachment_type.JSON,
        )
        if safe_payload is not None:
            allure.attach(
                json_module.dumps(safe_payload, ensure_ascii=False, default=str),
                "请求参数",
                allure.attachment_type.JSON,
            )

        response = self.request(
            method=method,
            url=url,
            headers=headers,
            cookies=cookies,
            files=files,
            **kwargs,
        )
        # 状态码单独作为结构化元数据保留；响应 Body 继续沿用既有“响应结果”附件。
        allure.attach(
            json_module.dumps({"status_code": response.status_code}, ensure_ascii=False),
            "响应元数据",
            allure.attachment_type.JSON,
        )
        try:
            body = response.json()
            attachment = json_module.dumps(sanitize(body), ensure_ascii=False, indent=2)
            attachment_type = allure.attachment_type.JSON
        except Exception:
            attachment = response.text
            attachment_type = allure.attachment_type.TEXT
        allure.attach(attachment, "响应结果", attachment_type)
        return response
