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
import json
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
        # ★"셋 중 하나다" 로 끝내면 안 된다 — 서버에 **직접 물어보면** 어느
        #   것인지 바로 안다. 도구 목록에 wikiWords 가 있나부터 본다.
        names, err = [], ""
        try:
            names = [t.get("name") for t in hub._client(wiki).tools()]
        except Exception as e:                          # noqa: BLE001
            err = "{}: {}".format(type(e).__name__, e)
        if err:
            print("  ★서버에 못 붙었다 — {}".format(err))
            print("     주소: {}".format(wiki.get("url")))
            print("     → mcp_server.py 를 띄웠나? 주소·포트가 맞나?")
        elif "wikiWords" not in names:
            print("  ★붙긴 했는데 **wikiWords 도구가 없다.** 서버가 옛날 것이다.")
            print("     지금 있는 도구: {}".format(" · ".join(n for n in names if n)))
            print("     → LLM_WIKI_MCP/amhs-llm-wiki/mcp_server.py 를 새 것으로")
            print("       덮고 **:8020 을 껐다 켜라**. 파일만 덮으면 파이썬이")
            print("       옛 코드를 계속 물고 있다.")
            print("     ※ wiki_mcp_stdio.py 만 덮은 것 아닌가? 지금 붙는 쪽은")
            print("       http({}) — mcp_server.py 다.".format(wiki.get("url")))
        else:
            words = hub._dyn_words(wiki)
            if not words:
                print("  ★도구는 있는데 낱말이 0개다 — 위키에 페이지가 없다.")
                print("     (wiki_진단.py ② 로 페이지가 있는지 봐라)")
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
    print("⑤ 웹 검색 (등록된 자료에 없을 때 나가는 길)")
    print("=" * 70)
    web = next((s for s in srv if s.get("fallback")), None)
    if not web:
        print("  등록돼 있지 않다 — 새 config.py 가 아니다.")
    else:
        print("  [{}] {}".format("켜짐" if web.get("enabled") else "★꺼짐",
                                 web.get("name") or web["key"]))
        a = web.get("args") or []
        raw = a[0] if a else ""
        path = raw if os.path.isabs(raw) else os.path.join(
            os.path.dirname(HERE), raw)
        exists = bool(raw) and os.path.isfile(path)
        print("  파일  : {}  {}".format(path or "(없음)",
                                        "있음" if exists else "★없음"))
        if not exists:
            print("     → WEB_MCP 폴더가 real_time_amhs **바로 밑**에 와야 한다.")
            print("       avatar_2d 안에 풀면 못 찾는다.")
        env = web.get("env") or {}
        url, kind = env.get("WEB_SEARCH_URL", ""), env.get("WEB_SEARCH_KIND", "")
        print("  검색  : {}  (방식 {})".format(url or "★안 정해짐", kind or "-"))
        if not web.get("enabled"):
            print("     → 화면(설정 → 외부 도구)에서 껐다. 켜야 나간다.")
        elif exists and url:
            try:
                with hub._srv_lock(web["key"]):
                    c = hub._client(web)
                    txt, bad_ = c.call("webSearch", {"query": "테스트", "topK": 3})
                if bad_:
                    print("  검색 시험: ★실패 — {}".format(str(txt)[:160]))
                    print("     → 그 주소가 이 PC 에서 열리나? 프록시를 타야 하나?")
                else:
                    print("  검색 시험: OK — {}건".format(
                        json.loads(txt).get("count", "?")))
            except Exception as e:                      # noqa: BLE001
                print("  검색 시험: ★못 붙었다 — {}: {}".format(type(e).__name__, e))

        print("")
        print("  질문이 웹으로 나가나")
        for q, _w in qs:
            ok_ = hub._web_ok(q)
            hit = [x for x in hub.matched(q)
                   if not x.get("fallback") and not x.get("knowledge")]
            if not ok_:
                why = "안 나감 (관제·잡담)"
            elif hit:
                why = "안 나감 ({} 가 받는다)".format(hit[0].get("name"))
            else:
                why = "나간다 — 등록 자료에 없으면"
            print("    {:<26} {}".format(q[:26], why))

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
