/* code_assist_v1/static/workspace.js — 워크스페이스 (트리 + 폴더/파일 업로드) */

const Workspace = {
  files: [],          // [{path, size, mtime}]
  expanded: new Set(),// 펼쳐진 폴더 경로 집합

  async refresh() {
    try {
      const data = await api("/api/code/workspace/tree");
      Workspace.files = data.items || [];
      Workspace.render();
    } catch (e) {
      toast("워크스페이스 로드 실패: " + e.message, "error");
    }
  },

  // 평탄 [{path,size}] → 트리 노드 {name, path, kind:'dir'|'file', size, children?}
  _buildTree(files) {
    const root = { name: "", path: "", kind: "dir", children: new Map() };
    for (const f of files) {
      const parts = f.path.split("/").filter(Boolean);
      let cur = root;
      for (let i = 0; i < parts.length; i++) {
        const name = parts[i];
        const isLeaf = i === parts.length - 1;
        const childPath = parts.slice(0, i + 1).join("/");
        if (!cur.children.has(name)) {
          cur.children.set(name, isLeaf
            ? { name, path: childPath, kind: "file", size: f.size }
            : { name, path: childPath, kind: "dir", children: new Map() }
          );
        }
        cur = cur.children.get(name);
      }
    }
    // Map → 정렬된 배열, 폴더 먼저
    const finalize = node => {
      if (node.kind !== "dir") return node;
      const arr = [...node.children.values()].map(finalize);
      arr.sort((a, b) => {
        if (a.kind !== b.kind) return a.kind === "dir" ? -1 : 1;
        return a.name.localeCompare(b.name);
      });
      node.children = arr;
      return node;
    };
    return finalize(root);
  },

  _countFiles(dirNode) {
    let n = 0;
    for (const c of dirNode.children) {
      n += c.kind === "file" ? 1 : Workspace._countFiles(c);
    }
    return n;
  },

  render() {
    const tree = $("#wsTree");
    if (!Workspace.files.length) {
      tree.innerHTML = `<div style="color:var(--muted);padding:14px;font-size:12px;">파일이 없습니다. ＋파일 또는 ＋폴더로 업로드하세요.</div>`;
      return;
    }
    tree.innerHTML = "";
    const root = Workspace._buildTree(Workspace.files);
    Workspace._renderChildren(tree, root.children, 0);
  },

  _renderChildren(parentEl, children, depth) {
    for (const node of children) {
      if (node.kind === "dir") {
        const row = document.createElement("div");
        row.className = "ws-node ws-dir";
        row.dataset.depth = depth;
        const isOpen = Workspace.expanded.has(node.path);
        if (isOpen) row.classList.add("open");
        const count = Workspace._countFiles(node);
        row.innerHTML = `
          <span class="caret">▶</span>
          <span>📁</span>
          <span class="ws-name" style="flex:1;">${node.name}</span>
          <span class="count">${count}</span>
          <button class="ws-del" title="폴더 삭제">✕</button>
        `;
        parentEl.appendChild(row);

        const childWrap = document.createElement("div");
        childWrap.className = "ws-children" + (isOpen ? " open" : "");
        parentEl.appendChild(childWrap);
        if (isOpen) Workspace._renderChildren(childWrap, node.children, depth + 1);

        row.addEventListener("click", e => {
          if (e.target.classList.contains("ws-del")) return;
          if (Workspace.expanded.has(node.path)) {
            Workspace.expanded.delete(node.path);
            row.classList.remove("open");
            childWrap.classList.remove("open");
            childWrap.innerHTML = "";
          } else {
            Workspace.expanded.add(node.path);
            row.classList.add("open");
            childWrap.classList.add("open");
            Workspace._renderChildren(childWrap, node.children, depth + 1);
          }
        });
        // 폴더 우클릭 → 하위 모든 파일 첨부 토글
        row.addEventListener("contextmenu", e => {
          e.preventDefault();
          Workspace._toggleAttachDir(node);
        });
        // 폴더 삭제
        row.querySelector(".ws-del").addEventListener("click", e => {
          e.stopPropagation();
          Workspace.deletePath(node.path, /*isDir*/ true, count);
        });
      } else {
        const row = document.createElement("div");
        row.className = "ws-node ws-file";
        row.dataset.depth = depth;
        const sizeKb = (node.size / 1024).toFixed(1);
        const attached = State.workspaceFiles.find(x => x.filename === node.path);
        row.innerHTML = `
          <span>📄</span>
          <span class="ws-name" style="flex:1;${attached ? "color:var(--accent-2);font-weight:600;" : ""}">${node.name}</span>
          <span class="size">${sizeKb}K</span>
          <button class="ws-del" title="파일 삭제">✕</button>
        `;
        row.addEventListener("click", e => {
          if (e.target.classList.contains("ws-del")) return;
          Workspace.preview(node.path);
        });
        row.addEventListener("contextmenu", e => {
          e.preventDefault();
          Workspace.toggleAttach(node.path);
        });
        row.querySelector(".ws-del").addEventListener("click", e => {
          e.stopPropagation();
          Workspace.deletePath(node.path, /*isDir*/ false);
        });
        parentEl.appendChild(row);
      }
    }
  },

  async clearAll() {
    if (!Workspace.files.length) {
      toast("워크스페이스가 비어있습니다", "ok");
      return;
    }
    const total = Workspace.files.length;
    const phrase = "초기화";
    const input = prompt(
      `워크스페이스의 모든 파일·폴더 ${total}개를 삭제합니다.\n` +
      `이 동작은 되돌릴 수 없습니다.\n\n` +
      `진행하려면 "${phrase}" 를 입력하세요:`
    );
    if (input !== phrase) {
      toast("취소됨", "ok");
      return;
    }
    try {
      const r = await fetch("/api/code/workspace/clear", { method: "POST" });
      const j = await r.json();
      if (!r.ok && r.status !== 207) throw new Error(j.error || `HTTP ${r.status}`);
      // 첨부·미리보기 모두 비움
      State.workspaceFiles = [];
      const wp = $("#workspacePanel");
      if (wp.classList.contains("preview-on")) {
        $("#wsPreview").textContent = "";
        wp.classList.remove("preview-on");
        const ab = wp.querySelector(".attach-toggle");
        if (ab) ab.remove();
      }
      Workspace.expanded.clear();
      const errMsg = j.errors?.length ? ` (${j.errors.length}개 실패)` : "";
      toast(`초기화 완료: ${j.removed || 0}개 삭제${errMsg}`, j.errors?.length ? "warn" : "ok");
      Chat.refreshChips();
      refreshMetaBar();
      Workspace.refresh();
    } catch (e) {
      toast("초기화 실패: " + e.message, "error");
    }
  },

  async deletePath(path, isDir, fileCount = 0) {
    const label = isDir ? `폴더 "${path}" 와 하위 ${fileCount}개 파일` : `파일 "${path}"`;
    if (!confirm(`${label}을(를) 삭제할까요?\n이 동작은 되돌릴 수 없습니다.`)) return;
    try {
      const r = await fetch("/api/code/workspace/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
      // 첨부 목록에서 해당 경로(폴더면 prefix) 정리
      if (isDir) {
        const prefix = path.endsWith("/") ? path : path + "/";
        State.workspaceFiles = State.workspaceFiles.filter(
          x => x.filename !== path && !x.filename.startsWith(prefix)
        );
      } else {
        State.workspaceFiles = State.workspaceFiles.filter(x => x.filename !== path);
      }
      // 미리보기 닫기 (현재 본 파일이 지워졌을 때)
      const wp = $("#workspacePanel");
      if (wp.classList.contains("preview-on")) {
        $("#wsPreview").textContent = "";
        wp.classList.remove("preview-on");
        const ab = wp.querySelector(".attach-toggle");
        if (ab) ab.remove();
      }
      toast(`삭제됨: ${path}`, "ok");
      Chat.refreshChips();
      refreshMetaBar();
      Workspace.refresh();
    } catch (e) {
      toast("삭제 실패: " + e.message, "error");
    }
  },

  async _toggleAttachDir(dirNode) {
    // 하위 모든 파일 수집
    const collect = n => {
      if (n.kind === "file") return [n.path];
      return n.children.flatMap(collect);
    };
    const paths = collect(dirNode);
    if (!paths.length) return;
    const allAttached = paths.every(p => State.workspaceFiles.find(x => x.filename === p));
    if (allAttached) {
      State.workspaceFiles = State.workspaceFiles.filter(x => !paths.includes(x.filename));
      toast(`${paths.length}개 파일 첨부 해제`, "ok");
    } else {
      let added = 0;
      for (const p of paths) {
        if (State.workspaceFiles.find(x => x.filename === p)) continue;
        try {
          const data = await api("/api/code/workspace/file?path=" + encodeURIComponent(p));
          State.workspaceFiles.push({ filename: p, content: data.content });
          added++;
        } catch (e) { /* 5MB 초과/바이너리 등 스킵 */ }
      }
      toast(`${added}개 파일 첨부`, "ok");
    }
    Chat.refreshChips();
    refreshMetaBar();
    Workspace.render();
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

  // 파일 업로드 (개별/일부)
  async handleFiles(fileList, { attachAfter = true } = {}) {
    if (!fileList || !fileList.length) return;
    let ok = 0, skip = 0, fail = 0;
    const skipReasons = [];
    for (const file of fileList) {
      const fd = new FormData();
      fd.append("file", file);
      // webkitRelativePath 가 있으면 폴더 구조 보존
      if (file.webkitRelativePath) {
        fd.append("relpath", file.webkitRelativePath);
      }
      try {
        const r = await fetch("/api/code/workspace/upload", { method: "POST", body: fd });
        const j = await r.json();
        if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
        if (j.status === "skipped") {
          skip++;
          if (skipReasons.length < 3) skipReasons.push(`${file.webkitRelativePath || file.name}: ${j.reason}`);
          continue;
        }
        if (attachAfter && !file.webkitRelativePath) {
          // 단일 파일만 자동 첨부 (폴더 업로드는 너무 많아서 스킵)
          try {
            const data = await api("/api/code/workspace/file?path=" + encodeURIComponent(j.path));
            State.workspaceFiles.push({ filename: j.path, content: data.content });
          } catch {}
        }
        ok++;
      } catch (e) {
        fail++;
        console.warn("업로드 실패:", file.webkitRelativePath || file.name, e.message);
      }
    }
    const parts = [`${ok}개 업로드`];
    if (skip) parts.push(`${skip}개 스킵`);
    if (fail) parts.push(`${fail}개 실패`);
    const kind = fail ? (fail > ok ? "error" : "warn") : (skip ? "warn" : "ok");
    toast(parts.join(" · "), kind);
    if (skipReasons.length) {
      console.warn("스킵 사유 (최대 3개):\n" + skipReasons.join("\n"));
    }
    Chat.refreshChips();
    refreshMetaBar();
    Workspace.refresh();
  },

  // chat.js 의 첨부 버튼에서도 사용 (단일/소수 파일)
  async handleAttach(fileList) {
    return Workspace.handleFiles(fileList, { attachAfter: true });
  },
};

$("#btnWsRefresh").addEventListener("click", () => Workspace.refresh());
$("#btnWsUploadFile").addEventListener("click", () => $("#wsFileInput").click());
$("#btnWsUploadDir").addEventListener("click", () => $("#wsDirInput").click());
$("#btnWsClear").addEventListener("click", () => Workspace.clearAll());

$("#wsFileInput").addEventListener("change", e => {
  Workspace.handleFiles(e.target.files, { attachAfter: false });
  e.target.value = "";
});
$("#wsDirInput").addEventListener("change", e => {
  Workspace.handleFiles(e.target.files, { attachAfter: false });
  e.target.value = "";
});
