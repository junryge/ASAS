"""테스트 공통 — 이 폴더를 import 경로에 올린다.

real_time_amhs 는 폴더 자체가 하나의 실행 단위라 (server.py 가 같은 폴더의
sentinel/analysis 를 그냥 import 한다) 테스트도 같은 방식으로 붙인다.
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
