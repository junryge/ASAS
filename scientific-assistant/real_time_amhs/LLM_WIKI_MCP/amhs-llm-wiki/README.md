# AMHS LLM-WIKI 지식정보 시스템

Andrej Karpathy의 [llm-wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
([긱뉴스](https://news.hada.io/topic?id=28208)) 스펙을 AMHS 현장에 맞춘 지식 시스템.

담당자들이 **양식에 맞게 작성**하고, MD/PDF/이미지/TXT/CSV 원본을 넣으면
LLM이 **관련 페이지까지 같이 갱신**해서 지식이 복리로 쌓인다.

- Python + HTML (Flask 모놀리식 단일 파일, 외부 CDN 없음) — 브라우저로 접속
- LLM은 **Claude 아님, OpenAI 호환 API** — 사내 게이트웨이 주소를 설정 화면에 입력
- 폐쇄망 기준: pip-only, Node/Docker 불필요
- 담당 구분 = **FAB** (공통 / M14 / M14B / M16A / M16B / M16HUB), 설비(OHT·AGV·CNV·MCS)는 태그

## 1. 설치 / 실행

```bash
pip install flask          # 필수
pip install pypdf          # 선택: PDF 텍스트 추출
pip install numpy          # 선택: 벡터 연산 가속 (없어도 동작)
python app.py              # http://0.0.0.0:8100
```

> 하이브리드 검색·리랭커는 **추가 설치 없이** 사내 OpenAI 호환 API로 동작한다.
> 로컬 모델을 쓰고 싶을 때만 `pip install sentence-transformers`.

| 환경변수 | 기본값 | 설명 |
|---|---|---|
| `LLM_WIKI_PORT` | 8100 | 웹 포트 |
| `LLM_WIKI_HOST` | 0.0.0.0 | 바인드 주소 |
| `LLM_WIKI_DATA` | ./data | 데이터 디렉토리 |
| `LLM_WIKI_SECRET` | (랜덤) | 세션 키 — 운영 시 고정값 권장 |

폐쇄망 반입: 폴더 zip → base64 → 내부망 → 압축 해제. 전부 순수 파이썬이라 휠 반입도 간단.

## 2. 구조 — 카파시 3-layer

```
data/
├─ sources/<FAB>/               원본 자료 (불변 — 진실의 출처)
├─ wiki/
│   ├─ index.md                 전체 카탈로그 (자동 생성)
│   ├─ log.md                   활동 로그, append-only (자동 생성)
│   └─ <FAB>/<타입>/*.md        지식 페이지 (프론트매터 포함)
├─ schema/schema.md             작성 규칙 (원문의 CLAUDE.md 역할)
└─ wiki.db                      SQLite
```

**페이지 타입**: `concept`(주제·절차) / `entity`(호기·구간·시스템) / `source`(원본 1건 요약)

## 3. 연산 (카파시 스펙)

| 연산 | 화면 | 하는 일 |
|---|---|---|
| **ingest** | 소스 상세 → [Ingest 실행] | ① 소스 요약 페이지 생성 ② **관련 기존 페이지 5~15개 갱신안 생성** ③ 검토 후 선택 적용 ④ 로그 기록 |
| **query** | 담당 노트북 / [질문] | 위키·소스에서 근거 검색 → 출처 명시 답변 → 좋은 답변은 노트로 저장 |
| **lint** | [린트] | 깨진 링크·고아 페이지·빈 요약·180일 미갱신·**미반영 소스** + LLM 모순/중복 점검 |
| **index** | [카탈로그] | 타입·FAB별 한줄요약 카탈로그 (index.md 자동 생성) |
| **log** | [로그] | `## [DATE] op \| Title` 형식 append-only 기록 |

> ingest가 이 시스템의 핵심이다. 소스 1건이 위키 여러 페이지에 퍼지면서 지식이 누적된다.
> **LLM이 자동 반영하지 않는다** — 전부 담당자가 체크한 것만 적용된다.

## 3-2. 검색 엔진 (하이브리드 + 리랭커)

**기본값은 BM25 단독**이다. 아무것도 설정 안 하면 지금까지와 똑같이 동작한다.
설정(설정 → 검색)에서 켜면 3단 파이프라인이 된다:

```
질문 → ① BM25(어휘) + Dense(의미) → RRF 융합 → ② Reranker → ③ 상위 K개를 LLM에
```

| 단계 | 왜 필요한가 | 백엔드 선택지 |
|---|---|---|
| **BM25** | `E101`·`M16A`·사내 약어처럼 **정확한 토큰**을 잡는다. 임베딩이 늘 놓치는 부분 | 내장 (stdlib) |
| **Dense** | "왜 자꾸 밀리나" 같이 **표현이 다른 의미 질문**을 잡는다 | OpenAI 호환 `/v1/embeddings` (권장) / 로컬 sentence-transformers |
| **RRF** | 두 결과를 점수 정규화 없이 **순위만으로** 합친다 | 내장 |
| **Reranker** | 후보 30개 중 진짜 쓸 5개만 남겨 **컨텍스트 오염을 줄인다**. 투자 대비 효과 최대 | **LLM 리랭커(설치 불필요)** / `/v1/rerank` / 로컬 CrossEncoder |

**청킹**: 페이지를 `##` 섹션 단위로 자른다. 검색이 페이지가 아니라 **해당 섹션**을 짚어서
LLM 컨텍스트에 넣으므로 긴 페이지에서도 정확도가 유지된다.

**장애 내성**: 임베딩·리랭커 서버가 죽어도 검색은 BM25로 자동 폴백된다. 예외로 페이지가 죽지 않는다.
numpy가 없으면 순수 파이썬으로 벡터 연산한다(수천 청크까진 체감 차이 없음).

**권장 도입 순서**
1. **LLM 리랭커부터** — 설치할 게 없다. `rerank_backend=llm`만 켜면 끝
2. 평가로 효과 확인 → 좋으면 전용 리랭커(Qwen3-Reranker-0.6B 등)로 교체
3. 그다음 임베딩(BGE-M3 등) 붙여서 하이브리드로

> 임베딩 모델이나 청크 크기를 바꾸면 **[검색엔진] → 재색인**을 반드시 돌려라.
> 페이지 저장 시엔 자동으로 증분 갱신된다.

## 3-3. 평가 하네스

**감으로 튜닝하지 않기 위한 화면.** 담당자들이 실제 묻는 질문 30~50개 + 정답 페이지를
골든셋으로 등록해두면(웹에서 추가 또는 CSV 임포트), 설정을 바꿀 때마다 숫자로 비교된다.

| 지표 | 뭘 보나 |
|---|---|
| **Hit@K** | 정답 페이지를 K개 안에 찾았나 |
| **MRR** | 몇 번째로 찾았나 (1등이면 1.0) |
| **Ctx 정밀도** | 가져온 문서 중 관련 있는 비율 |
| **Faithfulness** | 답변이 근거로 뒷받침되나 (환각 검출, LLM-as-judge) |
| **Answer Rel.** | 질문에 실제로 답했나 (LLM-as-judge) |

`mode=bm25`로 **기준선**을 먼저 찍어두고, 설정 바꾼 뒤 다시 돌려 비교하면 된다.
실행 이력이 남으므로 "리랭커 켠 후"처럼 라벨을 달아두면 추적된다.

## 4. 운영 흐름

1. **설정**에서 LLM 주소 입력 + FAB/양식을 조직에 맞게 조정
2. 담당자에게 URL 배포 → 각자 FAB 노트북에서:
   - 자료 업로드 → **Ingest 실행** → 검토 후 적용
   - **양식으로 작성** 버튼 → 섹션별 폼 채우기 (LLM 없이도 됨)
   - 소스 체크 → **질문** → 좋은 답변은 노트로 저장
3. **린트** 주기적으로 돌려서 품질 관리
4. **내보내기** → 담당별 MD zip / combined.md (RAG·파인튜닝·이관용)

## 5. LLM 설정

설정 화면에 OpenAI 호환 주소 입력 (끝에 `/v1`까지):

```
API Base URL: http://<사내 추론서버 또는 게이트웨이>/v1
모델명:       <서버에 로드된 모델 ID>
API Key:      (필요한 경우만)
```

`/v1/chat/completions`만 사용. vLLM·llama.cpp server·사내 게이트웨이 전부 호환.
**LLM 없이도** 작성·검색·카탈로그·린트(규칙)·내보내기는 다 동작한다.

## 6. MCP 연동

**① 동봉된 MCP 서버** (웹앱 꺼져 있어도 DB 직접 읽어서 동작)

```bash
pip install "mcp>=1.27,<2"
python mcp_server.py        # streamable-http, http://<주소>:8020/mcp
```

도구: `listDomains` / `searchWiki(query, topK, domainSlug)` / `readPage(pageId)` /
`listSources(domainSlug)` / `readSource(sourceId)`

`searchWiki`는 웹앱과 **동일한 하이브리드+리랭커 파이프라인**을 그대로 탄다.
결과에 매칭된 섹션 본문(`snippet`)이 함께 오므로 에이전트가 페이지 전체를 다시 읽을 필요가 없다.

**② JSON API**

```
GET  /api/health · /api/domains · /api/pages?domain=<slug> · /api/page/<id>
GET  /api/search?q=<검색어>&k=5 · /api/sources · /api/source/<id>
POST /api/ask   {"question": "..."}
```

## 7. 파일 구성

| 파일 | 설명 |
|---|---|
| `app.py` | 웹앱 전체 (Flask + 템플릿 + BM25 + 마크다운 렌더러 + ingest/lint + LLM 클라이언트) |
| `mcp_server.py` | MCP 서버 (FastMCP, streamable-http :8020) |
| `requirements.txt` | 의존성 |

## 8. 기존 설치 업그레이드

`pages` 테이블에 `ptype` / `source_ids` 컬럼이 자동 추가된다(마이그레이션 내장).
기존 페이지는 전부 `concept`으로 들어간다. `data/` 그대로 두고 app.py만 교체하면 된다.
