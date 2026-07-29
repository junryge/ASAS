# -*- coding: utf-8 -*-
"""
AMHS Daily Report System - FastAPI 서버
실행: python server.py  →  http://localhost:8000

폴더 구조:
  server.py
  config.json                      ← 암호/포트 설정 (여기서 수정)
  reports_db.json                  ← 리포트 데이터 (자동 생성)
  INDEX/Daily_Report_System.html   ← 웹 화면

config.json:
  editPassword  : 완료 리포트 "수정" 암호
  adminPassword : 완료 리포트 "삭제" 관리자 암호
  host / port   : 서버 주소·포트
※ config.json 수정 후 서버 재시작하면 적용 (브라우저 새로고침)
"""
import json
import threading
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

BASE = Path(__file__).resolve().parent
HTML = BASE / "INDEX" / "Daily_Report_System.html"
GUIDE = BASE / "INDEX" / "guide.html"          # 사용법 가이드 팝업 화면
IMAGE_DIR = BASE / "INDEX" / "IMAGE"           # 가이드 이미지(A1~A4.PNG) 폴더
DB = BASE / "reports_db.json"
CONFIG = BASE / "config.json"
LOCK = threading.Lock()

DEFAULT_CONFIG = {
    "editPassword": "AMHS1234",
    "adminPassword": "AMHS1234",
    "host": "0.0.0.0",
    "port": 8000,
}


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG.exists():
        try:
            user = json.loads(CONFIG.read_text(encoding="utf-8"))
            if isinstance(user, dict):
                cfg.update(user)
        except Exception as e:
            print(f"[경고] config.json 읽기 실패, 기본값 사용: {e}")
    else:
        CONFIG.write_text(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[안내] config.json 기본 파일을 생성했습니다.")
    return cfg


def load_db() -> dict:
    if DB.exists():
        try:
            data = json.loads(DB.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


app = FastAPI(title="AMHS Daily Report System", version="1.1")


@app.get("/")
def index():
    if not HTML.exists():
        return JSONResponse({"error": "INDEX/Daily_Report_System.html not found"}, status_code=404)
    return FileResponse(HTML, media_type="text/html")


@app.get("/guide.html")
def guide():
    """제목 옆 '가이드' 버튼이 여는 사용법 팝업 화면."""
    if not GUIDE.exists():
        return JSONResponse({"error": "INDEX/guide.html not found"}, status_code=404)
    return FileResponse(GUIDE, media_type="text/html")


@app.get("/IMAGE/{name}")
def guide_image(name: str):
    """가이드 이미지(A1.PNG ~ A4.PNG) 제공."""
    path = (IMAGE_DIR / name).resolve()
    if IMAGE_DIR.resolve() not in path.parents or not path.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(path)


@app.get("/api/config")
def get_config():
    cfg = load_config()  # 매 요청마다 읽음 → config.json 수정 후 새로고침만 해도 적용
    return {"editPassword": cfg["editPassword"], "adminPassword": cfg["adminPassword"]}


@app.get("/api/reports")
def get_reports():
    with LOCK:
        return JSONResponse(load_db())


@app.put("/api/reports")
async def put_reports(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)
    if not isinstance(data, dict):
        return JSONResponse({"ok": False, "error": "object expected"}, status_code=400)
    with LOCK:
        DB.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "count": len(data)}


@app.get("/health")
def health():
    return {"ok": True, "reports": len(load_db())}


if __name__ == "__main__":
    cfg = load_config()
    print("=" * 50)
    print("  AMHS Daily Report System")
    print(f"  브라우저에서 열기 →  http://localhost:{cfg['port']}")
    print("  암호 설정: config.json")
    print("=" * 50)
    uvicorn.run(app, host=cfg["host"], port=int(cfg["port"]))
