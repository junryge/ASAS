# Harness MVP Architecture

## 기존 src/ 분석 결과 (3-Section)

### Section 1: Tool Wiring

**원본 파일**: `src/tools.py`, `src/Tool.py`, `src/tool_pool.py`, `src/permissions.py`, `src/execution_registry.py`

**구조**:
- `PortingModule(name, responsibility, source_hint, status)` - 도구 데이터 모델
- JSON 스냅샷(`tools_snapshot.json`)에서 100+ 도구 로드, `@lru_cache` 캐싱
- `get_tool(name)` - 선형탐색 O(n), 대소문자 무시
- `get_tools(simple_mode, include_mcp, permission_context)` - 다중 필터
- `execute_tool(name, payload)` - 시뮬레이션 메시지 반환 (실제 실행 아님)
- `ToolPermissionContext(deny_names, deny_prefixes)` - frozenset/tuple 기반 차단
- `ToolPool` - 필터링된 도구 집합, 마크다운 렌더링
- `ExecutionRegistry` - MirroredCommand/MirroredTool 래퍼, 통합 실행 인터페이스

**데이터 흐름**:
```
JSON snapshot -> @lru_cache load -> PORTED_TOOLS tuple
                                     |
                    get_tools() filter -> ToolPool
                                     |
                    ExecutionRegistry -> MirroredTool.execute()
```

### Section 2: Task Orchestration

**원본 파일**: `src/task.py`, `src/tasks.py`, `src/runtime.py`, `src/query_engine.py`

**구조**:
- `PortingTask(id, description)` - 최소 태스크 모델
- `default_tasks()` - 3개 표준 태스크 팩토리
- `PortRuntime.route_prompt(prompt, limit)`:
  - 프롬프트 토큰화 (`/`, `-` 분리)
  - 토큰 vs name/source_hint/responsibility 오버랩 스코어링
  - command 우선, 나머지 score 내림차순 정렬
- `PortRuntime.bootstrap_session()`:
  1. build_port_context() -> 워크스페이스 스캔
  2. run_setup(trusted=True) -> 환경 설정
  3. QueryEnginePort.from_workspace() -> 엔진 생성
  4. route_prompt() -> 매칭
  5. ExecutionRegistry -> 명령/도구 실행
  6. stream_submit_message() + submit_message() -> 턴 처리
  7. persist_session() -> 세션 저장
  8. RuntimeSession 반환
- `QueryEnginePort.submit_message()`:
  - max_turns 체크 -> 라우팅 결과 포맷 -> 토큰 예산 확인 -> 메시지 저장 -> 컴팩션
  - stop_reason: 'completed' | 'max_turns_reached' | 'max_budget_reached'
- `QueryEnginePort.stream_submit_message()`:
  - yield: message_start -> command_match -> tool_match -> permission_denial -> message_delta -> message_stop
- `run_turn_loop(prompt, max_turns)`: 반복 submit, non-completed에서 중단

### Section 3: Runtime Context

**원본 파일**: `src/context.py`, `src/session_store.py`, `src/history.py`, `src/transcript.py`

**구조**:
- `PortContext`:
  - source_root, tests_root, assets_root, archive_root (4개 경로)
  - python_file_count, test_file_count, asset_file_count (3개 카운트)
  - archive_available (bool)
  - `build_port_context(base)` - rglob으로 파일 스캔
- `StoredSession(session_id, messages, input_tokens, output_tokens)`:
  - `.port_sessions/` 디렉토리에 JSON 저장
  - `save_session()` / `load_session()` 라운드트립
- `HistoryEvent(title, detail)` + `HistoryLog`:
  - add() -> events 리스트 추가
  - as_markdown() -> 마크다운 렌더링
- `TranscriptStore(entries, flushed)`:
  - append() -> flushed=False 리셋
  - compact(keep_last) -> 오래된 항목 제거
  - replay() -> tuple 반환
  - flush() -> flushed=True 설정

## MVP 매핑

| 원본 | MVP | 설계 결정 |
|------|-----|-----------|
| `PortingModule` | `Tool(handler=Callable)` | 실제 핸들러 포함 |
| `tools.py` + `tool_pool.py` + `execution_registry.py` | `registry.py` | 통합, dict 기반 |
| `PortRuntime` + `QueryEnginePort` | `HarnessEngine` | 라우팅+엔진 통합 |
| `PortRuntime._score()` | `ToolRouter._score()` | 동일 알고리즘 |
| `ToolPermissionContext` | `ToolPermissionContext` | 동일 구현 |
| `PortContext` | `WorkspaceContext` | 단순화 (경로 3개 -> 1개) |
| `StoredSession` | `StoredSession` | 동일 구현 |
| `HistoryLog` | `HistoryLog` | 동일 구현 |
| `TranscriptStore` | `TranscriptStore` | 동일 구현 |

## 누락 모듈 (분석 팩에 없었던 것)

기존 `src/`에서 import되지만 파일이 포함되지 않은 모듈 10개:
- `models.py` (PortingModule, PortingBacklog, PermissionDenial, UsageSummary)
- `commands.py` (PORTED_COMMANDS, execute_command 등)
- `port_manifest.py` (PortManifest, build_port_manifest)
- `setup.py` (WorkspaceSetup, run_setup)
- `system_init.py` (build_system_init_message)
- `bootstrap_graph.py`, `command_graph.py`
- `direct_modes.py`, `remote_runtime.py`
- `src/__init__.py`

이로 인해 기존 코드는 직접 실행 불가. MVP는 이를 모두 자체 포함하여 독립 실행 가능.
