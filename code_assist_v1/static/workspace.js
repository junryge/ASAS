/* code_assist_v1/static/workspace.js — 워크스페이스 (단일 폴더, user_id 없음) */

const Workspace = {
  files: [],

  async refresh() {
    try {
      const data = await api("/api/code/workspace/tree");
      Workspace.files = data.items || [];
      Workspace.render();
    } catch (e) {
      toast("워크스페이스 로드 실패: " + e.message, "error");
    }
  },

  render() {
    const tree = $("#wsTree");
    if (!Workspace.files.length) {
      tree.innerHTML = `<div style="color:var(--muted);padding:14px;font-size:12px;">파일이 없습니다. ＋ 로 업로드하세요.</div>`;
      return;
    }
    tree.innerHTML = "";
    Workspace.files.forEach(f => {
      const row = document.createElement("div");
      row.className = "ws-file";
      const sizeKb = (f.size / 1024).toFixed(1);
      const attached = State.workspaceFiles.find(x => x.filename === f.path);
      row.innerHTML = `
        <span>📄</span>
        <span style="flex:1;${attached ? "color:var(--accent-2);font-weight:600;" : ""}">${f.path}</span>
        <span class="size">${sizeKb}K</span>
      `;
      row.addEventListener("click", () => Workspace.preview(f.path));
      row.addEventListener("contextmenu", e => {
        e.preventDefault();
        Workspace.toggleAttach(f.path);
      });
      tree.appendChild(row);
    });
  },

  async preview(path) {
    try {
      const data = await api("/api/code/workspace/file?path=" + encodeURIComponent(path));
      const wp = $("#workspacePanel");
      wp.classList.add("preview-on");
      const pre = $("#wsPreview");
      pre.textContent = data.content || "(빈 파일)";

      const head = wp.querySelector(".ws-head");
      let attachBtn = head.querySelector(".attach-toggle");
      if (!attachBtn) {
        attachBtn = document.createElement("button");
        attachBtn.className = "ghost attach-toggle";
        attachBtn.title = "현재 파일을 채팅에 첨부";
        head.insertBefore(attachBtn, head.querySelector("#btnWsRefresh"));
      }
      const attached = State.workspaceFiles.find(x => x.filename === path);
      attachBtn.textContent = attached ? "✓첨부됨" : "📎첨부";
      attachBtn.onclick = () => {
        Workspace.setAttach(path, data.content);
        attachBtn.textContent = State.workspaceFiles.find(x => x.filename === path) ? "✓첨부됨" : "📎첨부";
      };
    } catch (e) {
      toast(e.message, "error");
    }
  },

  toggleAttach(path) {
    const existing = State.workspaceFiles.find(x => x.filename === path);
    if (existing) {
      State.workspaceFiles = State.workspaceFiles.filter(x => x !== existing);
    } else {
      api("/api/code/workspace/file?path=" + encodeURIComponent(path))
        .then(data => Workspace.setAttach(path, data.content))
        .catch(e => toast(e.message, "error"));
      return;
    }
    Chat.refreshChips();
    refreshMetaBar();
    Workspace.render();
  },

  setAttach(path, content) {
    const existing = State.workspaceFiles.find(x => x.filename === path);
    if (existing) {
      State.workspaceFiles = State.workspaceFiles.filter(x => x !== existing);
    } else {
      State.workspaceFiles.push({ filename: path, content });
    }
    Chat.refreshChips();
    refreshMetaBar();
    Workspace.render();
  },

  async handleAttach(fileList) {
    if (!fileList || !fileList.length) return;
    for (const file of fileList) {
      const fd = new FormData();
      fd.append("file", file);
      try {
        const r = await fetch("/api/code/workspace/upload", { method: "POST", body: fd });
        const j = await r.json();
        if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
        const data = await api("/api/code/workspace/file?path=" + encodeURIComponent(j.path));
        State.workspaceFiles.push({ filename: j.path, content: data.content });
        toast(`첨부: ${j.path}`, "ok");
      } catch (e) {
        toast("업로드 실패: " + e.message, "error");
      }
    }
    Chat.refreshChips();
    refreshMetaBar();
    Workspace.refresh();
  },
};

$("#btnWsRefresh").addEventListener("click", () => Workspace.refresh());
$("#btnWsUpload").addEventListener("click", () => $("#hiddenFileInput").click());
