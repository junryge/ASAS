"""
demos_v1/logpresso.py - Logpresso tables, groups, filters, helper functions, and query API
"""
import os
import re
import time
import math
import uuid
import requests as req
from flask import request, jsonify
from logpresso_client import query_logpresso

from demos_v1.utils import BASE_DIR
from demos_v1.config import _EXT_CONFIG, API_TOKEN

# ============================================
# 로그프레소 (Logpresso) 직접 조회 설정
# ============================================
_lp_cfg = _EXT_CONFIG.get("logpresso", {})
LOGPRESSO_HOST = _lp_cfg.get("host", "10.40.42.27")
LOGPRESSO_PORT = _lp_cfg.get("port", 8888)
LOGPRESSO_API_KEY = _lp_cfg.get("api_key", "db1d2335-49cf-e859-3519-1ca132922e38")
LOGPRESSO_PAGE_SIZE = _lp_cfg.get("page_size", 50)
LOGPRESSO_CACHE_TTL = _lp_cfg.get("cache_ttl", 600)
LOGPRESSO_CACHE_MAX = _lp_cfg.get("cache_max", 20)

# 알려진 테이블 메타데이터
LOGPRESSO_TABLES = {
    "ATLAS_OHT_HID_OFF": {
        "desc": "HID Off 기록",
        "columns": ["FAB_ID", "MCP_NM", "VHL_ID", "HID_ID", "OFF_TIME", "FROM_ADDRESS", "TO_ADDRESS"],
    },
    "ATLAS_HID_INFO": {
        "desc": "HID 구간 정보",
        "columns": ["FAB_ID", "MCP_NM", "HID_ID", "START", "ADDRESS"],
    },
    "ATLAS_RAIL_TRAFFIC": {
        "desc": "Rail 교통 속력 데이터",
        "columns": ["createTime", "fabId", "mcpName", "railEdgeId", "velocity", "maxVelocity", "absoluteVelocity", "vhlCnt", "passCnt", "HID_ID"],
    },
    "test_currentjob_predict": {
        "desc": "알람 예측 데이터",
        "columns": ["TIME", "ALARM_DESC", "ALARM_YN"],
    },
    "ts_data_view_m14a": {
        "desc": "M14A 설비 로그",
        "columns": ["_time", "TIME_EX", "MACHINENAME", "LEVEL", "CARRIER", "TEXT"],
    },
    "ts_data_view_m14b": {
        "desc": "M14B 설비 로그",
        "columns": ["_time", "TIME_EX", "MACHINENAME", "LEVEL", "CARRIER", "TEXT"],
    },
    "ts_data_view_m16": {
        "desc": "M16 설비 로그",
        "columns": ["_time", "TIME_EX", "MACHINENAME", "LEVEL", "CARRIER", "TEXT"],
    },
    "ts_data_view_m16b": {
        "desc": "M16B 설비 로그",
        "columns": ["_time", "TIME_EX", "MACHINENAME", "LEVEL", "CARRIER", "TEXT"],
    },
}

# 테이블 카테고리 그룹 (접두사 기반 자동 분류)
LOGPRESSO_TABLE_GROUPS = [
    {"id": "atlas",    "label": "🚀 ATLAS 물류",     "prefix": ["ATLAS_", "ICPKT_ATLAS_"]},
    {"id": "fab-hid",  "label": "🏭 FAB HID",        "prefix": ["M14A_", "M14B_", "M16A_", "M16B_"]},
    {"id": "ts",       "label": "📦 Transfer(TS)",    "prefix": ["ts_"]},
    {"id": "oht",      "label": "🚗 OHT",             "prefix": ["oht_"]},
    {"id": "cs",       "label": "💻 CS 데이터",       "prefix": ["cs_"]},
    {"id": "ds",       "label": "📊 DS 데이터",       "prefix": ["ds_"]},
    {"id": "ei",       "label": "⚡ EI 데이터",       "prefix": ["ei_"]},
    {"id": "secs",     "label": "🔌 SECS",            "prefix": ["secs_"]},
    {"id": "tibrv",    "label": "📡 TIBRV",           "prefix": ["tibrv_"]},
    {"id": "bridge",   "label": "🌉 브리지",          "prefix": ["bridge_"]},
    {"id": "sys",      "label": "⚙️ 시스템",          "prefix": ["sys_"]},
    {"id": "alarm",    "label": "🔔 알람/이상감지",   "prefix": ["ALERT_", "AMOS_", "abnormal_"]},
    {"id": "msglog",   "label": "📝 메시지로그",      "prefix": ["table_msglog"]},
    {"id": "test",     "label": "🧪 테스트",          "prefix": ["test_"]},
]

# FAB별 필터 (접미사/포함 기반 — 카테고리와 별도로 교차 필터 가능)
LOGPRESSO_FAB_FILTERS = [
    {"id": "m14",  "label": "M14 (전체)",  "keywords": ["m14a", "m14b", "m14"]},
    {"id": "m14a", "label": "M14A",        "keywords": ["m14a"]},
    {"id": "m14b", "label": "M14B",        "keywords": ["m14b"]},
    {"id": "m16",  "label": "M16 (전체)",  "keywords": ["m16a", "m16b", "m16e", "m16"]},
    {"id": "m16a", "label": "M16A",        "keywords": ["m16a"]},
    {"id": "m16b", "label": "M16B",        "keywords": ["m16b"]},
]


def _get_table_group(table_name):
    """테이블명으로 카테고리 그룹 ID 반환"""
    for grp in LOGPRESSO_TABLE_GROUPS:
        for pfx in grp["prefix"]:
            if table_name.startswith(pfx):
                return grp["id"]
    return "etc"


def _get_table_fabs(table_name):
    """테이블명에 포함된 FAB ID 목록 반환 (예: ['m14a'])"""
    tl = table_name.lower()
    matched = []
    for fab in LOGPRESSO_FAB_FILTERS:
        if fab["id"] in ("m14", "m16"):
            continue  # 상위 그룹은 스킵, 개별 FAB만 태깅
        for kw in fab["keywords"]:
            if kw in tl:
                matched.append(fab["id"])
                break
    return matched


def _filter_tables_by_groups(group_ids, fab_ids=None):
    """선택된 그룹/FAB에 해당하는 테이블만 반환. 둘 다 빈 리스트면 전체 반환."""
    if not group_ids and not fab_ids:
        return dict(LOGPRESSO_TABLES)

    # FAB 키워드 목록 구축 (예: ["m14a", "m14b", "m14"])
    fab_keywords = []
    for fid in (fab_ids or []):
        for fab in LOGPRESSO_FAB_FILTERS:
            if fab["id"] == fid:
                fab_keywords.extend(fab["keywords"])

    result = {}
    for tname, tinfo in LOGPRESSO_TABLES.items():
        tl = tname.lower()

        # 조건1: 카테고리 그룹 매칭
        group_ok = _get_table_group(tname) in group_ids if group_ids else True
        # 조건2: FAB 키워드 매칭 (테이블명에 m14, m14a 등 포함)
        fab_ok = any(kw in tl for kw in fab_keywords) if fab_keywords else True

        # 둘 다 지정되면 AND, 하나만 지정되면 해당 조건만
        if group_ids and fab_keywords:
            if group_ok and fab_ok:
                result[tname] = tinfo
        elif group_ids:
            if group_ok:
                result[tname] = tinfo
        elif fab_keywords:
            if fab_ok:
                result[tname] = tinfo

    return result


def _fetch_table_fields(table_name, timeout=5):
    """테이블에서 샘플 1건을 조회하여 필드(컬럼) 목록을 추출."""
    try:
        lpql = f"table duration=5m {table_name} | limit 1"
        df, err = query_logpresso(lpql, timeout=timeout)
        if df is not None and len(df.columns) > 0:
            return list(df.columns)
    except Exception:
        pass
    return []


def _refresh_logpresso_tables():
    """서버 시작 시 system tables 조회하여 LOGPRESSO_TABLES 자동 업데이트.
    로그프레소 서버 접속 불가 시 조용히 스킵 (집에서 테스트 등).
    """
    try:
        df, err = query_logpresso("system tables", timeout=5)
        if df is None or len(df) == 0:
            # 서버 연결 안 되면 조용히 넘어감
            print(f"[Logpresso] ℹ️ 서버 미접속 → 하드코딩 {len(LOGPRESSO_TABLES)}개 사용 (정상)")
            return

        added = 0
        for _, row in df.iterrows():
            tname = str(row.get("table", row.get("name", ""))).strip()
            if not tname or tname in LOGPRESSO_TABLES:
                continue
            # 새 테이블 등록 — 필드는 나중에 조회 시 동적으로 가져옴
            LOGPRESSO_TABLES[tname] = {
                "desc": str(row.get("description", row.get("desc", tname))).strip(),
                "columns": [],
            }
            added += 1

        print(f"[Logpresso] ✅ 테이블 목록 업데이트: 기존 8개 + 서버 {added}개 추가 → 총 {len(LOGPRESSO_TABLES)}개")
    except Exception:
        print(f"[Logpresso] ℹ️ 서버 미접속 → 하드코딩 {len(LOGPRESSO_TABLES)}개 사용 (정상)")

# 쿼리 결과 캐시 {query_id: {"df": DataFrame, "ts": timestamp, "lpql": str}}
_logpresso_cache = {}


def _logpresso_cache_cleanup():
    """만료된 캐시 제거"""
    now = time.time()
    expired = [k for k, v in _logpresso_cache.items() if now - v["ts"] > LOGPRESSO_CACHE_TTL]
    for k in expired:
        del _logpresso_cache[k]
    while len(_logpresso_cache) > LOGPRESSO_CACHE_MAX:
        oldest = min(_logpresso_cache, key=lambda k: _logpresso_cache[k]["ts"])
        del _logpresso_cache[oldest]


def classify_logpresso_intent(query):
    """로그프레소 관련 질문의 의도를 4가지로 분류
    Returns: 'table_list' | 'table_schema' | 'execute' | 'explain'
    """
    q = query.strip()

    table_list_kw = ["테이블 목록", "어떤 테이블", "테이블 뭐", "테이블 리스트", "테이블 종류",
                     "테이블 있", "테이블 알려", "테이블 보여"]
    if any(p in q for p in table_list_kw):
        return "table_list"

    schema_kw = ["구조", "컬럼", "필드", "스키마", "뭐가 있", "어떤 데이터", "어떤 컬럼"]
    if any(p in q for p in schema_kw):
        return "table_schema"

    exec_kw = ["보여줘", "조회해", "찾아줘", "검색해", "확인해줘", "가져와", "뽑아",
               "조회 해", "몇건", "몇개", "몇 건", "몇 개", "데이터 줘",
               "로그 줘", "결과 줘", "실행해", "돌려"]
    if any(p in q for p in exec_kw):
        return "execute"

    return "explain"


## query_logpresso → logpresso_client.py로 이동 (import 참조)


_LPQL_BLOCKED_COMMANDS = {"drop", "delete", "insert", "import", "create", "grant", "revoke", "update", "set "}


def validate_lpql_readonly(lpql):
    """LPQL 쿼리가 읽기 전용인지 검증"""
    lower = lpql.lower().strip()
    for cmd in _LPQL_BLOCKED_COMMANDS:
        if lower.startswith(cmd) or f"| {cmd}" in lower or f"|{cmd}" in lower:
            return f"보안 차단: '{cmd.strip()}' 명령은 실행할 수 없습니다. 읽기 전용 쿼리만 허용됩니다."
    return None


def extract_lpql_from_response(text):
    """LLM 응답에서 ```lpql ... ``` 또는 ``` ... ``` 코드블록 추출"""
    m = re.search(r"```(?:lpql|LPQL)\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return _clean_lpql(m.group(1).strip())
    m = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if m:
        candidate = m.group(1).strip()
        lpql_indicators = ["table ", "fulltext ", "stream ", "| fields", "| search", "| sort", "| limit", "| eval", "| stats"]
        if any(ind in candidate.lower() for ind in lpql_indicators):
            return _clean_lpql(candidate)
    return None


def _clean_lpql(lpql):
    """LPQL에서 주석(-- 또는 #) 제거 → 로그프레소 서버 500 에러 방지"""
    lines = lpql.split("\n")
    cleaned = []
    for line in lines:
        # -- 주석 제거
        line = re.sub(r'\s*--.*$', '', line)
        # # 주석 제거 (단, 문자열 안의 # 은 보존)
        line = re.sub(r'\s*#(?!["\']).*$', '', line)
        line = line.strip()
        if line:
            cleaned.append(line)
    return " ".join(cleaned)



# ============================================

def _llm_generate_lpql(user_query, history=None):
    """LLM을 호출하여 자연어 -> LPQL 쿼리 생성"""
    from demos_v1.skills import load_skill_content
    from demos_v1.models import MODEL_REGISTRY, FALLBACK_CHAINS
    from datetime import datetime
    today = datetime.now().strftime("%Y%m%d")

    # 사용자 질문에서 관련 테이블 그룹 자동 감지
    _q_lower = user_query.lower()
    _auto_groups = []
    for grp in LOGPRESSO_TABLE_GROUPS:
        _kws = [grp["id"]] + [p.rstrip("_").lower() for p in grp["prefix"]]
        if any(kw in _q_lower for kw in _kws):
            _auto_groups.append(grp["id"])
    # FAB 필터 감지 (M14, M16, M14A, M16B 등)
    _auto_fabs = []
    for fab in LOGPRESSO_FAB_FILTERS:
        if fab["id"] in _q_lower or fab["label"].lower() in _q_lower:
            _auto_fabs.append(fab["id"])
    # 테이블명이 직접 언급된 경우도 감지
    _direct_tables = {}
    for tname, tinfo in LOGPRESSO_TABLES.items():
        if tname.lower() in _q_lower:
            _direct_tables[tname] = tinfo
    # 관련 그룹 테이블 + FAB 필터 + 직접 언급 테이블 합치기
    _relevant = _filter_tables_by_groups(_auto_groups, _auto_fabs)
    _relevant.update(_direct_tables)
    # 관련 테이블이 없으면 전체 사용 (빈 columns 제외하지 않음)
    _target_tables = _relevant if _relevant else LOGPRESSO_TABLES

    table_info = "\n".join(
        f"- {name}: {info['desc']} (컬럼: {', '.join(info['columns'])})"
        for name, info in _target_tables.items()
    )

    skill_content = load_skill_content("logpresso-query") or ""

    system_prompt = f"""당신은 로그프레소 LPQL 쿼리 생성 전문가입니다.
사용자의 자연어 요청을 실행 가능한 LPQL 쿼리로 변환하세요.

## 규칙
1. 반드시 ```lpql 코드블록 안에 **순수 쿼리만** 출력하세요. **코드블록 안에 주석(--, #, //)을 절대 넣지 마세요.** 로그프레소 서버가 주석을 파싱하지 못해 오류가 발생합니다.
2. 쿼리의 각 부분(테이블, 조건, 파이프 명령)에 대한 설명은 **코드블록 바깥에** 줄별로 적어주세요.
3. 오늘 날짜: {today} (시간 형식: yyyyMMddHHmmss)
4. 어제 = {today} 기준 하루 전, 이번 주 = 최근 7일
5. **기간은 from/to 형식을 기본으로 사용하세요.** 사용자가 기간을 지정하지 않으면 오늘 하루(from={today}000000 to={today}235959)를 기본값으로 사용하세요. 사용자가 "최근 1시간" 같이 말하면 duration=1h도 가능합니다.
6. 읽기 전용 쿼리만 생성하세요 (INSERT/DELETE/DROP/CREATE 금지).
7. **캐리어/장비 추적, 특정 키워드 검색, 여러 테이블 동시 조회 시 `fulltext`를 우선 사용하세요.**
8. fulltext에서 여러 테이블 지정: `fulltext ... from 테이블1, 테이블2`
9. fulltext 안에서 필드 조건 직접 사용 가능: `(LEVEL=="ERROR") and (CARRIER=="xxx")`
10. limit에 오프셋 지정 가능: `limit 0 1000`
11. 행 순번: `eval No = seq() + 0`

## 중요: 사용자가 요청한 것만 쿼리에 포함하세요
- 사용자가 특정 컬럼을 요청하지 않았으면 `| fields`를 넣지 마세요 (전체 컬럼 반환).
- 사용자가 필터 조건을 요청하지 않았으면 `| search`를 넣지 마세요.
- 사용자가 정렬을 요청하지 않았으면 `| sort`를 넣지 마세요.
- 최소한의 쿼리만 생성하세요. 불필요한 파이프 명령을 추가하지 마세요.

## 출력 형식 예시
아래처럼 쿼리와 설명을 분리하세요:

```lpql
table from=20260327000000 to=20260327235959 ts_data_view_m14a | limit 5
```

- `table from=... to=...`: 오늘 하루 기간 지정
- `ts_data_view_m14a`: M14A 설비 로그 테이블
- `| limit 5`: 최대 5건 조회

## 사용 가능한 테이블
{table_info}

## LPQL 문법 참고
{skill_content[:6000]}
"""

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history[-4:])
    messages.append({"role": "user", "content": user_query})

    headers = {"Content-Type": "application/json"}
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"

    # 기존 FALLBACK_CHAINS 활용: glm-5 → 체인 순서대로 폴백
    primary_key = "glm-5"
    chain_keys = [primary_key] + FALLBACK_CHAINS.get(primary_key, [])
    # vision/reranker 모델 제외 (텍스트 전용만)
    chain_keys = [k for k in chain_keys if k in MODEL_REGISTRY
                  and "vision" not in MODEL_REGISTRY[k].get("capabilities", set())
                  and "rerank" not in MODEL_REGISTRY[k].get("capabilities", set())]

    tried = []
    for reg_key in chain_keys:
        reg = MODEL_REGISTRY[reg_key]
        tried.append(reg["model"])
        try:
            resp = req.post(
                reg["url"],
                headers=headers,
                json={
                    "model": reg["model"],
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 2048,
                    "stream": False,
                },
                timeout=60,
                verify=False,
            )
            resp.raise_for_status()
            result = resp.json()
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content")
                if content and content.strip():
                    if reg_key != primary_key:
                        print(f"[Logpresso LLM] 폴백 성공: {reg['model']}")
                    return content
                else:
                    print(f"[Logpresso LLM] {reg['model']} → 빈 응답, 다음 모델 시도...")
                    continue
        except Exception as e:
            print(f"[Logpresso LLM] {reg['model']} 오류: {e} → 다음 모델 시도...")
            continue

    print(f"[Logpresso LLM] 모든 모델 실패: {', '.join(tried)}")
    return None




def register_logpresso_routes(app):
    """Register logpresso API routes."""

    @app.route("/api/logpresso/query", methods=["POST"])
    def api_logpresso_query():
        """로그프레소 자연어 쿼리 엔드포인트 (4가지 모드 자동 분류)

        Input:
          - query: 자연어 질문
          - history: 대화 히스토리 (선택)
          - mode: 강제 모드 지정 (선택: table_list, table_schema, execute, explain)
          - lpql: 직접 LPQL 전달 시 LLM 스킵 (선택)
        """
        import pandas as pd

        data = request.json or {}
        user_query = data.get("query", "").strip()
        history = data.get("history", [])
        forced_mode = data.get("mode", "")
        direct_lpql = data.get("lpql", "").strip()

        if not user_query and not direct_lpql:
            return jsonify({"error": "query 또는 lpql 파라미터가 필요합니다."}), 400

        if forced_mode:
            mode = forced_mode
        elif direct_lpql:
            mode = "execute"
        else:
            mode = classify_logpresso_intent(user_query)

        # ── 모드 1: 테이블 목록 (서버에서 동적 조회, 실패 시 하드코딩 폴백) ──
        if mode == "table_list":
            # 서버에서 직접 테이블 목록 조회 시도
            df, err = query_logpresso("system tables", timeout=5)
            if df is not None and len(df) > 0:
                server_tables = df.to_dict("records")
                # 각 테이블의 필드값도 함께 조회 (빈 columns인 테이블만)
                for st in server_tables:
                    tname = st.get("table", st.get("name", ""))
                    if tname and tname in LOGPRESSO_TABLES:
                        cached_cols = LOGPRESSO_TABLES[tname].get("columns", [])
                        if cached_cols:
                            st["fields"] = cached_cols
                        else:
                            fields = _fetch_table_fields(tname, timeout=3)
                            if fields:
                                LOGPRESSO_TABLES[tname]["columns"] = fields
                            st["fields"] = fields
                        st["field_count"] = len(st.get("fields", []))
                    elif tname:
                        fields = _fetch_table_fields(tname, timeout=3)
                        st["fields"] = fields
                        st["field_count"] = len(fields)
                return jsonify({
                    "mode": "table_list",
                    "source": "server",
                    "tables": server_tables,
                    "total": len(server_tables),
                    "columns": list(df.columns),
                    "message": f"로그프레소 서버에서 조회: 총 {len(server_tables)}개 테이블 (필드 포함)",
                })

            # 서버 연결 실패 시 하드코딩 폴백 (필드 정보 포함)
            tables = []
            for name, info in LOGPRESSO_TABLES.items():
                cols = info["columns"]
                # 빈 columns → 서버에서 동적 조회 시도
                if not cols:
                    cols = _fetch_table_fields(name, timeout=3)
                    if cols:
                        info["columns"] = cols
                tables.append({
                    "table": name,
                    "desc": info["desc"],
                    "columns": cols,
                    "column_count": len(cols),
                })
            return jsonify({
                "mode": "table_list",
                "source": "local",
                "tables": tables,
                "total": len(tables),
                "message": f"로컬 등록 테이블: {len(tables)}개 (필드 포함)",
            })

        # ── 모드 2: 테이블 구조 확인 ──
        if mode == "table_schema":
            matched_table = None
            for tname in LOGPRESSO_TABLES:
                if tname.lower() in user_query.lower():
                    matched_table = tname
                    break

            if not matched_table:
                return jsonify({
                    "mode": "table_schema",
                    "error": "테이블명을 인식할 수 없습니다.",
                    "available_tables": list(LOGPRESSO_TABLES.keys()),
                }), 400

            info = LOGPRESSO_TABLES[matched_table]
            sample_data = []
            sample_lpql = f"table duration=5m {matched_table} | limit 5"
            df, _err = query_logpresso(sample_lpql, timeout=30)
            if df is not None and len(df) > 0:
                sample_data = df.head(5).to_dict("records")
                # 빈 columns → 샘플 조회 결과에서 필드 자동 보충
                if not info["columns"] and len(df.columns) > 0:
                    info["columns"] = list(df.columns)

            return jsonify({
                "mode": "table_schema",
                "table": matched_table,
                "desc": info["desc"],
                "columns": info["columns"],
                "column_count": len(info["columns"]),
                "sample_data": sample_data,
                "sample_lpql": sample_lpql,
            })

        # ── 모드 3: 쿼리 설명 (explain) — 쿼리만 생성, 실행 안 함 ──
        if mode == "explain":
            llm_response = _llm_generate_lpql(user_query, history)
            if not llm_response:
                return jsonify({"mode": "explain", "error": "LLM 응답 실패"}), 500

            lpql = extract_lpql_from_response(llm_response)
            return jsonify({
                "mode": "explain",
                "explanation": llm_response,
                "lpql": lpql,
            })

        # ── 모드 4: 직접 조회 (execute) — 무조건 5건만 미리보기 ──
        lpql = direct_lpql
        llm_explanation = ""

        if not lpql:
            llm_response = _llm_generate_lpql(user_query, history)
            if not llm_response:
                return jsonify({"mode": "execute", "error": "LLM에서 LPQL 생성 실패"}), 500

            llm_explanation = llm_response
            lpql = extract_lpql_from_response(llm_response)

            if not lpql:
                return jsonify({
                    "mode": "execute",
                    "error": "LLM 응답에서 LPQL 쿼리를 추출할 수 없습니다.",
                    "llm_response": llm_response,
                }), 400

        # 시간 범위 없으면 오늘 하루 기본 적용
        if not re.search(r'(duration|from|to)\s*=', lpql, re.IGNORECASE):
            from datetime import datetime
            _today = datetime.now().strftime("%Y%m%d")
            lpql = re.sub(r'^(table|fulltext)\s+', rf'\1 from={_today}000000 to={_today}235959 ', lpql, flags=re.IGNORECASE)

        # limit 강제 5건 적용
        lpql_lower = lpql.lower()
        if "| limit" in lpql_lower or "| head" in lpql_lower:
            lpql = re.sub(r'\|\s*(limit|head)\s+\d+(\s+\d+)?', '| limit 5', lpql, flags=re.IGNORECASE)
        else:
            lpql = lpql.rstrip() + " | limit 5"

        # 보안 검증
        sec_error = validate_lpql_readonly(lpql)
        if sec_error:
            return jsonify({"mode": "execute", "error": sec_error, "lpql": lpql}), 403

        # 쿼리 실행
        df, err_detail = query_logpresso(lpql, timeout=180)
        if df is None:
            error_msg = "Logpresso 조회 실패"
            if err_detail:
                error_msg += f": {err_detail.get('reason', '알 수 없는 오류')}"
            return jsonify({
                "mode": "execute",
                "error": error_msg,
                "lpql": lpql,
                "explanation": llm_explanation,
                "error_detail": err_detail,
            }), 502

        total_rows = len(df)

        # 캐시에 저장 (전체 데이터)
        _logpresso_cache_cleanup()
        query_id = str(uuid.uuid4())[:8]
        _logpresso_cache[query_id] = {"df": df, "ts": time.time(), "lpql": lpql}

        # 미리보기: 5건만 반환
        preview_data = df.head(5).to_dict("records")

        # 쿼리에서 테이블명 추출 → 필드 정보 포함
        _exec_table = None
        _exec_table_match = re.search(r'(?:table|fulltext)\s+(?:\S+=\S+\s+)*(\S+)', lpql, re.IGNORECASE)
        if _exec_table_match:
            _exec_table = _exec_table_match.group(1).strip()
        _exec_fields = list(df.columns)
        if _exec_table and _exec_table in LOGPRESSO_TABLES:
            if not LOGPRESSO_TABLES[_exec_table]["columns"] and _exec_fields:
                LOGPRESSO_TABLES[_exec_table]["columns"] = _exec_fields
            elif LOGPRESSO_TABLES[_exec_table]["columns"]:
                _exec_fields = LOGPRESSO_TABLES[_exec_table]["columns"]

        return jsonify({
            "mode": "execute",
            "success": True,
            "lpql": lpql,
            "explanation": llm_explanation,
            "query_id": query_id,
            "table": _exec_table,
            "columns": list(df.columns),
            "table_fields": _exec_fields,
            "total_rows": total_rows,
            "preview_data": preview_data,
            "preview_rows": min(5, total_rows),
            "message": f"조회 완료: 총 {total_rows}건 (미리보기 {min(5, total_rows)}건)" if total_rows > 0 else "결과 0건 (데이터가 없습니다. duration을 늘려보세요.)",
        })


    @app.route("/api/logpresso/query/page", methods=["POST"])
    def api_logpresso_query_page():
        """페이지네이션: 캐시된 결과에서 특정 페이지 반환 (50건씩)"""
        data = request.json or {}
        query_id = data.get("query_id", "")
        page = max(1, data.get("page", 1))

        if not query_id or query_id not in _logpresso_cache:
            return jsonify({"error": "query_id가 유효하지 않거나 캐시가 만료되었습니다."}), 404

        cache = _logpresso_cache[query_id]
        cache["ts"] = time.time()

        df = cache["df"]
        total_rows = len(df)
        total_pages = max(1, math.ceil(total_rows / LOGPRESSO_PAGE_SIZE))
        page = min(page, total_pages)

        start = (page - 1) * LOGPRESSO_PAGE_SIZE
        end = start + LOGPRESSO_PAGE_SIZE
        page_data = df.iloc[start:end].to_dict("records")

        return jsonify({
            "query_id": query_id,
            "lpql": cache["lpql"],
            "columns": list(df.columns),
            "data": page_data,
            "page": page,
            "page_size": LOGPRESSO_PAGE_SIZE,
            "total_rows": total_rows,
            "total_pages": total_pages,
            "row_range": f"{start + 1}~{min(end, total_rows)}",
        })


    @app.route("/api/logpresso/tables", methods=["GET"])
    def api_logpresso_tables():
        """등록된 테이블 목록 반환 (카테고리/FAB 필터: ?groups=atlas,ts&fabs=m14a,m16)"""
        group_filter = request.args.get("groups", "").strip()
        fab_filter = request.args.get("fabs", "").strip()
        group_ids = [g.strip() for g in group_filter.split(",") if g.strip()] if group_filter else []
        fab_ids = [f.strip() for f in fab_filter.split(",") if f.strip()] if fab_filter else []
        filtered = _filter_tables_by_groups(group_ids, fab_ids)
        tables = []
        for name, info in filtered.items():
            tables.append({"table": name, "desc": info["desc"], "columns": info["columns"], "group": _get_table_group(name), "fabs": _get_table_fabs(name)})
        groups = [{"id": g["id"], "label": g["label"], "count": sum(1 for t in LOGPRESSO_TABLES if _get_table_group(t) == g["id"])} for g in LOGPRESSO_TABLE_GROUPS]
        etc_count = sum(1 for t in LOGPRESSO_TABLES if _get_table_group(t) == "etc")
        if etc_count:
            groups.append({"id": "etc", "label": "📁 기타", "count": etc_count})
        fabs = [{"id": f["id"], "label": f["label"]} for f in LOGPRESSO_FAB_FILTERS]
        return jsonify({"tables": tables, "total": len(tables), "total_all": len(LOGPRESSO_TABLES), "groups": groups, "fabs": fabs})


