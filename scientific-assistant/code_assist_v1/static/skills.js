/* code_assist_v1/static/skills.js — 스킬 패널 + 작성 모달 (단일 폴더, source 구분 없음) */

const SKILL_KO = {
  // ===== agent-* (역할 기반 에이전트) =====
  "agent-ai-engineer": "AI 엔지니어",
  "agent-angular-architect": "Angular 아키텍트",
  "agent-api-designer": "API 설계자",
  "agent-api-documenter": "API 문서화 전문가",
  "agent-architect-reviewer": "아키텍처 리뷰어",
  "agent-backend-developer": "백엔드 개발자",
  "agent-cloud-architect": "클라우드 아키텍트",
  "agent-code-reviewer": "코드 리뷰어",
  "agent-cpp-pro": "C++ 전문가",
  "agent-csharp-developer": "C# 개발자",
  "agent-data-engineer": "데이터 엔지니어",
  "agent-database-administrator": "DB 관리자",
  "agent-database-optimizer": "DB 최적화 전문가",
  "agent-datadog-api-expert": "Datadog API 전문가",
  "agent-datadog-pro": "Datadog 전문가",
  "agent-debugger": "디버거",
  "agent-devops-engineer": "DevOps 엔지니어",
  "agent-devops-incident-responder": "DevOps 장애 대응",
  "agent-django-developer": "Django 개발자",
  "agent-dx-optimizer": "개발자 경험(DX) 최적화",
  "agent-frontend-developer": "프론트엔드 개발자",
  "agent-fullstack-developer": "풀스택 개발자",
  "agent-golang-pro": "Go 전문가",
  "agent-graphql-architect": "GraphQL 아키텍트",
  "agent-java-architect": "Java 아키텍트",
  "agent-javascript-pro": "JavaScript 전문가",
  "agent-kotlin-specialist": "Kotlin 전문가",
  "agent-laravel-specialist": "Laravel 전문가",
  "agent-llm-architect": "LLM 아키텍트",
  "agent-microservices-architect": "마이크로서비스 아키텍트",
  "agent-ml-engineer": "ML 엔지니어",
  "agent-mobile-app-developer": "모바일 앱 개발자",
  "agent-mobile-developer": "모바일 개발자",
  "agent-nextjs-developer": "Next.js 개발자",
  "agent-performance-engineer": "성능 엔지니어",
  "agent-performance-monitor": "성능 모니터링",
  "agent-platform-engineer": "플랫폼 엔지니어",
  "agent-python-pro": "Python 전문가",
  "agent-qa-expert": "QA 전문가",
  "agent-rails-expert": "Rails 전문가",
  "agent-react-specialist": "React 전문가",
  "agent-refactoring-specialist": "리팩토링 전문가",
  "agent-rust-engineer": "Rust 엔지니어",
  "agent-security-auditor": "보안 감사",
  "agent-security-engineer": "보안 엔지니어",
  "agent-spring-boot-engineer": "Spring Boot 엔지니어",
  "agent-sql-pro": "SQL 전문가",
  "agent-sre-engineer": "SRE 엔지니어",
  "agent-swift-expert": "Swift 전문가",
  "agent-terraform-engineer": "Terraform 엔지니어",
  "agent-typescript-pro": "TypeScript 전문가",
  "agent-vue-expert": "Vue 전문가",
  "agent-websocket-engineer": "WebSocket 엔지니어",

  // ===== 일반 워크플로우 / 도구 스킬 =====
  "backend-development": "백엔드 개발",
  "brainstorming": "브레인스토밍",
  "chrome-devtools": "Chrome 개발자 도구",
  "code-review": "코드 리뷰",
  "developer-growth-analysis": "개발자 성장 분석",
  "frontend-design": "프론트엔드 디자인",
  "frontend-development": "프론트엔드 개발",
  "knowledge-search": "지식 검색",
  "requesting-code-review": "코드 리뷰 요청",
  "skill-creator": "스킬 생성기",
  "systematic-debugging": "체계적 디버깅",
  "test-driven-development": "테스트 주도 개발(TDD)",
  "using-superpowers": "슈퍼파워 활용",
  "verification-before-completion": "완료 전 검증",
  "writing-plans": "계획 작성",
  "writing-skills": "스킬 작성",
};

const Skills = {
  cache: [],

  async fetchList(query = "") {
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    const data = await api("api/code/skills/list?" + params.toString());
    Skills.cache = data.items || [];
    return data;
  },

  async render(query = "") {
    if (currentTab !== "skills") return;
    const body = $("#sidebarBody");
    body.innerHTML = '<div style="padding:14px;color:var(--muted);font-size:12px;">로드 중…</div>';
    try {
      const data = await Skills.fetchList(query);
      body.innerHTML = "";

      const header = document.createElement("div");
      header.className = "section-title";
      header.textContent = `스킬 ${data.total}개`;
      body.appendChild(header);

      const active = Skills.cache.filter(s => State.activeSkills.has(s.id));
      const rest = Skills.cache.filter(s => !State.activeSkills.has(s.id));

      if (active.length) {
        const t = document.createElement("div");
        t.className = "section-title";
        t.textContent = "활성";
        body.appendChild(t);
        active.forEach(s => body.appendChild(Skills._row(s, true)));
      }

      if (rest.length) {
        const t2 = document.createElement("div");
        t2.className = "section-title";
        t2.textContent = active.length ? "사용 가능" : "스킬";
        body.appendChild(t2);
        rest.forEach(s => body.appendChild(Skills._row(s, false)));
      }

      if (!data.total) {
        const el = document.createElement("div");
        el.style.cssText = "padding:14px;color:var(--muted);font-size:12px;";
        el.textContent = "스킬이 없습니다. ＋ 버튼으로 만들거나 skills/ 폴더에 직접 추가하세요.";
        body.appendChild(el);
      }
    } catch (e) {
      body.innerHTML = `<div style="padding:14px;color:var(--error);font-size:12px;">로드 실패: ${e.message}</div>`;
    }
  },

  _row(s, active) {
    const row = document.createElement("div");
    row.className = "item" + (active ? " selected" : "");
    const ko = SKILL_KO[s.id] || "";
    const tip = (s.description || "").replace(/"/g, "&quot;");
    row.innerHTML = ko
      ? `<span class="name" title="${tip}" style="display:flex;flex-direction:column;line-height:1.25;">
           <span style="font-size:13px;font-weight:600;color:var(--text);">${ko}</span>
           <span style="font-size:10px;color:var(--muted);font-family:monospace;">${s.id}</span>
         </span>`
      : `<span class="name" title="${tip}">${s.id}</span>`;
    row.addEventListener("click", () => {
      if (State.activeSkills.has(s.id)) State.activeSkills.delete(s.id);
      else State.activeSkills.add(s.id);
      Chat.refreshChips();
      refreshMetaBar();
      Skills.render($("#sidebarSearch").value);
    });
    row.addEventListener("contextmenu", e => {
      e.preventDefault();
      Skills.openView(s.id);
    });
    return row;
  },

  async openView(id) {
    try {
      const data = await api(`api/code/skills/${encodeURIComponent(id)}`);
      const meta = data.meta;

      const body = document.createElement("div");
      body.innerHTML = `
        <div style="font-size:12px;color:var(--muted);margin-bottom:6px;">${meta.id}</div>
        <div style="font-size:13px;margin-bottom:8px;">${meta.description || ""}</div>
      `;
      const ta = document.createElement("textarea");
      ta.value = data.content || "";
      ta.style.minHeight = "300px";
      body.appendChild(ta);

      Modal.open({
        title: `스킬: ${id}`,
        body,
        footButtons: [
          { label: "삭제", danger: true, onClick: async () => {
            if (!confirm(`스킬 ${id} 를 삭제할까요?`)) return false;
            try {
              await api("api/code/skills/delete", { method: "POST", body: { id } });
              State.activeSkills.delete(id);
              Chat.refreshChips();
              Skills.render($("#sidebarSearch").value);
              toast("삭제됨", "ok");
            } catch (e) { toast(e.message, "error"); return false; }
          }},
          { label: "저장", primary: true, onClick: async () => {
            try {
              await api("api/code/skills/update", {
                method: "POST",
                body: { id, content: ta.value },
              });
              toast("저장됨", "ok");
            } catch (e) { toast(e.message, "error"); return false; }
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
      <label>스킬 ID (소문자/숫자/하이픈)</label>
      <input id="newSkillId" type="text" placeholder="my-coding-skill">
      <label>이름</label>
      <input id="newSkillName" type="text" placeholder="My Coding Skill">
      <label>설명 (라우터 매칭용 키워드 포함)</label>
      <input id="newSkillDesc" type="text" placeholder="FastAPI 라우트와 미들웨어를 작성한다">
      <label>태그 (쉼표 구분)</label>
      <input id="newSkillTags" type="text" placeholder="python, fastapi, backend">
      <label>본문 (마크다운)</label>
      <textarea id="newSkillBody" placeholder="# 절차

1. 첫 번째 단계
2. 두 번째 단계
"></textarea>
    `;
    Modal.open({
      title: "새 스킬 만들기",
      body,
      footButtons: [
        { label: "취소" },
        { label: "생성", primary: true, onClick: async () => {
          const id = $("#newSkillId").value.trim().toLowerCase();
          const name = $("#newSkillName").value.trim() || id;
          const description = $("#newSkillDesc").value.trim();
          const tags = $("#newSkillTags").value.split(",").map(s => s.trim()).filter(Boolean);
          const bodyText = $("#newSkillBody").value;
          if (!id) { toast("ID 필수", "error"); return false; }
          try {
            await api("api/code/skills/create", {
              method: "POST",
              body: { id, name, description, tags, body: bodyText },
            });
            toast("스킬 생성됨", "ok");
            Skills.render();
          } catch (e) { toast(e.message, "error"); return false; }
        }},
      ],
    });
  },
};
