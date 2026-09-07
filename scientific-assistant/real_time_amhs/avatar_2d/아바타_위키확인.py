# -*- coding: utf-8 -*-
"""아바타가 이 질문에 위키를 뒤지나 — 실제로 돌려 보고 찍는다.

    python 아바타_위키확인.py
    python 아바타_위키확인.py "리센느 누구야?" "AMOS 이상 감지는?"

★왜 필요한가
  위키·MCP 는 wiki_진단.py 로 확인이 된다. 그런데 거기까지 멀쩡한데도
  아바타가 "확인이 안 되요" 라고 하는 일이 있다. 아바타 쪽에서 갈릴 수
  있는 곳이 셋인데 눈으로 안 갈렸다:

      ① 서버가 켜져 있나 (enabled) · 붙나
      ② 그 질문에 **낱말이 걸리나** (when · when_dyn)
      ③ 걸려서 부른 결과에 답이 들어 있나

  ②가 제일 많이 걸린다 — 위키에 문서가 있어도 아바타가 아예 안 물어본다.

표준 라이브러리만 쓴다 (폐쇄망).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# (질문, 걸려야 하나) — 관제 질문은 **안 걸리는 게 맞다**. 그것까지 걸리면
# 상태를 물을 때마다 위키를 뒤진다.
QS = [("리센느 누구야?", True), ("리센느 팬덤 이름은?", True),
      ("AMOS 이상 감지는 뭐지?", True), ("VHL이 뭐야?", True),
      ("지금 M16HUB 점수 어때?", False)]


def main(argv):
    qs = [(q, True) for q in argv[1:]] or QS
    from avatar import config as C
    from avatar import mcp_client

    srv = [dict(s) for s in C.MCP_SERVERS]
    for s in srv:
        if s.get("cwd") is None:
            s["cwd"] = os.path.dirname(HERE)      # real_time_amhs
    hub = mcp_client.Hub(srv)

    print("=" * 70)
    print("① 등록된 MCP 서버")
    print("=" * 70)
    for s in srv:
        addr = s.get("url") or "(직접 띄움: {})".format(" ".join(s.get("args") or []))
        print("  [{}] {}  {}".format("켜짐" if s.get("enabled") else "꺼짐",
                                     s.get("name") or s["key"], addr))
        print("       when {}개 · when_dyn {}".format(
            len(s.get("when") or []), s.get("when_dyn") or "(없음)"))
        if not s.get("when_dyn") and s["key"] == "wiki":
            print("       ★when_dyn 이 없다 — 새 config.py 가 아니다."
                  " 문서를 넣어도 낱말이 안 는다.")

    print("")
    print("=" * 70)
    print("② 위키가 알려주는 낱말 (when_dyn)")
    print("=" * 70)
    wiki = next((s for s in srv if s["key"] == "wiki"), None)
    if not wiki:
        print("  위키 서버가 등록돼 있지 않다.")
    elif not wiki.get("when_dyn"):
        print("  when_dyn 이 없다 — 건너뛴다.")
    else:
        words = hub._dyn_words(wiki)
        if not words:
            print("  ★한 개도 못 받았다. 아래 중 하나다:")
            print("    · MCP 서버(:8020)가 안 떠 있다")
            print("    · MCP 서버가 **옛날 것**이라 wikiWords 도구가 없다"
                  " (mcp_server.py 를 새 것으로 덮고 재시작)")
            print("    · 위키에 페이지가 없다")
        else:
            print("  {}개 받음. 앞 20개:".format(len(words)))
            print("    " + " · ".join(words[:20]))

    print("")
    print("=" * 70)
    print("③ 질문마다 — 어느 서버가 걸리나")
    print("=" * 70)
    bad = 0
    for q, want in qs:
        names = [s.get("name") or s["key"] for s in hub.matched(q)]
        if names:
            mark = "" if want else "   ★관제 질문인데 걸렸다 (상태 물을 때마다 위키를 뒤진다)"
        else:
            mark = "" if not want else ""
        print("  {:<28} → {}{}".format(
            q[:28], " · ".join(names) or ("★아무것도 안 걸림" if want
                                          else "(안 걸림 — 맞다)"), mark))
        if want and not names:
            bad += 1

    print("")
    print("=" * 70)
    print("④ 실제로 불러서 받은 글 (첫 질문)")
    print("=" * 70)
    got, used = hub.gather(qs[0][0], use_cache=False)
    print("  도구 {}번 호출 · 글 {}자".format(used, len(got or "")))
    if got:
        for ln in str(got).splitlines()[:12]:
            print("    " + ln[:100])
    else:
        print("    (빈 글 — 아바타는 근거 없이 답하게 된다)")

    print("")
    print("=" * 70)
    if bad:
        print("★{}개 질문이 아무 서버에도 안 걸렸다.".format(bad))
        print("  · ②에서 낱말을 못 받았으면 → MCP 서버(:8020) 재시작부터")
        print("  · ②는 받았는데 ③이 안 걸리면 → 그 낱말이 질문에 없는 것이다")
        print("    (위키 페이지 제목·태그에 그 말을 넣어라)")
    else:
        print("전부 걸린다. 여기까지 정상이면 남은 것은 LLM 쪽이다 —")
        print("④ 의 글에 답이 있는데도 엉뚱하게 말하면 모델·페르소나 문제다.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
