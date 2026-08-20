#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAW 복원 스크립트 — 분할 zip + base64 → 데일리 CSV 61개
========================================================
RAW/ 에는 용량 때문에 다음 형태로 보관되어 있다:
    IOS.zip.z01 + IOS.zip.z02 + IOS.zip.zIP   (분할 zip)
      └─ 안에 IOS.zip.txt (base64 인코딩된 IOS.zip)
           └─ 안에 M16A_HUBROOM_PR_2026MMDD.CSV × 61 (2026-04-01 ~ 05-31)

이 스크립트가 위 3단계를 자동으로 풀어 CSV 를 꺼낸다.

사용:
    python3 RAW/decode_raw.py --out ./RAW_APRMAY
    → ./RAW_APRMAY/M16A_HUBROOM_PR_20260401.CSV ... 20260531.CSV (61개)

검증: base64 헤더의 sha256 과 복원된 zip 을 대조한다.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = ["IOS.zip.z01", "IOS.zip.z02", "IOS.zip.zIP"]


def concat_parts(workdir):
    """분할 zip 을 순서대로 이어붙인다."""
    out = os.path.join(workdir, "IOS_full.zip")
    with open(out, "wb") as w:
        for p in PARTS:
            src = os.path.join(HERE, p)
            if not os.path.exists(src):
                sys.exit(f"분할 파일 없음: {src}")
            with open(src, "rb") as r:
                while chunk := r.read(1 << 20):
                    w.write(chunk)
    return out


def extract_b64_txt(full_zip, workdir):
    """
    concat 된 multi-part zip 에서 IOS.zip.txt 를 꺼낸다.
    파이썬 zipfile 은 multi-part 를 못 읽으므로 unzip 에 위임
    (unzip 은 'extra bytes' 경고를 내면서도 복원 가능).
    """
    r = subprocess.run(["unzip", "-o", full_zip, "-d", workdir],
                       capture_output=True, text=True)
    txt = os.path.join(workdir, "IOS.zip.txt")
    if not os.path.exists(txt):
        sys.exit(f"IOS.zip.txt 추출 실패:\n{r.stdout}\n{r.stderr}")
    return txt


def decode_b64(txt, workdir):
    """# 주석 헤더를 걷어내고 base64 디코딩 → zip. sha256 검증."""
    expect_sha = None
    b64_lines = []
    with open(txt, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                if "sha256:" in line:
                    expect_sha = line.split("sha256:")[1].strip()
                continue
            s = line.strip()
            if s:
                b64_lines.append(s)
    raw = base64.b64decode("".join(b64_lines))
    out = os.path.join(workdir, "IOS_decoded.zip")
    with open(out, "wb") as w:
        w.write(raw)
    got = hashlib.sha256(raw).hexdigest()
    if expect_sha:
        status = "OK" if got == expect_sha else "불일치!"
        print(f"  sha256 검증: {status}")
        if got != expect_sha:
            sys.exit(f"  기대 {expect_sha}\n  실제 {got}")
    return out


def main():
    ap = argparse.ArgumentParser(description="RAW 복원 (분할zip+base64 → CSV)")
    ap.add_argument("--out", default="./RAW_APRMAY", help="CSV 출력 폴더")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        print("1/4 분할 zip 이어붙이기 ...")
        full = concat_parts(work)
        print("2/4 base64 텍스트 추출 ...")
        txt = extract_b64_txt(full, work)
        print("3/4 base64 디코딩 ...")
        dec = decode_b64(txt, work)
        print("4/4 CSV 추출 ...")
        with zipfile.ZipFile(dec) as z:
            names = [n for n in z.namelist() if n.upper().endswith(".CSV")]
            z.extractall(args.out, members=names)
        print(f"\n완료: {len(names)}개 CSV → {args.out}")
        if names:
            print(f"  {min(names)} ~ {max(names)}")


if __name__ == "__main__":
    main()
