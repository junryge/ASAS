"""시험용 빈 pandas — 이 상자에 pandas 가 없을 때만 쓴다 (실제 현장에는 진짜 pandas 가 있다).

월드모델파생/logpresso_query.py 가 맨 위에서 `import pandas as pd` 를 한다. 실시간판은
그 모듈에서 서버(SERVERS) · 키(API_KEY) · 쿼리 규칙만 빌려 쓰고 pandas 는 안 쓴다 —
CSV 는 표준 csv 로 읽는다. 그래서 import 만 통과하면 된다.
"""


class DataFrame:                       # logpresso_query 의 반환형 표기(-> pd.DataFrame)가 import 때 읽힌다
    """빈 자리 — 실시간판은 쓰지 않는다."""


def read_csv(*a, **k):                 # 재생판 조회(query_oht_chunked)용 — 실시간판은 안 부른다
    raise ImportError("시험용 빈 pandas 입니다 (read_csv 없음)")


def concat(*a, **k):
    raise ImportError("시험용 빈 pandas 입니다 (concat 없음)")
