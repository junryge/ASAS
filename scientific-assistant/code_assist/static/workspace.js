/* code_assist_v1/static/workspace.js — 워크스페이스 (트리 + 폴더/파일 업로드) */

const Workspace = {
  files: [],          // [{path, size, mtime}]
  expanded: new Set(),// 펼쳐진 폴더 경로 집합

  async refresh() {
    try {
      const data = await api("/api/code/workspace/tree");
      Workspace.files = data.items || [];
      console.log(`[ws] tree: ${Workspace.files.length}개 파일`, Workspace.files.map(f => f.path));
      Workspace.render();
    } catch (e) {
      toast("워크스페이스 로드 실패: " + e.message, "error");
    }
  },

  // 모든 폴더 펼침/접기
  expandAll() {
    const collect = node => {
      if (node.kind === "dir") {
        Workspace.expanded.add(node.path);
        node.children.forEach(collect);
      }
    };
    const root = Workspace._buildTree(Workspace.files);
    root.children.forEach(collect);
    Workspace.render();
  },
  collapseAll() {
    Workspace.expanded.clear();
    Workspace.render();
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
      tree.innerHTML = `<div style="color:var(--muted);padding:14px;font-size:12px;line-height:1.6;">
        파일이 없습니다.<br>
        • <b>＋파일</b> / <b>＋폴더</b> 버튼<br>
        • 또는 이 영역에 <b>폴더를 드래그</b>해서 떨어뜨리세요
      </div>`;
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

  openFolderDropModal() {
    const body = document.createElement("div");
    body.innerHTML = `
      <div id="wsBigDrop" style="
        border: 2px dashed var(--accent);
        border-radius: 12px;
        padding: 60px 40px;
        text-align: center;
        background: rgba(80,160,255,0.05);
        transition: all .15s;
        cursor: pointer;
      ">
        <div style="font-size: 56px; margin-bottom: 12px;">📁</div>
        <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">폴더를 여기에 드래그해서 떨어뜨리세요</div>
        <div style="color: var(--muted); font-size: 12px; line-height: 1.7;">
          윈도우 탐색기에서 폴더를 잡아서 이 영역에 끌어다 놓으세요.<br>
          하위 폴더와 <b>모든 파일</b>이 그대로 업로드됩니다.
        </div>
      </div>
      <details style="margin-top:14px;color:var(--muted);font-size:11px;">
        <summary style="cursor:pointer;">⓵ 다이얼로그로 선택 (덜 추천)</summary>
        <div style="margin-top:8px;line-height:1.6;">
          버튼 누르면 윈도우 폴더 다이얼로그가 열립니다.<br>
          ⚠️ 폴더를 <b>더블클릭으로 들어가지 마세요</b> — 한 번만 클릭한 후 하단 "업로드" 버튼.<br>
          <button id="wsDirFallback" class="ghost" style="margin-top:6px;">＋ 다이얼로그 열기</button>
        </div>
      </details>
    `;
    Modal.open({
      title: "📁 폴더 업로드",
      body,
      footButtons: [{ label: "닫기" }],
    });

    const dropEl = $("#wsBigDrop");
    const setActive = on => {
      dropEl.style.background = on ? "rgba(80,160,255,0.18)" : "rgba(80,160,255,0.05)";
      dropEl.style.borderColor = on ? "var(--accent-2, var(--accent))" : "var(--accent)";
    };
    ["dragenter", "dragover"].forEach(ev =>
      dropEl.addEventListener(ev, e => { e.preventDefault(); e.stopPropagation(); setActive(true); })
    );
    ["dragleave"].forEach(ev =>
      dropEl.addEventListener(ev, e => { e.preventDefault(); e.stopPropagation(); setActive(false); })
    );
    dropEl.addEventListener("drop", async e => {
      e.preventDefault();
      e.stopPropagation();
      setActive(false);
      const items = e.dataTransfer?.items;
      if (!items || !items.length) return;
      const entries = [];
      for (const it of items) {
        const entry = it.webkitGetAsEntry?.();
        if (entry) entries.push(entry);
      }
      if (!entries.length) {
        if (e.dataTransfer.files?.length) {
          Modal.close();
          Workspace.handleFiles(e.dataTransfer.files, { attachAfter: false });
        }
        return;
      }
      Modal.close();
      toast("드래그 인식 중…", "ok");
      const files = await _entriesToFiles(entries);
      console.log(`[ws] 모달 드롭: ${files.length}개 파일 수집`);
      Workspace.handleFiles(files, { attachAfter: false });
    });

    // 폴백 다이얼로그 버튼
    const fb = $("#wsDirFallback");
    if (fb) fb.addEventListener("click", () => {
      Modal.close();
      $("#wsDirInput").click();
    });
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
    const uploadedDirs = new Set();   // 업로드된 폴더의 모든 prefix (자동 펼침용)
    for (const file of fileList) {
      const fd = new FormData();
      fd.append("file", file);
      // webkitRelativePath (폴더 input) 또는 _relPath (드래그앤드롭) 가 있으면 폴더 구조 보존
      const relPath = file.webkitRelativePath || file._relPath || "";
      if (relPath) {
        fd.append("relpath", relPath);
      }
      try {
        const r = await fetch("/api/code/workspace/upload", { method: "POST", body: fd });
        const j = await r.json();
        if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
        if (j.status === "skipped") {
          skip++;
          if (skipReasons.length < 5) skipReasons.push(`${file.webkitRelativePath || file.name}: ${j.reason}`);
          continue;
        }
        // 업로드된 path 의 모든 상위 폴더를 펼침 대상에 추가
        if (j.path) {
          const parts = j.path.split("/");
          for (let i = 1; i < parts.length; i++) {
            uploadedDirs.add(parts.slice(0, i).join("/"));
          }
        }
        if (attachAfter && !relPath) {
          // 단일 파일만 자동 첨부 (폴더 업로드는 너무 많아서 스킵)
          try {
            const data = await api("/api/code/workspace/file?path=" + encodeURIComponent(j.path));
            State.workspaceFiles.push({ filename: j.path, content: data.content });
          } catch {}
        }
        ok++;
      } catch (e) {
        fail++;
        console.warn("[ws] 업로드 실패:", file.webkitRelativePath || file.name, e.message);
      }
    }
    const parts = [`${ok}개 업로드`];
    if (skip) parts.push(`${skip}개 스킵`);
    if (fail) parts.push(`${fail}개 실패`);
    const kind = fail ? (fail > ok ? "error" : "warn") : (skip ? "warn" : "ok");
    toast(parts.join(" · "), kind);
    if (skipReasons.length) {
      console.warn("[ws] 스킵 사유 (최대 5개):\n" + skipReasons.join("\n"));
    }
    // 폴더 업로드 시 그 폴더들을 자동 펼침 (사용자가 안에 든 파일을 바로 볼 수 있게)
    uploadedDirs.forEach(d => Workspace.expanded.add(d));
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
$("#btnWsExpandAll").addEventListener("click", () => Workspace.expandAll());
$("#btnWsCollapseAll").addEventListener("click", () => Workspace.collapseAll());
$("#btnWsUploadFile").addEventListener("click", () => $("#wsFileInput").click());
$("#btnWsUploadDir").addEventListener("click", () => Workspace.openFolderDropModal());
$("#btnWsClear").addEventListener("click", () => Workspace.clearAll());

// ── 드래그앤드롭으로 폴더/파일 업로드 (웹킷 다이얼로그가 폴더를 1개만 인식하는 윈도우 케이스 대비) ──
async function _entriesToFiles(entries, prefix = "") {
  const out = [];
  for (const entry of entries) {
    if (entry.isFile) {
      await new Promise(resolve => {
        entry.file(
          file => { file._relPath = prefix + entry.name; out.push(file); resolve(); },
          () => resolve()
        );
      });
    } else if (entry.isDirectory) {
      const reader = entry.createReader();
      const subEntries = await new Promise(resolve => {
        const all = [];
        const readBatch = () => reader.readEntries(
          batch => { if (!batch.length) resolve(all); else { all.push(...batch); readBatch(); } },
          () => resolve(all)
        );
        readBatch();
      });
      const subFiles = await _entriesToFiles(subEntries, prefix + entry.name + "/");
      out.push(...subFiles);
    }
  }
  return out;
}

const _wsDropZone = $("#wsTree");
const _wsPanel = $("#workspacePanel");
["dragenter", "dragover"].forEach(ev => {
  _wsDropZone.addEventListener(ev, e => {
    e.preventDefault();
    e.stopPropagation();
    _wsPanel.classList.add("drag-over");
  });
});
["dragleave", "drop"].forEach(ev => {
  _wsDropZone.addEventListener(ev, e => {
    e.preventDefault();
    e.stopPropagation();
    _wsPanel.classList.remove("drag-over");
  });
});
_wsDropZone.addEventListener("drop", async e => {
  const items = e.dataTransfer?.items;
  if (!items || !items.length) return;
  const entries = [];
  for (const it of items) {
    const entry = it.webkitGetAsEntry?.();
    if (entry) entries.push(entry);
  }
  if (!entries.length) {
    // fallback: 일반 file list
    if (e.dataTransfer.files?.length) {
      Workspace.handleFiles(e.dataTransfer.files, { attachAfter: false });
    }
    return;
  }
  toast("드래그 인식 중…", "ok");
  const files = await _entriesToFiles(entries);
  console.log(`[ws] 드래그앤드롭: ${files.length}개 파일 수집`);
  for (let i = 0; i < Math.min(10, files.length); i++) {
    console.log(`   [${i}] ${files[i]._relPath} (${files[i].size}B)`);
  }
  if (files.length > 10) console.log(`   ... 외 ${files.length - 10}개 더`);
  Workspace.handleFiles(files, { attachAfter: false });
});

$("#wsFileInput").addEventListener("change", e => {
  console.log(`[ws] ＋파일 input: ${e.target.files.length}개 선택됨`);
  for (let i = 0; i < Math.min(10, e.target.files.length); i++) {
    const f = e.target.files[i];
    console.log(`   [${i}] ${f.name} (${f.size}B) relPath="${f.webkitRelativePath || ""}"`);
  }
  Workspace.handleFiles(e.target.files, { attachAfter: false });
  e.target.value = "";
});
$("#wsDirInput").addEventListener("change", e => {
  console.log(`[ws] ＋폴더 input: ${e.target.files.length}개 파일 선택됨`);
  if (e.target.files.length === 0) {
    toast("폴더 안에 파일이 없거나 접근 거부됨", "warn");
    return;
  }
  if (e.target.files.length === 1) {
    toast("⚠ 1개만 인식됐어요. 다이얼로그에서 폴더를 더블클릭으로 들어가지 말고 한 번만 클릭한 뒤 '업로드' 누르세요. 또는 폴더를 트리에 드래그하세요!", "warn");
  }
  for (let i = 0; i < Math.min(10, e.target.files.length); i++) {
    const f = e.target.files[i];
    console.log(`   [${i}] ${f.webkitRelativePath || f.name} (${f.size}B)`);
  }
  if (e.target.files.length > 10) {
    console.log(`   ... 외 ${e.target.files.length - 10}개 더`);
  }
  Workspace.handleFiles(e.target.files, { attachAfter: false });
  e.target.value = "";
});
