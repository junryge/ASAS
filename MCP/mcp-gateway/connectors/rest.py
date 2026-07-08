# -*- coding: utf-8 -*-
"""REST API 커넥터 — config.yaml에 등록된 내부 엔드포인트만 호출 (허용 목록 방식)."""
import logging

import requests

log = logging.getLogger("gateway.rest")


def register(mcp, cfg: dict) -> None:
    rc = cfg.get("rest", {}) or {}
    endpoints: dict = rc.get("endpoints") or {}
    timeout = rc.get("timeout", 10)

    @mcp.tool()
    def rest_endpoints() -> dict:
        """호출 가능한 내부 REST 엔드포인트 목록(이름: URL)을 반환한다."""
        return endpoints

    @mcp.tool()
    def rest_call(
        endpoint: str,
        method: str = "GET",
        params: dict | None = None,
        body: dict | None = None,
    ) -> dict:
        """등록된 내부 REST 엔드포인트를 호출한다.

        endpoint: config.yaml rest.endpoints에 등록된 이름 (rest_endpoints로 확인)
        method: GET / POST / PUT / DELETE
        params: 쿼리 스트링, body: JSON 바디
        """
        if endpoint not in endpoints:
            return {"error": f"허용되지 않은 endpoint: {endpoint}", "allowed": list(endpoints)}
        method = method.upper()
        if method not in ("GET", "POST", "PUT", "DELETE"):
            return {"error": f"지원하지 않는 method: {method}"}
        url = endpoints[endpoint]
        log.info("rest_call %s %s params=%s", method, url, params)
        try:
            r = requests.request(method, url, params=params, json=body, timeout=timeout)
            try:
                data = r.json()
            except ValueError:
                data = r.text[:10000]
            return {"status": r.status_code, "data": data}
        except requests.RequestException as e:
            log.warning("rest_call 실패 %s: %s", url, e)
            return {"error": str(e), "url": url}
