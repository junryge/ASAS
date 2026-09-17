# oht3d — 3D 아이소메트리 뷰어 (three.js)

출처: 고객이 준 이식 세트 `oht3d_port` (three.js **r169**, MIT · CDN/빌드 도구 없음 · 폐쇄망 동작).

| 파일 | 역할 |
|---|---|
| `three.module.min.js` | three.js r169 — 세트 그대로 (손대지 않음) |
| `oht3d.js` | 3D 뷰어 모듈 — `createOHT3D(container, options)` |

`dashboard.html` 의 **'⬢ 아이소메트리'** 단추가 `import('/static/js/oht3d/oht3d.js')` 로 받아서 쓴다.
`main.py` 가 `/static` 을 서빙하고, `oht_world.spec` 의 datas 에 `('static', 'static')` 이 있어 exe 에도 들어간다.

## 세트 원본과 다른 곳 (oht3d.js)

| 무엇 | 왜 |
|---|---|
| `projection: 'iso' \| 'persp'` — 직교(아이소메트리) 카메라 | 원본은 원근뿐이었다. 단추 이름이 아이소메트리라 등각(방위 45°·고도 35.264°)으로 연다. 바 단추 '아이소로 / 원근으로'. |
| 직교 절두체 반높이 = `dist·tan(16°)` | 원근용으로 짜인 시점 계산(전체·존·패널 밀기·라벨 겹침)이 그대로 맞는다. |
| 직교에서 스프라이트 크기 × `dist` | three 의 `sizeAttenuation:false` 는 원근에서만 '화면 크기 고정' 이다. 직교에서는 0.1 m 짜리 라벨이 되어 안 보였다. |
| 상태 4 = **OBS** | 2D 맵이 OBS(장애물 정지)를 JAM 과 다른 색으로 보여준다. 넷뿐이면 그 구분이 사라진다. |
| 행거를 노드마다가 아니라 **4 m 칸마다** | 실물 M14A 는 노드가 0.7 m 간격(9,403개)이라 노드마다 세우면 봉 9천 개가 숲이 되어 차량·설비가 안 보였다. |
| `dark` / `background` / `stateColors` 옵션 + `setOptions` | 페이지 테마(body[data-theme])와 ⚙ 설정의 차량 색을 따라간다. 원본은 prefers-color-scheme 만 봤다. |
| `setActive(false)` | 2D 로 돌아가 숨겨진 동안 루프가 헛돌지 않게. |

## 입력 (dashboard.html 의 `layout3D` / `vehicle3D` 가 만든다)

- 도면 단위 → m: **0.01** (실물 M14A 에서 잰 값 — 엣지 10,424개의 distance-puls(mm) ÷ 도면 길이 중앙값 9.99)
- 엣지 id `'from-to'`, 존은 HID 마스터 Full_Name, 설비는 스테이션 종류 9(오른쪽)·8(왼쪽)을 레일에서 1.7 m 띄워 1.6 m 칸마다 하나
- 차량: `from/to/ratio` 로 레일 위에, 없으면 `x,y` — 상태는 2D 와 같은 순서(7 JAM · 6 OBS · 2/8/9 정지 · 적재 · 공차)
