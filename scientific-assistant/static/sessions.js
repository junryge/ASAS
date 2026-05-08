/* code_assist_v1/static/sessions.js — 세션 패널 (삭제 + 날짜/시간 표시) */

const Sessions = {
  async fetchList() {
    try {
      return await api("api/code/session/list");
    } catch {
      return { sessions: [] };
    }
  },

  async render() {
    if (currentTab !== "sessions") return;
    const body = $("#sidebarBody");
    body.innerHTML = '<div style="padding:14px;color:var(--muted);font-size:12px;">로드 중…</div>';
    const data = await Sessions.fetchList();
    body.innerHTML = "";
    const header = document.createElement("div");
    header.className = "section-title";
    header.textContent = `세션 ${data.sessions?.length || 0}개`;
    body.appendChild(header);

    if (!data.sessions?.length) {
      const el = document.createElement("div");
      el.style.cssText = "padding:14px;color:var(--muted);font-size:12px;";
      el.textContent = "저장된 세션이 없습니다. 채팅 후 자동 저장됩니다.";
      body.appendChild(el);
      return;
    }

    data.sessions.forEach(s => body.appendChild(Sessions._row(s)));
  },

  _row(s) {
    const row = document.createElement("div");
    row.className = "item";
    row.style.flexDirection = "column";
    row.style.alignItems = "stretch";
    row.style.gap = "2px";

    const ts = s.timestamp ? new Date(s.timestamp * 1000) : null;
    const dateStr = ts ? Sessions._fmt(ts) : "—";
    const title = (s.first_message || s.session_id || "").slice(0, 60);
    const isCurrent = State.session_id === s.session_id;

    row.innerHTML = `
      <div style="display:flex;align-items:center;gap:6px;">
        <span class="name" style="flex:1;font-size:13px;${isCurrent ? "color:var(--accent);font-weight:600;" : ""}"
              title="${(title || "(빈 세션)").replace(/"/g, "&quot;")}">${title || "(빈 세션)"}</span>
        <span class="badge">${s.message_count || 0}턴</span>
        <button class="ghost session-del" title="삭제" style="padding:2px 6px;font-size:11px;">✕</button>
      </div>
      <div style="font-size:10.5px;color:var(--muted);font-family:var(--mono);">
        ${dateStr}  ·  <span style="opacity:.7;">${(s.session_id || "").slice(0,8)}</span>
      </div>
    `;

    // 본문 클릭 → 세션 로드
    row.addEventListener("click", e => {
      if (e.target.classList.contains("session-del")) return;
      Sessions.load(s.session_id);
    });

    // 삭제 버튼
    row.querySelector(".session-del").addEventListener("click", async e => {
      e.stopPropagation();
      if (!confirm(`이 세션을 삭제할까요?\n  ${title || s.session_id}`)) return;
      try {
        const r = await fetch(`api/code/session/delete/${encodeURIComponent(s.session_id)}`, {
          method: "DELETE",
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        if (State.session_id === s.session_id) {
          State.session_id = null;
          State.messages = [];
          Chat.clear();
        }
        toast("세션 삭제됨", "ok");
        Sessions.render();
      } catch (e) {
        toast("삭제 실패: " + e.message, "error");
      }
    });

    return row;
  },

  async load(sid) {
    try {
      const data = await api(`api/code/session/load/${encodeURIComponent(sid)}`);
      State.messages = data.messages || [];
      State.session_id = sid;
      Chat.clear();
      State.messages.forEach(m => Chat.appendMessage(m.role, m.content));
      toast(`세션 로드: ${sid.slice(0,8)}`, "ok");
      Sessions.render();
    } catch (e) {
      toast(e.message, "error");
    }
  },

  _fmt(d) {
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    const hh = String(d.getHours()).padStart(2, "0");
    const mi = String(d.getMinutes()).padStart(2, "0");
    return `${yyyy}-${mm}-${dd} ${hh}:${mi}`;
  },
};
