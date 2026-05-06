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
    el.scrollTop = el.scrollHeight;
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
  },

  async send() {
    const text = composerInput.value.trim();
    if (!text) return;
    if (!State.model) {
      toast("모델을 선택하세요", "error");
      return;
    }

    composerInput.value = "";
    composerInput.style.height = "auto";

    State.messages.push({ role: "user", content: text });
    Chat.appendMessage("user", text);

    const assistantNode = Chat.appendMessage("assistant", "");
    assistantNode.innerHTML = '<span class="cursor"></span>';
    let buffer = "";

    State.streaming = true;
    $("#btnSend").textContent = "중단";
    $("#btnSend").classList.add("stop");
    $("#metaStatus").textContent = "스트리밍 중…";

    const ac = new AbortController();
    State.abortController = ac;

    const payload = {
      model: State.model,
      messages: State.messages,
      skills: Array.from(State.activeSkills),
      effort: State.effort,
      enable_knowledge: State.enableKnowledge,
      workspace_files: State.workspaceFiles,
      system_prompt: State.systemPromptExtra || "",
      disable_fallback: true,
    };

    try {
      const r = await fetch("/api/code/chat/stream", {
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

      // 자동 세션 저장 (하네스 미가용 시 조용히 무시)
      try {
        await fetch("/api/harness/session/save", {
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
  // highlight.js 적용
  if (window.hljs) {
    $$("pre code", root).forEach(c => { try { hljs.highlightElement(c); } catch {} });
  }
}
