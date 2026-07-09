# AMHS MCP Gateway (폐쇄망)

니 PC(MCP 클라이언트 + LLM 호출 코드) → **서버 PC(이 게이트웨이, :8010)** → DB PC / REST / 파일서버 / 내부 MCP 서버

## 1. 패키지 반입 (외부망 PC에서 1회)

외부망 PC에서 (서버 PC와 같은 OS·Python 버전 기준):

```
pip download -r pkgs/requirements.txt -d pkgs/
```

`pkgs/` 폴더째 USB/반입절차로 서버 PC에 복사 후, 서버 PC에서:

```
pip install --no-index --find-links pkgs -r pkgs/requirements.txt
```

Oracle/MSSQL 안 쓰면 oracledb, pymssql은 빼도 된다 (없어도 서버는 뜬다).

## 2. 설정

`config.yaml` 열어서 내부 서버 주소·계정으로 수정:
- `rest.endpoints` — 내부 REST API 주소
- `db.connections` — Oracle/MSSQL 접속 정보 (CHANGE_ME 교체)
- `files.roots` — 공유폴더 경로
- `relay.servers` — 중계할 내부 MCP 서버 주소

## 3. 실행 (서버 PC)

```
python server.py
```

→ `http://<서버IP>:8010/mcp` 로 접속 가능. 방화벽에서 8010 인바운드 열어야 한다.

### 관리 콘솔 (HTML에서 설정 → YAML 저장)

- 브라우저에서 `http://<서버IP>:8010/console` 접속
- 콘솔에서 서버 등록/수정/삭제하면 → 게이트웨이가 `mcp-gateway/servers.yaml`에 자동 저장
- 콘솔에 등록한 서버는 **곧바로 릴레이 중계 대상이 된다** (`relay_servers`/`relay_call`에서 바로 보임).
  게이트웨이 재시작 불필요 — 호출마다 servers.yaml을 다시 읽는다. `config.yaml`의 `relay.servers`와 병합되며 이름이 겹치면 콘솔 등록이 우선.
  · 항목 포맷: `{name, url}` 또는 `{name, host, port}` (port 있으면 `http://host:port/mcp`로 조립). `enabled: false`면 제외.
- 헤더에 저장 상태 표시: **YAML 저장 연결됨**(정상) / **게이트웨이 미연결 · 임시 저장**(오프라인 폴백)
- INDEX 폴더(MCP_Console.html)는 mcp-gateway 폴더와 같은 위치에 둬야 한다 (config server.console_html로 경로 변경 가능)
- **관리 API 보호(선택)**: `config.yaml`의 `server.admin_token`을 채우면 서버 저장(POST)에 `Authorization: Bearer <토큰>` 헤더가 필요하다. 비워두면 개방(하위호환).

### 헬스체크

- `GET http://<서버IP>:8010/health` → `{status, uptime_seconds, tool_count, registered_servers, auth_enabled}` (모니터링/로드밸런서용)

## 4. 클라이언트 연결 (니 PC)

### Python 코드에서

```python
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client("http://<서버IP>:8010/mcp") as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            print([t.name for t in tools.tools])
            res = await s.call_tool("gateway_info", {})
            print(res.content[0].text)

asyncio.run(main())
```

※ 폐쇄망이므로 Claude Desktop 같은 외부 클라이언트는 사용 불가.
클라이언트는 위 코드처럼 니 PC에서 직접 만든 앱(MCP 클라이언트 + 내부 LLM 호출)이 전부다.

## 제공 tool 목록

| tool | 설명 |
|---|---|
| gateway_info | 게이트웨이 상태·설정 요약 (연결 확인용) |
| rest_endpoints / rest_call | 등록된 내부 REST API 호출 |
| db_connections / db_query | Oracle/MSSQL 쿼리 (기본 SELECT만) |
| fs_roots / fs_list / fs_read / fs_write / fs_search | 공유폴더 접근 (root 밖 차단) |
| relay_servers / relay_list_tools / relay_call | 내부 다른 MCP 서버 중계 |

모든 호출은 `gateway.log`에 감사 로그로 남는다.
