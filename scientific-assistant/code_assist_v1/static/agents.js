/* code_assist_v1/static/agents.js — 개인 에이전트(프리셋) 관리 + 가동
 *
 * 에이전트 = 자주 쓰는 설정 묶음(이름·페르소나·스킬·지식검색·모델·effort)을
 * 사용자 아이디별로 저장. "가동" 시 전역 State 에 주입 → 기존 채팅 흐름이
 * 그대로 그 값으로 /api/code/chat/stream payload 를 구성한다.
 * (백엔드 채팅 엔드포인트는 변경 없음)
 */

// 현재 사용자 ID (knowledge.js _kbUid 패턴 동일)
function _agentUid() {
  try {
    const u = JSON.parse(sessionStorage.getItem("demos_user") || "null");
    return (u && u.id) ? u.id : null;
  } catch { return null; }
}

function _agentUidQs() {
  const uid = _agentUid();
  return uid ? ("?user_id=" + encodeURIComponent(uid)) : "";
}

const Agents = {
  // ── 목록 조회 ──
  async fetchList() {
    try {
      return await api("api/code/agent/list" + _agentUidQs());
    } catch {
      return { agents: [] };
    }
  },

  // ── 관리 모달 (목록 + 새로 만들기) ──
  async openManager() {
    if (!_agentUid()) {
      toast("로그인이 필요합니다", "error");
      return;
    }
    const body = document.createElement("div");
    body.innerHTML = '<div style="padding:14px;color:var(--muted);font-size:12px;">로드 중…</div>';

    Modal.open({
      title: "🤖 개인 에이전트",
      body,
      footButtons: [
        { label: "＋ 새 에이전트", primary: true, onClick: () => { Agents.openEditor(); return false; } },
        { label: "닫기" },
      ],
    });

    const data = await Agents.fetchList();
    body.innerHTML = "";

    const hint = document.createElement("p");
    hint.style.cssText = "color:var(--muted);font-size:11px;margin:0 0 10px;line-height:1.6;";
    hint.innerHTML = "저장된 설정 묶음(페르소나·스킬·지식검색·모델·effort)을 <b>가동</b>하면 채팅에 즉시 적용됩니다.";
    body.appendChild(hint);

    if (!data.agents?.length) {
      const el = document.createElement("div");
      el.style.cssText = "padding:14px;color:var(--muted);font-size:12px;";
      el.textContent = "저장된 에이전트가 없습니다. ＋ 새 에이전트로 만드세요.";
      body.appendChild(el);
      return;
    }

    data.agents.forEach(a => body.appendChild(Agents._row(a)));
  },

  // ── 목록 한 행 (sessions.js _row 스타일) ──
  _row(a) {
    const row = document.createElement("div");
    row.className = "item";
    row.style.cssText = "flex-direction:column;align-items:stretch;gap:4px;padding:10px 12px;";

    const skillCount = (a.skills || []).length;
    const persona = (a.persona || "").trim();
    const personaPreview = persona ? persona.slice(0, 80) + (persona.length > 80 ? "…" : "") : "(페르소나 없음)";

    row.innerHTML = `
      <div style="display:flex;align-items:center;gap:6px;">
        <span class="name" style="flex:1;font-size:13px;font-weight:600;">${_esc(a.name || "이름 없음")}</span>
        <button class="primary act-run" style="padding:3px 10px;font-size:11px;">가동</button>
        <button class="ghost act-edit" style="padding:3px 8px;font-size:11px;">편집</button>
        <button class="ghost danger act-del" style="padding:3px 8px;font-size:11px;">✕</button>
      </div>
      <div style="font-size:11px;color:var(--muted);line-height:1.5;">${_esc(personaPreview)}</div>
      <div style="font-size:10.5px;color:var(--muted);font-family:var(--mono);">
        스킬 ${skillCount} · KB ${a.enable_knowledge ? "ON" : "off"} · ${_esc(a.model || "모델유지")} · effort ${a.effort ?? 2}
      </div>
    `;

    row.querySelector(".act-run").addEventListener("click", e => {
      e.stopPropagation();
      Agents.activate(a);
    });
    row.querySelector(".act-edit").addEventListener("click", e => {
      e.stopPropagation();
      Agents.openEditor(a);
    });
    row.querySelector(".act-del").addEventListener("click", async e => {
      e.stopPropagation();
      if (!confirm(`에이전트 "${a.name}" 을(를) 삭제할까요?`)) return;
      try {
        const r = await fetch(`api/code/agent/delete/${encodeURIComponent(a.agent_id)}` + _agentUidQs(), { method: "DELETE" });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        toast("에이전트 삭제됨", "ok");
        Agents.openManager();
      } catch (err) {
        toast("삭제 실패: " + err.message, "error");
      }
    });

    return row;
  },

  // ── 생성/편집 모달 ──
  async openEditor(agent = null) {
    const isEdit = !!agent;
    const a = agent || { name: "", persona: "", skills: [], enable_knowledge: false, model: "", effort: 2 };

    // 스킬 목록 로드 (실패해도 폼은 표시)
    let skillItems = [];
    try {
      const sd = await Skills.fetchList();
      skillItems = sd.items || [];
    } catch { skillItems = []; }
    const activeSet = new Set(a.skills || []);

    // 모델 옵션은 상단바 #modelSelect 에서 복제 (+ "현재 유지" 옵션)
    const modelOptions = '<option value="">— 현재 모델 유지 —</option>' + ($("#modelSelect")?.innerHTML || "");

    const body = document.createElement("div");
    body.innerHTML = `
      <label>이름</label>
      <input id="agName" type="text" placeholder="예: 보안 코드 리뷰어" value="${_esc(a.name)}">

      <label>페르소나 (시스템 프롬프트로 전달)</label>
      <textarea id="agPersona" placeholder="예: 당신은 깐깐한 보안 코드 리뷰어입니다. 취약점을 우선순위로 지적하세요." style="min-height:120px;">${_esc(a.persona)}</textarea>

      <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;margin-top:4px;">
        <div style="flex:1;min-width:160px;">
          <label>모델</label>
          <select id="agModel" style="width:100%;">${modelOptions}</select>
        </div>
        <div style="min-width:120px;">
          <label>effort</label>
          <select id="agEffort" style="width:100%;">
            <option value="0">0 (정확)</option>
            <option value="1">1</option>
            <option value="2">2 (균형)</option>
            <option value="3">3 (창의)</option>
          </select>
        </div>
        <label style="display:flex;align-items:center;gap:6px;font-weight:400;cursor:pointer;padding-bottom:6px;">
          <input type="checkbox" id="agKB" style="margin:0;cursor:pointer;"> 📚 지식검색 ON
        </label>
      </div>

      <label style="margin-top:8px;">스킬 (${skillItems.length}개 중 선택)</label>
      <div id="agSkills" style="max-height:200px;overflow:auto;border:1px solid var(--border);border-radius:var(--radius);padding:8px;display:flex;flex-direction:column;gap:4px;"></div>
    `;

    // 스킬 체크박스 채우기 (SKILL_KO 한글 라벨 재사용 — skills.js 전역)
    const skillsBox = body.querySelector("#agSkills");
    if (!skillItems.length) {
      skillsBox.innerHTML = '<span style="color:var(--muted);font-size:12px;">스킬이 없습니다.</span>';
    } else {
      skillItems.forEach(s => {
        const ko = (typeof SKILL_KO !== "undefined" && SKILL_KO[s.id]) || "";
        const lbl = document.createElement("label");
        lbl.style.cssText = "display:flex;align-items:center;gap:8px;font-weight:400;font-size:12px;cursor:pointer;";
        lbl.innerHTML = `
          <input type="checkbox" value="${_esc(s.id)}" style="margin:0;cursor:pointer;" ${activeSet.has(s.id) ? "checked" : ""}>
          <span>${ko ? _esc(ko) + ' <span style="color:var(--muted);font-family:monospace;font-size:10px;">' + _esc(s.id) + "</span>" : _esc(s.id)}</span>
        `;
        skillsBox.appendChild(lbl);
      });
    }

    Modal.open({
      title: isEdit ? `에이전트 편집: ${a.name}` : "새 에이전트",
      body,
      footButtons: [
        { label: "취소", onClick: () => { Agents.openManager(); return false; } },
        { label: isEdit ? "저장" : "생성", primary: true, onClick: () => Agents._submit(isEdit ? a.agent_id : null) },
      ],
    });

    // 기존 값 반영 (select / checkbox)
    $("#agModel").value = a.model || "";
    $("#agEffort").value = String(a.effort ?? 2);
    $("#agKB").checked = !!a.enable_knowledge;
  },

  // ── 저장 ──
  async _submit(agentId) {
    const name = $("#agName").value.trim();
    if (!name) { toast("이름을 입력하세요", "error"); return false; }

    const skills = $$("#agSkills input[type=checkbox]")
      .filter(c => c.checked).map(c => c.value);

    const payload = {
      user_id: _agentUid(),
      agent_id: agentId || undefined,
      name,
      persona: $("#agPersona").value,
      skills,
      enable_knowledge: $("#agKB").checked,
      model: $("#agModel").value,
      effort: parseInt($("#agEffort").value, 10),
    };

    try {
      await api("api/code/agent/save", { method: "POST", body: payload });
      toast(agentId ? "에이전트 저장됨" : "에이전트 생성됨", "ok");
      Agents.openManager();
    } catch (e) {
      toast("저장 실패: " + e.message, "error");
    }
    return false;  // 모달 직접 제어
  },

  // ── 가동: 저장값을 State 에 주입 (핵심) ──
  activate(a) {
    // 페르소나 → 사용자 추가 시스템 프롬프트 (send() payload 의 system_prompt)
    State.systemPromptExtra = a.persona || "";
    localStorage.setItem("code_assist_v1.systemPromptExtra", State.systemPromptExtra);

    State.activeSkills = new Set(a.skills || []);
    State.enableKnowledge = !!a.enable_knowledge;

    if (a.model) {
      State.model = a.model;
      const sel = $("#modelSelect");
      if (sel) sel.value = a.model;
    }
    if (a.effort != null) {
      State.effort = a.effort;
      const es = $("#effortSelect");
      if (es) es.value = String(a.effort);
    }

    // UI 동기화
    const kb = $("#btnKB");
    if (kb) kb.classList.toggle("active", State.enableKnowledge);
    refreshMetaBar();
    Chat.refreshChips();
    if (typeof Skills !== "undefined" && currentTab === "skills") Skills.render($("#sidebarSearch")?.value || "");

    toast(`🤖 에이전트 가동: ${a.name}`, "ok");
    Modal.close();
  },
};

// HTML escape 헬퍼
function _esc(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// 상단바 버튼 바인딩 (app.js #systemPromptBtn 패턴 동일)
document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("agentBtn");
  if (btn) btn.addEventListener("click", () => Agents.openManager());
});
