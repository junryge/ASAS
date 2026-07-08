# -*- coding: utf-8 -*-
"""DB 커넥터 — Oracle(oracledb) / MSSQL(pymssql). 기본은 SELECT만 허용."""
import logging
import re

log = logging.getLogger("gateway.db")


def _is_select(sql: str) -> bool:
    s = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)          # /* */ 주석 제거
    s = re.sub(r"--[^\n]*", " ", s)                          # -- 주석 제거
    first = (s.strip().split(None, 1) or [""])[0].upper()
    return first in ("SELECT", "WITH")


def _query_oracle(conn_cfg: dict, sql: str, max_rows: int) -> dict:
    try:
        import oracledb
    except ImportError:
        return {"error": "oracledb 미설치 — pkgs에서 pip install --no-index oracledb"}
    with oracledb.connect(
        user=conn_cfg["user"], password=conn_cfg["password"], dsn=conn_cfg["dsn"]
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchmany(max_rows) if cols else []
            return {"columns": cols, "rows": [list(r) for r in rows], "rowcount": len(rows)}


def _query_mssql(conn_cfg: dict, sql: str, max_rows: int) -> dict:
    try:
        import pymssql
    except ImportError:
        return {"error": "pymssql 미설치 — pkgs에서 pip install --no-index pymssql"}
    with pymssql.connect(
        server=conn_cfg["host"],
        user=conn_cfg["user"],
        password=conn_cfg["password"],
        database=conn_cfg["database"],
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchmany(max_rows) if cols else []
            return {"columns": cols, "rows": [list(r) for r in rows], "rowcount": len(rows)}


def register(mcp, cfg: dict) -> None:
    dc = cfg.get("db", {}) or {}
    connections: dict = dc.get("connections") or {}
    max_rows = int(dc.get("max_rows", 500))
    select_only = bool(dc.get("select_only", True))

    @mcp.tool()
    def db_connections() -> dict:
        """사용 가능한 DB 연결 목록(이름: 종류)을 반환한다. 계정 정보는 노출하지 않는다."""
        return {name: c.get("type") for name, c in connections.items()}

    @mcp.tool()
    def db_query(connection: str, sql: str) -> dict:
        """등록된 DB 연결로 SQL을 실행한다.

        connection: config.yaml db.connections에 등록된 이름 (db_connections로 확인)
        sql: 실행할 SQL. select_only=true면 SELECT/WITH만 허용.
        결과는 max_rows까지만 반환한다.
        """
        if connection not in connections:
            return {"error": f"등록되지 않은 연결: {connection}", "allowed": list(connections)}
        if select_only and not _is_select(sql):
            return {"error": "SELECT/WITH 쿼리만 허용된다 (config db.select_only)"}
        c = connections[connection]
        log.info("db_query %s: %.200s", connection, sql)
        try:
            if c.get("type") == "oracle":
                return _query_oracle(c, sql, max_rows)
            if c.get("type") == "mssql":
                return _query_mssql(c, sql, max_rows)
            return {"error": f"지원하지 않는 type: {c.get('type')}"}
        except Exception as e:  # DB 드라이버 예외 전부
            log.warning("db_query 실패 %s: %s", connection, e)
            return {"error": str(e)}
