/* code_assist_v1/static/chat.js — 메시지 렌더 + SSE 스트리밍 */

const Chat = {
  appendMessage(role, content = "") {
    const wrap = document.createElement("div");
    wrap.className = "msg " + role;
    const av = document.createElement("div");
    av.className = "avatar";
    av.textContent = role === "user" ? "U" : "A";
    const body = document.createElement("div");
    body.className = "body";
    const r = document.createElement("div");
    r.className = "role";
    r.textContent = role === "user" ? "You" : "Assistant";
    const c = document.createElement("div");
    c.className = "content";
    c.dataset.raw = content;
    if (role === "user") c.textContent = content;
    else c.innerHTML = renderMd(content);
    body.appendChild(r);
    body.appendChild(c);
    wrap.appendChild(av);
    wrap.appendChild(body);
    $("#messages").appendChild(wrap);
    Chat.scrollToBottom();
    return c;
  },

  clear() {
    $("#messages").innerHTML = "";
  },

  scrollToBottom() {
    const el = $("#messages");
    if (!el) return;
    // 매 토큰 도착 시 layout 갱신 후 스크롤되도록 한 프레임 지연
    // (innerHTML 재렌더링 직후엔 scrollHeight가 아직 업데이트 안 됨)
    requestAnimationFrame(() => {
      el.scrollTop = el.scrollHeight;
    });
  },

  refreshChips() {
    const chips = $("#composerChips");
    chips.innerHTML = "";
    State.activeSkills.forEach(sid => {
      const c = document.createElement("span");
      c.className = "chip";
      c.innerHTML = `🛠 ${sid} <span class="x">✕</span>`;
      c.querySelector(".x").addEventListener("click", () => {
        State.activeSkills.delete(sid);
        Chat.refreshChips();
        Skills.render();
        refreshMetaBar();
      });
      chips.appendChild(c);
    });
    if (State.enableKnowledge) {
      const c = document.createElement("span");
      c.className = "chip kb";
      c.innerHTML = `📚 도메인 지식 ON <span class="x">✕</span>`;
      c.querySelector(".x").addEventListener("click", () => {
        State.enableKnowledge = false;
        $("#btnKB").classList.remove("active");
        Chat.refreshChips();
        refreshMetaBar();
      });
      chips.appendChild(c);
    }
    State.workspaceFiles.forEach(f => {
      const c = document.createElement("span");
      c.className = "chip file";
      c.innerHTML = `📄 ${f.filename} <span class="x">✕</span>`;
      c.querySelector(".x").addEventListener("click", () => {
        State.workspaceFiles = State.workspaceFiles.filter(x => x !== f);
        Chat.refreshChips();
        refreshMetaBar();
      });
      chips.appendChild(c);
    });
    State.pastedImages.forEach(img => {
      const c = document.createElement("span");
      c.className = "chip image";
      c.innerHTML = `<img src="${img.dataUrl}" class="chip-thumb" alt=""> <span class="thumb-label">🖼 ${(img.size / 1024).toFixed(0)}K</span> <span class="x">✕</span>`;
      c.querySelector(".x").addEventListener("click", () => {
        State.pastedImages = State.pastedImages.filter(x => x !== img);
        Chat.refreshChips();
        refreshMetaBar();
      });
      // 썸네일 클릭 → 모달로 원본 보기
      c.querySelector(".chip-thumb").addEventListener("click", () => {
        const w = document.createElement("div");
        w.innerHTML = `<img src="${img.dataUrl}" style="max-width:100%;max-height:70vh;display:block;margin:0 auto;">`;
        Modal.open({ title: img.name, body: w, footButtons: [{ label: "닫기" }] });
      });
      chips.appendChild(c);
    });
  },

  async send() {
    const text = composerInput.value.trim();
    const hasImages = State.pastedImages.length > 0;
    if (!text && !hasImages) return;
    if (!State.model) {
      toast("모델을 선택하세요", "error");
      return;
    }

    composerInput.value = "";
    composerInput.style.height = "auto";

    // 이미지가 있으면 OpenAI 호환 multimodal 형식으로 전송
    let userContent;
    if (hasImages) {
      const parts = [];
      if (text) parts.push({ type: "text", text });
      for (const img of State.pastedImages) {
        parts.push({ type: "image_url", image_url: { url: img.dataUrl } });
      }
      userContent = parts;
    } else {
      userContent = text;
    }

    State.messages.push({ role: "user", content: userContent });
    // UI 표시: 텍스트 + 이미지 썸네일
    const userNode = Chat.appendMessage("user", text || "(이미지)");
    if (hasImages) {
      const gallery = document.createElement("div");
      gallery.className = "msg-image-gallery";
      State.pastedImages.forEach(img => {
        const im = document.createElement("img");
        im.src = img.dataUrl;
        im.alt = img.name;
        im.title = img.name;
        gallery.appendChild(im);
      });
      userNode.appendChild(gallery);
    }
    // 전송 후 보관 비움
    State.pastedImages = [];
    Chat.refreshChips();
    refreshMetaBar();

    const assistantNode = Chat.appendMessage("assistant", "");
    assistantNode.innerHTML = '<span class="cursor"></span>';
    let buffer = "";

    State.streaming = true;
    $("#btnSend").textContent = "중단";
    $("#btnSend").classList.add("stop");
    $("#metaStatus").textContent = "스트리밍 중…";

    const ac = new AbortController();
    State.abortController = ac;

    // demos_v1 로그인 user_id 추출 (지식베이스 user_id별 폴더 검색용)
    let _chatUid = null;
    try {
      const _u = JSON.parse(sessionStorage.getItem('demos_user') || 'null');
      if (_u && _u.id) _chatUid = _u.id;
    } catch {}

    // 사고 모드 체크박스 상태 (체크 시 모델이 reasoning 토큰 생성)
    const _thinkEl = document.getElementById('thinkToggle');
    const _thinkMode = !!(_thinkEl && _thinkEl.checked);

    const payload = {
      model: State.model,
      messages: State.messages,
      skills: Array.from(State.activeSkills),
      effort: State.effort,
      enable_knowledge: State.enableKnowledge,
      workspace_files: State.workspaceFiles,
      system_prompt: State.systemPromptExtra || "",
      disable_fallback: true,
      user_id: _chatUid,
      think_mode: _thinkMode,
    };

    try {
      const r = await fetch("api/code/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: ac.signal,
      });
      if (!r.ok || !r.body) {
        throw new Error(`HTTP ${r.status}`);
      }

      const reader = r.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let pending = "";
      let meta = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        pending += decoder.decode(value, { stream: true });

        let nl;
        while ((nl = pending.indexOf("\n\n")) !== -1) {
          const event = pending.slice(0, nl);
          pending = pending.slice(nl + 2);
          if (!event.startsWith("data:")) continue;
          const json = event.slice(5).trim();
          if (!json) continue;
          let obj;
          try { obj = JSON.parse(json); }
          catch { continue; }

          if (obj.error) {
            assistantNode.innerHTML = `<p style="color:var(--error)">⚠ ${obj.error}</p>`;
            throw new Error(obj.error);
          }
          if (obj.delta) {
            buffer += obj.delta;
            assistantNode.dataset.raw = buffer;
            assistantNode.innerHTML = renderMd(buffer) + '<span class="cursor"></span>';
            Chat.scrollToBottom();
          }
          if (obj.done) {
            meta = obj;
          }
        }
      }

      // 종료
      assistantNode.innerHTML = renderMd(buffer);
      attachCopyButtons(assistantNode);
      State.messages.push({ role: "assistant", content: buffer });
      // 모델이 수정을 제안했으면 미리보기 + 적용 버튼을 붙인다
      Chat.offerEdits(assistantNode, buffer);

      // 자동 세션 저장 (하네스 미가용 시 조용히 무시)
      try {
        await fetch("api/code/session/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: State.session_id,
            messages: State.messages,
            skills_used: Array.from(State.activeSkills),
            metadata: { source: "code_assist_v1", model: State.model },
          }),
        }).then(r => r.ok ? r.json() : null).then(j => {
          if (j?.session_id) State.session_id = j.session_id;
        });
      } catch {}

      if (meta) {
        const parts = [];
        if (meta.model_used) parts.push(`model=${meta.model_used}`);
        if (meta.elapsed_ms) parts.push(`${meta.elapsed_ms}ms`);
        if (meta.knowledge_files?.length) parts.push(`kb=${meta.knowledge_files.length}`);
        $("#metaStatus").textContent = parts.join(" · ");
      } else {
        $("#metaStatus").textContent = "완료";
      }
    } catch (e) {
      if (e.name === "AbortError") {
        assistantNode.innerHTML = renderMd(buffer || "") +
          '<p style="color:var(--muted);font-size:12px;">⏹ 중단됨</p>';
        $("#metaStatus").textContent = "중단됨";
      } else {
        toast("스트리밍 오류: " + e.message, "error");
        $("#metaStatus").textContent = "오류";
      }
    } finally {
      State.streaming = false;
      State.abortController = null;
      $("#btnSend").textContent = "전송";
      $("#btnSend").classList.remove("stop");
    }
  },

  stop() {
    if (State.abortController) {
      State.abortController.abort();
    }
  },
};

// 마크다운 렌더 (marked.js 사용, 폐쇄망 폴백 mini parser)
// ── 모델이 낸 수정을 워크스페이스에 반영 ──
// ★여기가 '채팅' 과 '에이전트' 의 갈림길이다. 예전엔 모델이 코드를 뱉으면
//   사람이 눈으로 골라 손으로 붙여 넣었다.
//   먼저 미리보기(diff)를 보여 주고, 사람이 눌러야 실제로 쓴다 — 모델이
//   멋대로 파일을 갈아엎게 두지 않는다.
Chat.offerEdits = async function (node, text) {
  if (!/```(edit|write):/.test(text || "")) return;
  let prev;
  try {
    prev = await api("api/code/edits/preview", {
      method: "POST", body: { text, user_id: _wsUid() || undefined },
    });
  } catch (e) {
    console.warn("[edits] 미리보기 실패:", e.message);
    return;
  }
  if (!prev.edits || !prev.edits.length) return;

  const box = document.createElement("div");
  box.className = "edit-offer";
  // ★이미 적용한 건 다시 적용하면 안 된다. edit 는 SEARCH 가 이미 바뀌어
  //   있어 실패하고, write 는 그 뒤에 손으로 고친 것을 조용히 덮어쓴다.
  const doneList = prev.edits.filter(e => e.already);
  const okList = prev.edits.filter(e => e.ok && !e.already);
  const badList = prev.edits.filter(e => !e.ok);

  const head = document.createElement("div");
  head.className = "edit-offer-head";
  head.textContent = okList.length
    ? `📝 파일 수정 제안 — 적용 가능 ${okList.length}건`
      + (doneList.length ? ` · 이미 적용 ${doneList.length}건` : "")
      + (badList.length ? ` · 거절 ${badList.length}건` : "")
    : (doneList.length && !badList.length
        ? `✓ 이 수정은 이미 적용했습니다 (${doneList.length}건)`
        : `📝 파일 수정 제안 — 적용할 것 없음`
          + (doneList.length ? ` · 이미 적용 ${doneList.length}건` : "")
          + (badList.length ? ` · 거절 ${badList.length}건` : ""));
  box.appendChild(head);

  prev.edits.forEach(e => {
    const row = document.createElement("div");
    row.className = "edit-row " + (e.already ? "done" : e.ok ? "ok" : "bad");
    const why = e.already ? "이미 적용됨" : (e.ok ? "" : e.reason);
    row.innerHTML = `<code>${e.already ? "✓ " : ""}${e.path}</code>`
      + ` <span class="edit-why">${why}</span>`;
    if (e.diff && !e.already) {
      const pre = document.createElement("pre");
      pre.className = "edit-diff";
      pre.textContent = e.diff;
      row.appendChild(pre);
    }
    box.appendChild(row);
  });

  if (okList.length) {
    const btn = document.createElement("button");
    btn.className = "btn-apply-edits";
    btn.textContent = `워크스페이스에 적용 (${okList.length}건)`;
    btn.onclick = async () => {
      btn.disabled = true;
      btn.textContent = "적용 중…";
      try {
        const r = await api("api/code/edits/apply", {
          method: "POST", body: { text, user_id: _wsUid() || undefined },
        });
        // ★적용했으면 버튼이 다시 눌리면 안 된다. 새로고침해도 서버
        //   기록(.applied.json)이 남아 있어 '이미 적용됨' 으로 뜬다.
        btn.textContent = `✓ ${r.applied}건 적용됨`
          + (r.failed ? ` · ${r.failed}건 거절` : "");
        btn.classList.add("done");
        toast(`${r.applied}건 적용`, r.failed ? "warn" : "ok");
        // 적용된 내용이 다음 질문에도 반영되도록 첨부본을 새로 읽는다.
        // ★안 하면 모델은 고치기 전 코드를 계속 보고 같은 수정을 또 낸다.
        const paths = [...new Set(r.edits.filter(x => x.ok).map(x => x.path))];
        if (paths.length) {
          try {
            const bulk = await api("api/code/workspace/files", {
              method: "POST", body: { paths, user_id: _wsUid() || undefined },
            });
            (bulk.files || []).forEach(f => {
              const cur = State.workspaceFiles.find(x => x.filename === f.filename);
              if (cur) cur.content = f.content;
              else State.workspaceFiles.push(f);
            });
          } catch {}
        }
        Chat.refreshChips();
        // ★window.Workspace 는 늘 undefined 다 — 이 파일들은 일반 스크립트라
        //   최상위 const 가 window 에 안 붙는다. 그래서 이 줄은 한 번도
        //   실행되지 않았고, 수정을 적용해도 워크스페이스 트리와 '고친 파일'
        //   목록이 갱신되지 않았다. 이름으로 직접 본다.
        if (typeof Workspace !== "undefined") Workspace.refresh();
        // 적용했으면 바로 받을 수 있게 — 고친 파일만
        addDownloadRow(box, paths);
      } catch (e) {
        btn.disabled = false;
        btn.textContent = "적용 실패 — 다시";
        toast("적용 실패: " + e.message, "error");
      }
    };
    box.appendChild(btn);
  }
  node.appendChild(box);
};

// ★고친 뒤 바로 받을 수 있어야 한다. 프로젝트를 통째로 다시 받는 건 낭비다 —
//   300개 중 두 개를 고쳤으면 그 둘만 받으면 된다.
function addDownloadRow(box, paths) {
  if (box.querySelector(".edit-dl")) return;
  const uid = (typeof _wsUid === "function" && _wsUid()) || "";
  const q = uid ? "&user_id=" + encodeURIComponent(uid) : "";
  const row = document.createElement("div");
  row.className = "edit-dl";
  row.innerHTML =
    `<a href="api/code/workspace/download?changed=1${q}" download>📥 고친 파일만 받기</a>`
    + (paths && paths.length === 1
        ? ` <a href="api/code/workspace/download?path=${encodeURIComponent(paths[0])}${q}" download>📄 ${paths[0]}</a>`
        : "")
    + ` <a href="api/code/workspace/download?${q.slice(1)}" download>📦 전체 받기</a>`;
  box.appendChild(row);
  Chat.refreshDownloadBar();
}

/* ══════════ 채팅 옆 고정 다운로드 바 ══════════
   ★없어지던 이유: 받기 링크가 '그 메시지' 안에 DOM 으로만 붙어 있었다.
     세션을 다시 열면 Chat.clear() 로 메시지를 통째로 지우고 저장된 본문만
     다시 그리므로, DOM 으로만 있던 받기 줄은 같이 사라졌다. 새로고침도
     마찬가지다.
   ★그래서 메시지에서 떼어 낸다. 워크스페이스에 고친 파일이 남아 있는 한
     화면 위에 계속 떠 있어야 한다 — 언제든 다시 받을 수 있어야 하니까. */
Chat.refreshDownloadBar = async function () {
  const bar = document.getElementById("chatDlBar");
  if (!bar) return;
  const uid = (typeof _wsUid === "function" && _wsUid()) || "";
  const q = uid ? "&user_id=" + encodeURIComponent(uid) : "";
  let d;
  try {
    d = await api("api/code/workspace/changes" + (uid ? "?user_id=" + encodeURIComponent(uid) : ""));
  } catch { bar.style.display = "none"; return; }
  if (!d || !d.count) { bar.style.display = "none"; bar.innerHTML = ""; return; }

  const names = (d.items || []).slice(0, 3).map(i => i.path).join(", ");
  bar.style.display = "flex";
  bar.innerHTML =
    `<span class="chat-dl-n">✏️ 고친 파일 ${d.count}개</span>`
    + `<span class="chat-dl-p" title="${(d.items || []).map(i => i.path).join("\n")}">`
    + `${names}${d.count > 3 ? ` 외 ${d.count - 3}개` : ""}</span>`
    + `<a class="chat-dl-a" href="api/code/workspace/download?changed=1${q}" download>📥 고친 파일만 받기</a>`
    + `<a class="chat-dl-a" href="api/code/workspace/download?${q.slice(1)}" download>📦 전체 받기</a>`;
};

function renderMd(text) {
  if (!text) return "";
  if (window.marked) {
    try { return marked.parse(text); }
    catch { /* fallthrough */ }
  }
  return miniRenderMd(text);
}

// marked.js 로드 실패 시 폴백 (코드블록·헤딩·리스트만)
function miniRenderMd(t) {
  const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  // 코드블록
  t = t.replace(/```(\w*)\n([\s\S]*?)```/g, (m, lang, code) =>
    `<pre><code class="language-${lang}">${esc(code)}</code></pre>`);
  // 인라인 코드
  t = t.replace(/`([^`\n]+)`/g, (m, c) => `<code>${esc(c)}</code>`);
  // 헤딩
  t = t.replace(/^### (.+)$/gm, "<h3>$1</h3>")
       .replace(/^## (.+)$/gm, "<h2>$1</h2>")
       .replace(/^# (.+)$/gm, "<h1>$1</h1>");
  // 굵게/기울임
  t = t.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
       .replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "<em>$1</em>");
  // 리스트 (간단)
  t = t.replace(/(?:^|\n)(- .+(?:\n- .+)*)/g, m => {
    const items = m.trim().split("\n").map(l => `<li>${l.replace(/^- /, "")}</li>`).join("");
    return `\n<ul>${items}</ul>`;
  });
  // 단락
  t = t.split(/\n{2,}/).map(p =>
    /^<(h\d|ul|ol|pre|blockquote)/.test(p.trim()) ? p : `<p>${p.replace(/\n/g, "<br>")}</p>`
  ).join("\n");
  return t;
}

// 코드블록에 복사 버튼 부착
function attachCopyButtons(root) {
  $$("pre", root).forEach(pre => {
    if (pre.querySelector(".copy-btn")) return;
    const btn = document.createElement("button");
    btn.className = "copy-btn";
    btn.textContent = "복사";
    btn.onclick = () => {
      const code = pre.querySelector("code")?.textContent || pre.textContent;
      navigator.clipboard.writeText(code).then(
        () => { btn.textContent = "복사됨"; setTimeout(() => btn.textContent = "복사", 1500); },
        () => toast("복사 실패", "error")
      );
    };
    pre.appendChild(btn);
  });
  collapseLongCode(root);
  // highlight.js 적용
  if (window.hljs) {
    $$("pre code", root).forEach(c => { try { hljs.highlightElement(c); } catch {} });
  }
}

// ── 긴 코드 블록은 접는다 ──
// ★모델에게 '바뀐 부분만 내놔라' 라고 시켜도 가끔 파일을 통째로 뱉는다.
//   그러면 화면이 코드로 뒤덮여서 정작 무엇이 바뀌었는지 안 보인다.
//   지우지는 않는다 — 사용자가 일부러 '전체 코드 보여줘' 라고 했을 수도
//   있으니, 접어 두고 펼 수 있게만 한다.
const CODE_FOLD_LINES = 30;
function collapseLongCode(root) {
  $$("pre", root).forEach(pre => {
    if (pre.dataset.folded) return;
    const code = pre.querySelector("code") || pre;
    const n = (code.textContent || "").split("\n").length;
    if (n <= CODE_FOLD_LINES) return;
    pre.dataset.folded = "1";
    pre.classList.add("folded");
    const bar = document.createElement("button");
    bar.className = "fold-btn";
    bar.textContent = `▼ ${n}줄 — 펼치기`;
    bar.onclick = () => {
      const on = pre.classList.toggle("folded");
      bar.textContent = on ? `▼ ${n}줄 — 펼치기` : `▲ 접기`;
    };
    pre.appendChild(bar);
  });
}
