/* code_assist_v1/static/knowledge.js — 도메인 지식 (user_id 기반, demos_v1 공유) */

// demos_v1 로그인 시 localStorage('demos_user') = {id, name, role, token} 저장됨
// → 같은 origin이라 code_assist_v1도 그대로 읽어 user_id 추출
function _kbUid() {
  try {
    const u = JSON.parse(sessionStorage.getItem('demos_user') || 'null');
    return (u && u.id) ? u.id : null;
  } catch { return null; }
}

function _kbUidQs() {
  const uid = _kbUid();
  return uid ? ('?user_id=' + encodeURIComponent(uid)) : '';
}

const Knowledge = {
  async fetchList() {
    return await api("api/code/knowledge/list" + _kbUidQs());
  },

  async render(query = "") {
    if (currentTab !== "knowledge") return;
    const body = $("#sidebarBody");
    body.innerHTML = '<div style="padding:14px;color:var(--muted);font-size:12px;">로드 중…</div>';
    try {
      const data = await Knowledge.fetchList();
      let items = data.items || [];
      if (query) {
        const ql = query.toLowerCase();
        items = items.filter(it => it.filename.toLowerCase().includes(ql));
      }
      body.innerHTML = "";
      const header = document.createElement("div");
      header.className = "section-title";
      header.innerHTML = `
        지식 ${items.length}개
        <span style="float:right;font-size:11px;text-transform:none;letter-spacing:0;">
          <button class="ghost" id="kbUploadBtn" style="font-size:11px;padding:2px 6px;">업로드</button>
        </span>
      `;
      body.appendChild(header);

      items.forEach(it => body.appendChild(Knowledge._row(it)));

      if (!items.length) {
        const el = document.createElement("div");
        el.style.cssText = "padding:14px;color:var(--muted);font-size:12px;";
        el.textContent = "문서가 없습니다. ＋ 또는 업로드 버튼으로 추가하세요.";
        body.appendChild(el);
      }

      $("#kbUploadBtn")?.addEventListener("click", () => Knowledge.openUpload());
    } catch (e) {
      body.innerHTML = `<div style="padding:14px;color:var(--error);font-size:12px;">${e.message}</div>`;
    }
  },

  _row(it) {
    const row = document.createElement("div");
    row.className = "item";
    const sizeKb = (it.size / 1024).toFixed(1);
    row.innerHTML = `
      <span class="name">${it.filename}</span>
      <span class="badge">${sizeKb}K</span>
    `;
    row.addEventListener("click", () => Knowledge.openView(it.filename));
    return row;
  },

  async openView(filename) {
    try {
      const data = await api(`api/code/knowledge/view/${encodeURIComponent(filename)}${_kbUidQs()}`);

      const body = document.createElement("div");
      body.innerHTML = `<div style="font-size:12px;color:var(--muted);margin-bottom:6px;">${filename}</div>`;
      const ta = document.createElement("textarea");
      ta.value = data.content || "";
      body.appendChild(ta);

      Modal.open({
        title: filename,
        body,
        footButtons: [
          { label: "삭제", danger: true, onClick: async () => {
            if (!confirm(`${filename} 삭제할까요?`)) return false;
            await api("api/code/knowledge/delete", { method: "POST", body: { filename, user_id: _kbUid() } });
            toast("삭제됨", "ok");
            Knowledge.render();
          }},
          { label: "저장", primary: true, onClick: async () => {
            await api("api/code/knowledge/create", {
              method: "POST",
              body: { filename, content: ta.value, user_id: _kbUid() },
            });
            toast("저장됨", "ok");
            Knowledge.render();
          }},
          { label: "닫기" },
        ],
      });
    } catch (e) {
      toast(e.message, "error");
    }
  },

  openCreate() {
    const body = document.createElement("div");
    body.innerHTML = `
      <label>파일명 (.md 자동 추가)</label>
      <input id="newKbName" type="text" placeholder="my_domain.md">
      <label>내용 (마크다운, frontmatter 권장)</label>
      <textarea id="newKbContent" placeholder='---
title: My Domain Knowledge
tags: [coding, python]
date: 2026-05-06
---

# 본문

여기에 도메인 지식을 작성하세요.
'></textarea>
    `;
    Modal.open({
      title: "새 도메인 지식",
      body,
      footButtons: [
        { label: "취소" },
        { label: "저장", primary: true, onClick: async () => {
          const filename = $("#newKbName").value.trim();
          const content = $("#newKbContent").value;
          if (!filename) { toast("파일명 필수", "error"); return false; }
          try {
            await api("api/code/knowledge/create", {
              method: "POST",
              body: { filename, content, user_id: _kbUid() },
            });
            toast("생성됨", "ok");
            Knowledge.render();
          } catch (e) { toast(e.message, "error"); return false; }
        }},
      ],
    });
  },

  openUpload() {
    const body = document.createElement("div");
    body.innerHTML = `
      <label>파일 선택 (.md, .txt, .pdf, .docx)</label>
      <input id="kbUploadFile" type="file" accept=".md,.txt,.pdf,.docx,.json,.yaml,.yml">
      <p style="color:var(--muted);font-size:12px;margin-top:8px;">
        업로드 시 텍스트 추출 후 knowledge/ 에 .md 로 저장됩니다.
      </p>
    `;
    Modal.open({
      title: "도메인 지식 업로드",
      body,
      footButtons: [
        { label: "취소" },
        { label: "업로드", primary: true, onClick: async () => {
          const file = $("#kbUploadFile").files?.[0];
          if (!file) { toast("파일 선택 필요", "error"); return false; }
          const fd = new FormData();
          fd.append("file", file);
          const _uid = _kbUid();
          if (_uid) fd.append("user_id", _uid);
          try {
            const r = await fetch("api/code/knowledge/upload", { method: "POST", body: fd });
            const j = await r.json();
            if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
            toast(`업로드됨: ${j.filename} (${j.extracted_chars}자)`, "ok");
            Knowledge.render();
          } catch (e) { toast(e.message, "error"); return false; }
        }},
      ],
    });
  },
};
