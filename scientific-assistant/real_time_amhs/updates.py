"""업데이트 내역 — 날짜 · 버전 · 내용 (관제 'UI대쉬보드' 옆 탭).

고객 2026-10-06: "UI대쉬보드 옆에 업데이트 내역 쓸 수 있게 해줘. 비밀번호는 숨김
활성화와 동일하게 하고, 업데이트 내역 기록하고 저장하는 데 비밀번호 필요 —
날짜, 버전, 내용".

★보는 것은 누구나, **저장·지우기만 비밀번호**다. 비밀번호는 **서버가** 확인한다 —
  화면에서만 보면 주소창으로 API 를 바로 부르면 그만이다. (숨김 모드는 화면 가림이라
  그렇게 둬도 되지만, 이건 파일에 남는 저장이다.)
★비밀번호 글자는 어디에도 두지 않는다 — SHA-256 값만 둔다. dashboard.html 의
  HIDE_PW_SHA 와 **같은 값**이어야 한다 (tests/test_updates.py 가 본다).
  비밀번호를 바꾸면 **둘 다** 바꾼다:
      python -c "import hashlib;print(hashlib.sha256('새비번'.encode()).hexdigest())"
★화면은 비밀번호 글자를 그대로 보낸다 (해시를 보내면 안 된다 — 해시는 화면 소스에
  보이므로, 해시를 받아 주면 소스를 연 사람 누구나 저장할 수 있다).
★저장은 data/updates.json 하나 — data/ 는 배포 때 덮어쓰지 않는 자리다.
  반쯤 쓴 파일이 남지 않게 .part 에 쓰고 바꿔 끼운다.
  ★읽다가 깨진 파일이면 **저장하지 않는다** — 빈 목록으로 보고 새로 쓰면 그동안
    적어 둔 내역이 통째로 사라진다.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import uuid
from datetime import datetime

# dashboard.html 의 HIDE_PW_SHA 와 같은 값 (숨김 해제 비밀번호)
PW_SHA = "2af6268c371a817aef7f2773f842a78626a735dd1cc7efea9af5e00f6e83546c"
FILE = "updates.json"
MAX_VER = 40          # 버전 글자 수
MAX_TEXT = 5000       # 내용 글자 수
_LOCK = threading.Lock()


def path(cfg: dict | None = None) -> str:
    from store_csv import data_dir
    return os.path.join(data_dir(cfg), FILE)


def pw_ok(pw) -> bool:
    """숨김 해제와 같은 비밀번호인가 — 글자 비교 대신 해시를 시간 일정하게 비교한다."""
    if not isinstance(pw, str) or not pw:
        return False
    return hmac.compare_digest(hashlib.sha256(pw.encode("utf-8")).hexdigest(), PW_SHA)


def _read(p: str) -> list[dict]:
    """파일 → 목록. 없으면 []. ★깨졌으면 ValueError — 덮어쓰지 않게 위로 알린다."""
    if not os.path.isfile(p):
        return []
    with open(p, encoding="utf-8") as f:
        items = json.load(f)
    if not isinstance(items, list):
        raise ValueError("목록이 아닙니다")
    return [x for x in items if isinstance(x, dict)]


def _write(p: str, items: list[dict]) -> None:
    with open(p + ".part", "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    os.replace(p + ".part", p)


def _order(items: list[dict]) -> list[dict]:
    """날짜 최근이 위, 같은 날이면 나중에 저장한 것이 위."""
    return sorted(items, key=lambda x: (str(x.get("date") or ""), str(x.get("saved") or "")),
                  reverse=True)


def load(cfg: dict | None = None) -> tuple[list[dict], str]:
    """(목록, 오류). 오류가 있으면 목록은 비어 있다."""
    p = path(cfg)
    try:
        with _LOCK:
            return _order(_read(p)), ""
    except (OSError, ValueError) as e:
        print(f"[업데이트] ⚠️ {p} 읽기 실패: {e}")
        return [], f"업데이트 내역 파일을 못 읽었습니다 ({type(e).__name__}) — {p}"


def _clean(b: dict) -> tuple[dict | None, str]:
    d = str(b.get("date") or "").strip()
    v = str(b.get("version") or "").strip()
    t = str(b.get("content") or "").replace("\r\n", "\n").strip()
    try:
        datetime.strptime(d, "%Y-%m-%d")
    except ValueError:
        return None, "날짜를 넣으세요 (YYYY-MM-DD)"
    if not v:
        return None, "버전을 넣으세요"
    if len(v) > MAX_VER:
        return None, f"버전은 {MAX_VER}자까지입니다"
    if not t:
        return None, "내용을 넣으세요"
    if len(t) > MAX_TEXT:
        return None, f"내용은 {MAX_TEXT}자까지입니다"
    return {"date": d, "version": v, "content": t}, ""


def add(b: dict, cfg: dict | None = None) -> tuple[dict, int]:
    """하나 저장 — b = {date, version, content, pw}. (응답, HTTP 코드)."""
    if not pw_ok(b.get("pw")):
        return {"ok": False, "error": "비밀번호가 다릅니다"}, 403
    e, err = _clean(b)
    if err:
        return {"ok": False, "error": err}, 400
    e["id"] = uuid.uuid4().hex[:12]
    e["saved"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    p = path(cfg)
    with _LOCK:
        try:
            items = _read(p)
        except (OSError, ValueError) as x:
            return {"ok": False, "error": f"있던 내역을 못 읽어 저장하지 않았습니다 "
                                          f"({type(x).__name__}) — {p}"}, 500
        items.append(e)
        try:
            _write(p, items)
        except OSError as x:
            return {"ok": False, "error": f"저장 실패 — {x}"}, 500
    print(f"[업데이트] {e['date']} {e['version']} 저장")
    return {"ok": True, "item": e, "items": _order(items)}, 200


def delete(b: dict, cfg: dict | None = None) -> tuple[dict, int]:
    """하나 지움 — b = {delete: id, pw}. 잘못 적은 것을 고칠 길이 이것뿐이다
    (지우고 다시 적는다). 저장과 같은 비밀번호."""
    if not pw_ok(b.get("pw")):
        return {"ok": False, "error": "비밀번호가 다릅니다"}, 403
    rid = str(b.get("delete") or "")
    p = path(cfg)
    with _LOCK:
        try:
            items = _read(p)
        except (OSError, ValueError) as x:
            return {"ok": False, "error": f"있던 내역을 못 읽었습니다 ({type(x).__name__}) — {p}"}, 500
        left = [x for x in items if x.get("id") != rid]
        if len(left) == len(items):
            return {"ok": False, "error": "없는 항목입니다 (이미 지워졌을 수 있습니다)"}, 404
        try:
            _write(p, left)
        except OSError as x:
            return {"ok": False, "error": f"저장 실패 — {x}"}, 500
    print(f"[업데이트] {rid} 지움")
    return {"ok": True, "items": _order(left)}, 200
