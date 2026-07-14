# 작업 규칙

## DFS 리포트 시스템 (AMHS Daily Report System)

- **수정은 항상 압축 풀린 `DFS/FDS/` 폴더에서 직접 한다.** (사용자 지시: 2026-07-14)
  - `DFS/FDS/server.py` — FastAPI 서버 (실행: `python server.py` → http://localhost:8000)
  - `DFS/FDS/INDEX/Daily_Report_System.html` — 웹 화면 (달력형 일일 리포트 시스템)
  - `DFS/FDS/config.json` — 암호/포트 설정
  - `DFS/FDS/reports_db.json` — 리포트 데이터 (서버가 자동 생성/갱신)
- `DFS/FDS.zip` 은 구버전 보관용 — **더 이상 갱신하지 않는다.**
- `DFS/샘플-3.html` — 날짜별로 등록하는 리포트 템플릿 (AMOS 반송이벤트 보고서)

### Daily_Report_System.html 수정 방법 (중요)

이 파일은 번들 아카이브 형식이다. 실제 앱 소스는 **468번째 줄**의
`<script type="__bundler/template">` 안에 JSON 문자열로 인코딩되어 있다.

수정 절차:
1. 468번째 줄을 `json.loads()` 로 디코드 → 내부 HTML (앱 로직은 `<script type="text/x-dc">` 안의 React 스타일 컴포넌트)
2. 내부 HTML 수정 (x-dc 스크립트 안에 리터럴 `</script>` 금지 — `'<'+'/script>'` 로 분리)
3. `json.dumps(ensure_ascii=False)` 후 모든 `</` 를 `</` 로 치환하여 468번째 줄에 재기록
4. 라운드트립 검증: `json.loads(새 줄) == 수정한 내부 HTML`

### 저장 동작 (2026-07 수정됨)

- 샘플-3.html 의 "저장" 버튼 → `postMessage({type:'amhs-report-save', date, html})` 로 부모(달력 시스템)에 전달 → 부모가 해당 날짜 body 갱신 + `PUT /api/reports` 로 서버 저장
- 구버전 샘플 호환: 뷰어가 iframe 열 때 `#__amhs_bridge` 스크립트 주입 (localStorage 저장 감지 → HTML 직렬화 → postMessage)
- 반드시 `http://서버IP:8000` 으로 접속해야 서버 저장됨 (file:// 로 열면 경고 토스트 표시)

### 계정/로그인 체계 (2026-07 추가)

- `server.py` 는 표준 라이브러리만 사용 (FastAPI/uvicorn 불필요) — `python server.py` 만으로 실행
- 최고 관리자: `config.json` 의 `adminId` / `adminPassword` 로 로그인 (기본 admin / AMHS1234)
  - 리포트 등록·수정·삭제 + "👥 계정 관리"(운영담당자 생성/삭제/비번변경)
- 운영담당자: `users_db.json` 에 저장 (비밀번호 sha256+salt 해시) — 웹에서 관리자가 생성
  - 등록된 리포트 열람 + 리포트 안 내용 입력·저장만 가능
- 인증: POST /api/login → 토큰(X-Auth-Token 헤더), 세션 12시간, 서버 재시작 시 재로그인
- 날짜별 저장 API: PUT/DELETE /api/reports/{YYYY-MM-DD} (운영담당자 PUT은 기존 날짜만 허용)
- 서버 응답 전에 요청 body 를 반드시 소진할 것 (keep-alive 오염 방지 — _json_body 먼저 호출)

### 운영담당자별 내용 격리 (2026-07 추가)

- 리포트 = 등록 원본(body) + 담당자별 사본(opBodies: {아이디: {body, updatedAt}})
- 운영담당자 GET /api/reports → 자기 사본만 body 로 받음 (opBodies 는 절대 안 내려감)
- 운영담당자 PUT /api/reports/{날짜} → 자기 사본에만 저장 (원본 불변)
- 관리자 PUT (쿼리 없음) → 원본 저장, 서버가 opBodies 보존 / ?op=아이디 → 해당 담당자 사본 저장
- 관리자 뷰어에 [등록 원본][담당자 아이디…] 보기 전환 필 표시
- 다운로드(복원/엑셀/PC보관/기간 HTML·MD)는 관리자 전용 (화면에서 숨김)
- 관리자 계정: AMHS1234 / AMHS1234 (config.json adminId/adminPassword)
- 로컬 캐시 키는 로그인 아이디별 분리 (daily_reports_v1:아이디)
