/* code_assist_v1/static/app.js — 전역 상태·토스트·모달·탭 */

const State = {
  session_id: null,              // 자동 세션 ID (하네스 저장 시 채워짐)
  model: "",
  effort: 2,
  activeSkills: new Set(),       // skill_id
  enableKnowledge: false,        // 📚 토글
  workspaceFiles: [],            // [{filename, content}] 첨부
  pastedImages: [],              // [{name, mime, dataUrl}] — 다음 전송 시 user 메시지에 multimodal 로 첨부
  messages: [],                  // [{role, content}]
  streaming: false,
  abortController: null,         // 스트리밍 중단용
  systemPromptExtra: localStorage.getItem("code_assist_v1.systemPromptExtra") || "",
};

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

// ── 토스트 ──
function toast(msg, kind = "") {
  const wrap = $("#toastWrap");
  const el = document.createElement("div");
  el.className = "toast " + kind;
  el.textContent = msg;
  wrap.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ── 모달 ──
const Modal = {
  open({ title, body, footButtons = [] }) {
    $("#modalTitle").textContent = title || "";
    $("#modalBody").innerHTML = "";
    if (typeof body === "string") $("#modalBody").innerHTML = body;
    else if (body instanceof Node) $("#modalBody").appendChild(body);

    const foot = $("#modalFoot");
    foot.innerHTML = "";
    footButtons.forEach(b => {
      const btn = document.createElement("button");
      btn.textContent = b.label;
      if (b.primary) btn.className = "primary";
      if (b.danger) btn.className = "danger";
      btn.onclick = () => {
        const result = b.onClick?.();
        if (result !== false) Modal.close();
      };
      foot.appendChild(btn);
    });
    $("#modalBg").classList.add("show");
  },
  close() { $("#modalBg").classList.remove("show"); },
};
$("#modalBg").addEventListener("click", e => { if (e.target.id === "modalBg") Modal.close(); });
$("#modalClose").addEventListener("click", Modal.close);

// ── API 헬퍼 ──
async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  const init = { method: opts.method || "GET", headers };
  if (opts.body !== undefined) init.body = JSON.stringify(opts.body);
  const r = await fetch(path, init);
  if (!r.ok) {
    let err = `HTTP ${r.status}`;
    try { const j = await r.json(); err = j.error || err; } catch {}
    throw new Error(err);
  }
  return r.json();
}

// ── 모델 목록 로드 ──
async function loadModels() {
  try {
    const data = await api("/api/code/models");
    const sel = $("#modelSelect");
    sel.innerHTML = "";

    if (data.api?.length) {
      const og = document.createElement("optgroup");
      og.label = "API 모델";
      data.api.forEach(m => {
        const opt = document.createElement("option");
        opt.value = m.id;
        opt.textContent = `${m.name || m.id}`;
        og.appendChild(opt);
      });
      sel.appendChild(og);
    }
    if (data.gguf?.length) {
      const og = document.createElement("optgroup");
      og.label = "GGUF (로컬)";
      data.gguf.forEach(m => {
        const opt = document.createElement("option");
        opt.value = m.id;
        opt.textContent = `${m.name} (${m.size_gb}GB)`;
        og.appendChild(opt);
      });
      sel.appendChild(og);
    }

    const def = data.default;
    if (def && [...sel.options].some(o => o.value === def)) {
      sel.value = def;
    }
    State.model = sel.value;
    refreshMetaBar();
  } catch (e) {
    toast("모델 목록 로드 실패: " + e.message, "error");
  }
}

// ── 메타바 ──
function refreshMetaBar() {
  $("#metaModel").textContent = "model: " + (State.model || "-");
  $("#metaSkills").textContent = "skills: " + State.activeSkills.size;
  $("#metaKB").textContent = "KB: " + (State.enableKnowledge ? "ON" : "off");
  $("#metaWS").textContent = "files: " + State.workspaceFiles.length
    + (State.pastedImages.length ? `+🖼${State.pastedImages.length}` : "");
}

// ── 사이드바 탭 ──
let currentTab = "skills";
function setTab(name) {
  currentTab = name;
  $$(".sidebar .tabs button").forEach(b => b.classList.toggle("active", b.dataset.tab === name));
  if (name === "skills") Skills.render();
  else if (name === "knowledge") Knowledge.render();
  else if (name === "sessions") Sessions.render();
}
$$(".sidebar .tabs button").forEach(b => b.addEventListener("click", () => setTab(b.dataset.tab)));

// ── 사이드바 검색·추가 ──
$("#sidebarSearch").addEventListener("input", e => {
  if (currentTab === "skills") Skills.render(e.target.value);
  else if (currentTab === "knowledge") Knowledge.render(e.target.value);
});
$("#sidebarAddBtn").addEventListener("click", () => {
  if (currentTab === "skills") Skills.openCreate();
  else if (currentTab === "knowledge") Knowledge.openCreate();
  else if (currentTab === "sessions") {
    State.messages = [];
    State.session_id = null;
    Chat.clear();
    toast("새 세션 시작");
  }
});

// ── 모델 선택·effort ──
$("#modelSelect").addEventListener("change", e => {
  State.model = e.target.value;
  refreshMetaBar();
});
$("#effortSelect").addEventListener("change", e => {
  State.effort = parseInt(e.target.value, 10);
});
$("#newSessionBtn").addEventListener("click", () => {
  State.messages = [];
  State.session_id = null;
  Chat.clear();
  refreshMetaBar();
  toast("새 세션 시작");
});

// ── 시스템 프롬프트 모달 ──
async function openSystemPromptModal() {
  let info;
  try {
    info = await api("/api/code/system_prompt");
  } catch (e) {
    toast("시스템 프롬프트 로드 실패: " + e.message, "error");
    return;
  }
  const body = document.createElement("div");
  body.innerHTML = `
    <label>기본 시스템 프롬프트 <span style="color:var(--muted);font-weight:400;">(읽기 전용)</span></label>
    <textarea id="spBase" readonly style="background:var(--code-bg);min-height:160px;font-size:12px;"></textarea>
    <label>반-환각 가드 <span style="color:var(--muted);font-weight:400;">(읽기 전용)</span></label>
    <textarea id="spAnti" readonly style="background:var(--code-bg);min-height:80px;font-size:12px;"></textarea>
    <label>사용자 추가 지시 <span style="color:var(--accent);font-weight:400;">(편집 가능, 자동 저장)</span></label>
    <textarea id="spExtra" placeholder="예: 답변은 항상 한국어로. 코드는 Python 3.11 문법으로." style="min-height:120px;"></textarea>
    <p style="color:var(--muted);font-size:11px;margin-top:8px;line-height:1.6;">
      💡 활성 스킬 본문 + (KB ON 시) 도메인 지식 + 워크스페이스 첨부 파일이 위 프롬프트에 더해져 LLM 에 전달됩니다.<br>
      💡 사용자 추가 지시는 브라우저에 저장돼 다음 세션에도 유지됩니다.
    </p>
  `;
  Modal.open({
    title: "시스템 프롬프트",
    body,
    footButtons: [
      { label: "초기화", danger: true, onClick: () => {
        const extra = $("#spExtra");
        if (extra) extra.value = "";
        State.systemPromptExtra = "";
        localStorage.removeItem("code_assist_v1.systemPromptExtra");
        toast("사용자 추가 지시 초기화됨", "ok");
        return false;  // 모달 유지 (사용자가 다시 입력하거나 닫기로 나감)
      }},
      { label: "저장", primary: true, onClick: () => {
        const extra = $("#spExtra");
        const val = extra ? extra.value : "";
        State.systemPromptExtra = val;
        localStorage.setItem("code_assist_v1.systemPromptExtra", val);
        toast(`저장됨 (${val.length}자)`, "ok");
        return false;  // 모달 유지
      }},
      { label: "닫기" },
    ],
  });
  $("#spBase").value = info.base || "";
  $("#spAnti").value = info.anti_hallucination || "";
  const extra = $("#spExtra");
  extra.value = State.systemPromptExtra;
  // 자동 저장도 유지 (편의)
  extra.addEventListener("input", () => {
    State.systemPromptExtra = extra.value;
    localStorage.setItem("code_assist_v1.systemPromptExtra", extra.value);
  });
}
$("#systemPromptBtn").addEventListener("click", openSystemPromptModal);

// ── 테마 토글 (다크/라이트) ──
function applyTheme(name) {
  document.documentElement.setAttribute("data-theme", name);
  $("#themeBtn").textContent = name === "light" ? "☀️" : "🌙";
  $("#themeBtn").title = name === "light" ? "라이트 → 다크 전환" : "다크 → 라이트 전환";
  // highlight.js 코드블록 스타일 동적 교체
  const linkId = "hljs-theme-link";
  let link = document.getElementById(linkId);
  if (!link) {
    link = document.createElement("link");
    link.id = linkId;
    link.rel = "stylesheet";
    document.head.appendChild(link);
  }
  link.href = name === "light"
    ? "https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/styles/github.min.css"
    : "https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/styles/github-dark.min.css";
}

const _initialTheme = localStorage.getItem("code_assist_v1.theme") || "dark";
applyTheme(_initialTheme);

$("#themeBtn").addEventListener("click", () => {
  const cur = document.documentElement.getAttribute("data-theme") || "dark";
  const next = cur === "dark" ? "light" : "dark";
  applyTheme(next);
  localStorage.setItem("code_assist_v1.theme", next);
  toast(next === "light" ? "☀️ 라이트 모드" : "🌙 다크 모드", "ok");
});

// ── KB 토글 ──
$("#btnKB").addEventListener("click", () => {
  State.enableKnowledge = !State.enableKnowledge;
  $("#btnKB").classList.toggle("active", State.enableKnowledge);
  Chat.refreshChips();
  refreshMetaBar();
  toast(State.enableKnowledge ? "📚 도메인 지식 검색 ON" : "도메인 지식 검색 OFF", "ok");
});

// ── 첨부 ──
$("#btnAttach").addEventListener("click", () => $("#hiddenFileInput").click());
$("#hiddenFileInput").addEventListener("change", e => {
  Workspace.handleAttach(e.target.files);
  e.target.value = "";
});

// ── 입력 박스 ──
const composerInput = $("#composerInput");
composerInput.addEventListener("input", () => {
  composerInput.style.height = "auto";
  composerInput.style.height = Math.min(composerInput.scrollHeight, 200) + "px";
});
composerInput.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    Chat.send();
  } else if (e.key === "Escape" && State.streaming) {
    Chat.stop();
  }
});

// ── 클립보드 이미지 붙여넣기 (Ctrl/Cmd+V) → VLM multimodal 첨부 ──
const MAX_PASTED_IMAGE_MB = 20;

function _readImageItem(item) {
  return new Promise((resolve, reject) => {
    const blob = item.getAsFile();
    if (!blob) { reject(new Error("blob 없음")); return; }
    if (blob.size > MAX_PASTED_IMAGE_MB * 1024 * 1024) {
      reject(new Error(`이미지가 ${MAX_PASTED_IMAGE_MB}MB 초과`));
      return;
    }
    const reader = new FileReader();
    reader.onload = () => resolve({
      name: blob.name || `clip-${Date.now()}.${(blob.type.split("/")[1] || "png")}`,
      mime: blob.type || "image/png",
      dataUrl: reader.result,
      size: blob.size,
    });
    reader.onerror = () => reject(reader.error || new Error("read 실패"));
    reader.readAsDataURL(blob);
  });
}

composerInput.addEventListener("paste", async e => {
  const items = e.clipboardData?.items || [];
  const imageItems = [...items].filter(it => it.kind === "file" && it.type.startsWith("image/"));
  if (!imageItems.length) return;  // 텍스트 paste 는 기본 동작
  e.preventDefault();
  for (const it of imageItems) {
    try {
      const img = await _readImageItem(it);
      State.pastedImages.push(img);
      toast(`🖼 이미지 첨부 (${(img.size / 1024).toFixed(0)}K)`, "ok");
    } catch (err) {
      toast("이미지 붙여넣기 실패: " + err.message, "error");
    }
  }
  Chat.refreshChips();
  refreshMetaBar();
});

$("#btnSend").addEventListener("click", () => {
  if (State.streaming) Chat.stop();
  else Chat.send();
});

// 마크다운 렌더 옵션 (highlight.js 자동 적용)
if (window.marked) {
  marked.setOptions({
    breaks: true,
    gfm: true,
    highlight: (code, lang) => {
      if (window.hljs && lang && hljs.getLanguage(lang)) {
        try { return hljs.highlight(code, { language: lang }).value; }
        catch {}
      }
      return code;
    },
  });
}

// ── 부트 ──
window.addEventListener("DOMContentLoaded", async () => {
  await loadModels();
  setTab("skills");
  Workspace.refresh();
});
