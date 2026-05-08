# Harness MVP

Python 도구 실행 하네스 - 도구 등록, 프롬프트 라우팅, 멀티턴 실행, 세션 저장을 지원합니다.

## 프로젝트 구조

```
harness-mvp/
    harness/                   # 메인 패키지
        __init__.py            # 공개 API export
        __main__.py            # python -m harness 진입점
        models.py              # 핵심 데이터클래스 (Tool, Task, TurnResult 등)
        registry.py            # 도구 등록/조회/필터/실행
        permissions.py         # 권한 차단 (deny-list 기반)
        router.py              # 프롬프트 -> 도구 매칭 (토큰 스코어링)
        engine.py              # HarnessEngine (턴 루프, 예산, 스트림, 세션)
        session.py             # 세션 JSON 저장/로드
        history.py             # 이벤트 로그
        transcript.py          # 트랜스크립트 관리
        context.py             # 워크스페이스 컨텍스트 스캔
        cli.py                 # CLI 인터페이스
    tests/                     # 테스트 모음
        test_models.py
        test_permissions.py
        test_registry.py
        test_router.py
        test_engine.py
        test_session.py
        test_history.py
        test_transcript.py
        test_context.py
        test_cli.py
```

## 빠른 시작

### 요구사항
- Python 3.10+

### CLI 사용

```bash
# 등록된 도구 목록
python -m harness list

# 도구 검색
python -m harness find echo

# 프롬프트 라우팅 (매칭 결과 확인)
python -m harness route "echo hello"

# 프롬프트 실행 (멀티턴 루프)
python -m harness run "echo hello" --max-turns 3

# 구조화 출력 모드
python -m harness run "echo test" --structured-output

# 권한 차단 적용
python -m harness run "echo test" --deny-tool echo

# 단일 도구 직접 실행
python -m harness exec-tool upper "hello world"

# 기본 태스크 목록
python -m harness tasks

# 워크스페이스 컨텍스트
python -m harness context

# 세션 목록/로드
python -m harness session-list
python -m harness session-load <session_id>

# 세션 리포트
python -m harness summary
```

### 테스트 실행

```bash
python -m pytest tests/ -v
```

## 아키텍처

### 3-Layer 구조

**1. Tool Wiring (도구 배선)**
- `ToolRegistry`: dict 기반 O(1) 조회, 등록/해제/필터/실행
- `ToolPermissionContext`: deny_names + deny_prefixes로 도구 차단
- `Tool.handler`: 실제 Callable[[str], str] 핸들러

**2. Task Orchestration (태스크 오케스트레이션)**
- `ToolRouter.route()`: 프롬프트 토큰화 -> 도구 name/description 매칭 스코어링
- `HarnessEngine.submit()`: 단일 턴 (라우팅 -> 권한 필터 -> 실행 -> 결과)
- `HarnessEngine.run_loop()`: 멀티턴 루프 (max_turns, budget 제한)
- `HarnessEngine.stream_submit()`: 이벤트 스트림 제너레이터

**3. Runtime Context (런타임 컨텍스트)**
- `WorkspaceContext`: 파일시스템 스캔
- `StoredSession`: JSON 세션 저장/로드
- `HistoryLog`: 이벤트 기록 -> 마크다운 렌더링
- `TranscriptStore`: 메시지 컴팩션, 리플레이

### 빌트인 도구

| 이름 | 설명 |
|------|------|
| echo | 입력 그대로 반환 |
| upper | 대문자 변환 |
| word-count | 단어 수 카운트 |
| reverse | 문자열 뒤집기 |
| char-count | 문자 수 카운트 |

### 커스텀 도구 등록

```python
from harness import Tool, ToolRegistry, HarnessEngine

registry = ToolRegistry()
registry.register(Tool(
    name='my-tool',
    description='My custom tool',
    handler=lambda payload: f'Processed: {payload}',
))

engine = HarnessEngine.create(registry)
result = engine.submit('my-tool test input')
print(result.output)
```

## 기존 분석 코드와의 관계

이 MVP는 `claw-code-core-harness-analysis_2026-04-01/src/` 의 하네스 패턴을 참조하여 독립적으로 구축되었습니다.

| 기존 src/ | MVP harness/ | 변경점 |
|-----------|-------------|--------|
| tools.py + Tool.py + tool_pool.py + execution_registry.py | registry.py | 4파일 -> 1파일 통합 |
| runtime.py + query_engine.py | engine.py | 라우팅+엔진 통합 |
| 시뮬레이션 실행 (문자열 반환) | 실제 핸들러 실행 | Callable[[str], str] |
| JSON 스냅샷 의존 | 프로그래밍 방식 등록 | 외부 의존성 제거 |
| 선형탐색 O(n) | dict 기반 O(1) | 성능 개선 |
