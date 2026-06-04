/* hermes-client.js — 프론트 드롭인 헬퍼
 *
 * 사용법 (기존 채팅 send 흐름을 감싼다):
 *   1) 전송 전:  const addon = await Hermes.prep(userId, query);
 *               → 이 addon 을 system_prompt 에 합쳐서 기존 /api/chat 로 전송
 *   2) 응답 후:  const r = await Hermes.post(userId, answer, query, sessionId);
 *               → r.clean(블록 제거 본문), r.questions(되묻기), r.pending_skills(승인 대기)
 *   3) 스킬 승인: await Hermes.confirmSkill(userId, spec);
 */
(function (global) {
  async function _json(url, opts) {
    const r = await fetch(url, opts);
    return r.json();
  }
  const Hermes = {
    base: "",   // 다른 호스트면 'http://host:port' 로 설정

    async prep(userId, query) {
      if (!userId) return "";
      try {
        const d = await _json(this.base + "/api/hermes/prep", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: userId, query: query || "" }),
        });
        return d.system_addon || "";
      } catch (e) { return ""; }
    },

    async post(userId, answer, userMessage, sessionId) {
      try {
        return await _json(this.base + "/api/hermes/post", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: userId, answer: answer || "",
            user_message: userMessage || "", session_id: sessionId || "",
          }),
        });
      } catch (e) { return { clean: answer, pending_skills: [], questions: [] }; }
    },

    async confirmSkill(userId, spec) {
      return _json(this.base + "/api/hermes/skill/confirm", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, spec }),
      });
    },

    listSkills(userId) {
      return _json(this.base + "/api/hermes/skills?user_id=" + encodeURIComponent(userId));
    },
    getMemory(userId) {
      return _json(this.base + "/api/hermes/memory?user_id=" + encodeURIComponent(userId));
    },
    memoryOp(userId, store, action, opts) {
      return _json(this.base + "/api/hermes/memory/op", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(Object.assign({ user_id: userId, store, action }, opts || {})),
      });
    },
    searchSessions(userId, q) {
      return _json(this.base + "/api/hermes/sessions/search?user_id=" +
        encodeURIComponent(userId) + "&q=" + encodeURIComponent(q || ""));
    },
  };
  global.Hermes = Hermes;
})(window);
