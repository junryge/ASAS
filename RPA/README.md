# FlowBot Studio — RPA 워크플로우 빌더 (실제 실행판)

`RPA_Workflow_Builder.html` 로 만든 워크플로우를 **윈도우 PC에서 실제로 실행**하는
RPA 시스템입니다. (기존 HTML은 실행 시늉만 내는 시뮬레이션이었고, 여기에 실행
엔진 `server.py` 를 붙여 진짜 자동화가 동작합니다.)

## 1. 설치 (윈도우, 최초 1회)

```bat
cd RPA
pip install -r requirements.txt
```

## 2. 실행

```bat
python server.py
```

콘솔에 접속 주소가 표시됩니다 → 브라우저에서 **http://localhost:8600** 접속.

> ⚠️ 반드시 `http://localhost:8600` 으로 접속해야 실제 실행/서버저장이 됩니다.
> HTML 파일을 `file://` 로 그냥 열면 시뮬레이션(가짜)만 됩니다.

## 3. 사용 흐름

1. 화면에서 **＋ 스텝 추가** 로 자동화 단계를 쌓습니다.
2. 상단 **트리거** 를 눌러 실행 방식(수동 / 매일 / 매주 + 시각)을 정합니다.
3. **▶ 실행** → 서버가 각 스텝을 실제로 수행하고, 오른쪽 콘솔에 실시간 로그가 뜹니다.
4. **💾 저장** → 서버(`rpa_flow.json`)에 저장됩니다. 트리거가 매일/매주면
   서버 스케줄러가 그 시각에 **자동 실행**합니다. (서버가 켜져 있어야 함)

## 4. 지원 스텝(노드)

| 노드 | 실제 동작 |
|---|---|
| Python 스크립트 | 코드를 임시 .py 로 저장 후 `python` 으로 실행, 출력 캡처 |
| 마우스 | `pyautogui` 로 이동/클릭/더블/우클릭 |
| 키보드 | 텍스트 입력(한글은 클립보드 붙여넣기) / 단축키 |
| 대기 | 지정 초 동안 대기(중지 가능) |
| CMD | 명령 프롬프트 실행, 출력 캡처 |
| 이미지 인식 | 화면에서 이미지 찾기 / 화면 캡처 저장 |
| 조건(IF) | 조건식 평가 → false면 다음 스텝 1개 건너뜀 |
| 반복(Loop) | 바로 다음 스텝 1개를 지정 횟수 반복 |
| HTTP 요청 | GET/POST/PUT/DELETE 전송 |
| **브라우저** | URL 을 기본 브라우저로 열기 |
| **다운로드** | URL 에서 파일 다운로드(토큰/저장폴더/파일명 지정) |

## 5. 날짜 변수 (자동 자동화의 핵심)

모든 텍스트·URL·파일명 칸에 아래 변수를 쓰면 실행 시점 날짜로 자동 치환됩니다.

| 변수 | 예(오늘=2026-07-14 기준) |
|---|---|
| `{today}` | `20260714` |
| `{yesterday}` | `20260713` |
| `{tomorrow}` | `20260715` |
| `{now}` | `20260714002000` |
| 포맷 지정 `{yesterday:%Y-%m-%d}` | `2026-07-13` |

## 6. 이미 설정된 시나리오 — 매일 새벽 발동이벤트 CSV 자동 다운로드

`rpa_flow.json` 에 아래 시나리오가 **미리 저장**되어 있습니다. 서버를 켜두기만 하면
매일 00:20 에 자동 실행됩니다. (화면에서 다시 편집 후 💾저장을 누르면 갱신됩니다.)

- **트리거**: 매일 `00:20`
- **다운로드 노드**:
  - URL: `http://aiu-amhas-prediction-que.aipp01.skhynix.com/files/pjt_shared_pool/job/m16a_hubroom_event_prediction/predict_tobe/{yesterday}_발동이벤트.csv?_xsrf=...`
  - 파일명: `{yesterday}_발동이벤트.csv`  (실행일 **전날**)
  - 저장 폴더: 비움 → 서버 `downloads/` 폴더

동작 예: 오늘이 **07/16** 이면 `20260715_발동이벤트.csv` 를 받습니다 (실행일 전날).

JupyterLab 파일 다운로드 URL 은 파일 **우클릭 → Copy Download Link** 로 얻고,
날짜 부분만 `{yesterday}` 로 바꾸면 됩니다.

> ⚠️ URL 끝의 `?_xsrf=...` 토큰은 브라우저 세션 임시 토큰이라 시간이 지나면 만료될 수
> 있습니다. 자동 다운로드가 실패하면 **Copy Download Link** 로 새 URL 을 복사해 날짜만
> `{yesterday}` 로 바꿔 다시 붙여넣으세요. (xsrf 없이도 받아지면 `?_xsrf=...` 를 아예
> 빼면 만료 걱정이 없습니다.)

## 6-1. ★ JupyterLab 비밀번호 로그인 (중요)

주신 JupyterLab 은 **비밀번호(Password) 로그인**이 필요합니다. server.py 가 다운로드
직전에 `/login` 으로 자동 로그인(`_xsrf` 획득 → password POST → 세션 쿠키)하도록,
비밀번호를 아래 둘 중 **한 곳**에 넣으세요.

**방법 1) `config.json` (권장 — 화면에 안 보이고 파일 하나만 관리)**
```json
{ "jupyter_password": "여기에_주피터_접속_비밀번호" }
```

**방법 2) 화면에서 직접 입력**
다운로드 노드 편집 → **"Jupyter 로그인 비밀번호"** 칸에 입력 (비우면 config.json 사용)

- 로그인 성공하면 그 세션으로 CSV 를 받습니다 → 진짜 CSV 다운로드 ✓
- 비번이 틀리거나 없으면 로그에 **"CSV 가 아니라 HTML(로그인 페이지)"** 경고가 뜹니다.
- `?_xsrf=...` 는 이제 URL 에서 빼도 됩니다(로그인 세션이 처리). 날짜만 `{yesterday}` 로 두세요.

> ⚠️ `config.json` 은 비밀번호가 들어가므로 git/공유 금지입니다(`.gitignore` 처리됨).

## 7. 파일 구성

```
RPA/
├─ RPA_Workflow_Builder.html   # 빌더 화면(프론트)
├─ server.py                   # 실행 엔진(백엔드) — 여기서 실제 실행
├─ requirements.txt            # 의존성
├─ config.json                 # 비밀번호 설정(여기에 jupyter_password 입력)
├─ rpa_flow.json               # 서버 저장 워크플로우
├─ .gitignore                  # config.json/downloads 제외
└─ downloads/                  # 다운로드/캡처 저장 폴더(자동 생성)
```
