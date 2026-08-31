#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app_paths.py — 개발/PyInstaller 빌드 양쪽에서 동작하는 경로 헬퍼.

- bundled_dir():   번들된 리소스(예: dashboard.html) 위치
                   • 개발  : 이 파일이 있는 폴더
                   • frozen: sys._MEIPASS (PyInstaller 임시 추출 경로)
- runtime_dir():   런타임 사용자 데이터 위치 (OHT_MAP, 캐시 등)
                   • 개발  : 이 파일이 있는 폴더
                   • frozen: .exe 가 있는 폴더 (사용자가 만진다)
"""
import os
import sys
import pathlib


def bundled_dir() -> pathlib.Path:
    if getattr(sys, 'frozen', False):
        base = getattr(sys, '_MEIPASS', None)
        if base:
            return pathlib.Path(base)
        return pathlib.Path(sys.executable).parent
    return pathlib.Path(__file__).parent.resolve()


def runtime_dir() -> pathlib.Path:
    if getattr(sys, 'frozen', False):
        return pathlib.Path(sys.executable).parent.resolve()
    return pathlib.Path(__file__).parent.resolve()
