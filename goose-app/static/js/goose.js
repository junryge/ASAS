/* ============================================
   Goose App - Frontend Logic
   ============================================ */

// ── State ──
let state = {
  providers: {},
  currentModel: 'auto',
  currentSession: null,
  sessions: [],
  extensions: [],
  recipes: [],
  subagents: [],
  messages: [],
  isStreaming: false,
  attachedFiles: [],
  settings: {
    theme: 'dark',
    max_tokens: 4096,
    temperature: 0.7,
    shortcuts: true,
  },
};

// ── Init ──
document.addEventListener('DOMContentLoaded', async () => {
  await loadConfig();
  await loadSessions();
  await loadExtensions();
  await loadRecipes();
  setupEventListeners();
  checkOnboarding();
  updateSubagentsPoll();
});

// ── Config & Providers ──
async function loadConfig() {
  try {
    const resp = await fetch('/api/config');
    const data = await resp.json();
    state.providers = data.providers || {};
    populateProviderSelects();
  } catch (e) {
    console.error('Failed to load config:', e);
  }
}

function populateProviderSelects() {
  const providers = Object.values(state.providers);
  const selects = ['obProvider', 'settingsModel', 'subagentModel'];

  selects.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const current = el.value;
    el.innerHTML = '<option value="auto">Auto (recommended)</option>';
    providers
      .sort((a, b) => a.priority - b.priority)
      .forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = `${p.name} (${p.capabilities.join(', ')})`;
        el.appendChild(opt);
      });
    if (current) el.value = current;
  });

  // Model picker modal
  const pickerList = document.getElementById('modelPickerList');
  if (pickerList) {
    pickerList.innerHTML = '';
    const autoItem = createModelPickerItem('auto', 'Auto', 'Automatically selects the best model', true);
    pickerList.appendChild(autoItem);
    providers.sort((a, b) => a.priority - b.priority).forEach(p => {
      const item = createModelPickerItem(p.id, p.name, p.capabilities.join(', '), p.id === state.currentModel);
      pickerList.appendChild(item);
    });
  }
}

function createModelPickerItem(id, name, desc, isActive) {
  const div = document.createElement('div');
  div.style.cssText = `display:flex;align-items:center;gap:12px;padding:12px;border-radius:8px;cursor:pointer;transition:all .15s;margin-bottom:4px;background:${isActive ? 'var(--accent-dim)' : 'transparent'};border:1px solid ${isActive ? 'var(--accent)' : 'transparent'};`;
  div.onmouseenter = () => { if (!isActive) div.style.background = 'var(--bg-hover)'; };
  div.onmouseleave = () => { if (!isActive) div.style.background = 'transparent'; };
  div.onclick = () => { selectModel(id); closeModelPicker(); };
  div.innerHTML = `
    <div style="width:10px;height:10px;border-radius:50%;background:${isActive ? 'var(--success)' : 'var(--text-muted)'};flex-shrink:0;"></div>
    <div style="flex:1;">
      <div style="font-size:14px;font-weight:600;color:var(--text-primary);">${name}</div>
      <div style="font-size:12px;color:var(--text-muted);">${desc}</div>
    </div>
    ${isActive ? '<span style="color:var(--accent);font-size:12px;font-weight:600;">Active</span>' : ''}
  `;
  return div;
}

function selectModel(modelId) {
  state.currentModel = modelId;
  const name = modelId === 'auto' ? 'Auto' : (state.providers[modelId]?.name || modelId);
  document.getElementById('currentModelName').textContent = name;
  document.getElementById('modelIndicator').textContent = `Model: ${name}`;
  document.getElementById('rpModel').textContent = name;
  populateProviderSelects();
}

// ── Onboarding ──
function checkOnboarding() {
  const done = localStorage.getItem('goose_onboarded');
  if (done) {
    document.getElementById('onboarding').classList.add('hidden');
    const savedModel = localStorage.getItem('goose_model') || 'auto';
    selectModel(savedModel);
    if (!state.currentSession && state.sessions.length > 0) {
      loadSession(state.sessions[0].id);
    } else if (state.sessions.length === 0) {
      createSession();
    }
  } else {
    document.getElementById('obProvider').addEventListener('change', function() {
      document.getElementById('obStartBtn').disabled = !this.value;
    });
    document.getElementById('obStartBtn').disabled = false;
  }
}

function completeOnboarding() {
  const model = document.getElementById('obProvider').value || 'auto';
  const apiKey = document.getElementById('obApiKey').value;
  localStorage.setItem('goose_onboarded', 'true');
  localStorage.setItem('goose_model', model);
  if (apiKey) localStorage.setItem('goose_api_key', apiKey);
  selectModel(model);
  document.getElementById('onboarding').classList.add('hidden');
  createSession();
}

// ── Sessions ──
async function loadSessions() {
  try {
    const resp = await fetch('/api/sessions');
    state.sessions = await resp.json();
    renderSessionList();
  } catch (e) {
    console.error('Failed to load sessions:', e);
  }
}

function renderSessionList() {
  const list = document.getElementById('sessionList');
  list.innerHTML = '';
  state.sessions.forEach(s => {
    const item = document.createElement('div');
    item.className = `session-item${s.id === state.currentSession ? ' active' : ''}`;
    item.onclick = () => loadSession(s.id);
    item.innerHTML = `
      <span class="session-icon">💬</span>
      <span class="session-name">${escapeHtml(s.name)}</span>
      <span class="session-time">${formatTime(s.updated)}</span>
      <button class="session-delete" onclick="event.stopPropagation();deleteSession('${s.id}')" title="Delete">✕</button>
    `;
    list.appendChild(item);
  });
}

async function createSession() {
  try {
    const resp = await fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: state.currentModel }),
    });
    const session = await resp.json();
    state.sessions.unshift(session);
    state.currentSession = session.id;
    state.messages = [];
    renderSessionList();
    renderMessages();
    document.getElementById('chatInput').focus();
  } catch (e) {
    console.error('Failed to create session:', e);
  }
}

async function loadSession(sid) {
  try {
    const resp = await fetch(`/api/sessions/${sid}`);
    const session = await resp.json();
    state.currentSession = sid;
    state.messages = session.messages || [];
    if (session.model) selectModel(session.model);
    renderSessionList();
    renderMessages();
  } catch (e) {
    console.error('Failed to load session:', e);
  }
}

async function deleteSession(sid) {
  try {
    await fetch(`/api/sessions/${sid}`, { method: 'DELETE' });
    state.sessions = state.sessions.filter(s => s.id !== sid);
    if (state.currentSession === sid) {
      if (state.sessions.length > 0) {
        loadSession(state.sessions[0].id);
      } else {
        createSession();
      }
    }
    renderSessionList();
  } catch (e) {
    console.error('Failed to delete session:', e);
  }
}

async function saveCurrentSession() {
  if (!state.currentSession) return;
  try {
    await fetch(`/api/sessions/${state.currentSession}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: state.messages, model: state.currentModel }),
    });
  } catch (e) {
    console.error('Failed to save session:', e);
  }
}

async function exportCurrentSession() {
  if (!state.currentSession) return;
  try {
    const resp = await fetch(`/api/sessions/${state.currentSession}/export`);
    const data = await resp.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `goose-session-${state.currentSession}.json`;
    a.click();
  } catch (e) {
    console.error('Failed to export session:', e);
  }
}

// ── Chat ──
function renderMessages() {
  const inner = document.getElementById('chatMessagesInner');
  const welcome = document.getElementById('welcomeScreen');

  if (state.messages.length === 0) {
    welcome.style.display = 'flex';
    inner.innerHTML = '';
    inner.appendChild(welcome);
    document.getElementById('rpMsgCount').textContent = '0';
    return;
  }

  welcome.style.display = 'none';
  inner.innerHTML = '';

  state.messages.forEach((msg, idx) => {
    const group = document.createElement('div');
    group.className = 'msg-group';

    const label = document.createElement('div');
    label.className = `msg-label ${msg.role === 'user' ? 'user-label' : 'assistant-label'}`;
    label.textContent = msg.role === 'user' ? 'You' : 'Goose';

    const bubble = document.createElement('div');
    bubble.className = `msg ${msg.role === 'user' ? 'user-msg' : 'assistant-msg'}`;
    bubble.id = `msg-${idx}`;

    if (msg.role === 'user') {
      bubble.textContent = msg.content;
    } else {
      bubble.innerHTML = renderMarkdown(msg.content);
    }

    group.appendChild(label);
    group.appendChild(bubble);

    if (msg.role === 'assistant') {
      const actions = document.createElement('div');
      actions.className = 'msg-actions';
      actions.innerHTML = `
        <button class="msg-action-btn" onclick="copyText(${idx})" title="Copy">📋</button>
        <button class="msg-action-btn" onclick="regenerate(${idx})" title="Regenerate">🔄</button>
      `;
      group.appendChild(actions);
    }

    inner.appendChild(group);
  });

  document.getElementById('rpMsgCount').textContent = state.messages.length;
  scrollToBottom();
}

function renderMarkdown(text) {
  if (!text) return '';
  try {
    marked.setOptions({
      highlight: function(code, lang) {
        if (lang && hljs.getLanguage(lang)) {
          return hljs.highlight(code, { language: lang }).value;
        }
        return hljs.highlightAuto(code).value;
      },
      breaks: true,
    });
    let html = marked.parse(text);
    // Add copy buttons to code blocks
    html = html.replace(/<pre><code class="language-(\w+)">/g,
      '<pre><div class="code-header"><span>$1</span><button class="copy-btn" onclick="copyCode(this)">Copy</button></div><code class="language-$1 hljs">');
    html = html.replace(/<pre><code>/g,
      '<pre><div class="code-header"><span>code</span><button class="copy-btn" onclick="copyCode(this)">Copy</button></div><code class="hljs">');
    return html;
  } catch (e) {
    return escapeHtml(text);
  }
}

async function sendMessage() {
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text || state.isStreaming) return;

  // Add user message
  state.messages.push({ role: 'user', content: text });
  input.value = '';
  input.style.height = 'auto';
  renderMessages();

  // Add file context if attached
  let fileContext = '';
  if (state.attachedFiles.length > 0) {
    fileContext = '\n\n[Attached files: ' + state.attachedFiles.map(f => f.name).join(', ') + ']';
    state.attachedFiles = [];
    document.getElementById('chatAttachments').innerHTML = '';
  }

  // Show typing indicator
  state.isStreaming = true;
  updateSendButton();
  showTypingIndicator();

  // Prepare messages for API
  const apiMessages = state.messages.map(m => ({ role: m.role, content: m.content }));
  if (fileContext) {
    apiMessages[apiMessages.length - 1].content += fileContext;
  }

  // Get active extensions
  const activeExts = state.extensions.filter(e => e.enabled).map(e => e.id);

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: apiMessages,
        model: state.currentModel,
        max_tokens: state.settings.max_tokens,
        temperature: state.settings.temperature,
        extensions: activeExts,
        stream: true,
      }),
    });

    hideTypingIndicator();

    if (!resp.ok) {
      const err = await resp.json();
      state.messages.push({ role: 'assistant', content: `Error: ${err.error || 'Request failed'}` });
      renderMessages();
      state.isStreaming = false;
      updateSendButton();
      return;
    }

    // Streaming response
    state.messages.push({ role: 'assistant', content: '' });
    renderMessages();
    const msgIdx = state.messages.length - 1;
    const msgEl = document.getElementById(`msg-${msgIdx}`);

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.done) {
            if (data.full_content) state.messages[msgIdx].content = data.full_content;
            break;
          }
          if (data.content) {
            state.messages[msgIdx].content += data.content;
            msgEl.innerHTML = renderMarkdown(state.messages[msgIdx].content);
            scrollToBottom();
          }
          if (data.error) {
            state.messages[msgIdx].content = `Error: ${data.error}`;
            msgEl.innerHTML = renderMarkdown(state.messages[msgIdx].content);
          }
        } catch (e) { /* skip parse errors */ }
      }
    }

    // Final render
    if (msgEl) msgEl.innerHTML = renderMarkdown(state.messages[msgIdx].content);
    scrollToBottom();

  } catch (e) {
    hideTypingIndicator();
    state.messages.push({ role: 'assistant', content: `Connection error: ${e.message}` });
    renderMessages();
  }

  state.isStreaming = false;
  updateSendButton();
  saveCurrentSession();
  loadSessions();
}

async function stopGeneration() {
  try {
    await fetch('/api/chat/stop', { method: 'POST' });
  } catch (e) { /* ignore */ }
  state.isStreaming = false;
  updateSendButton();
  hideTypingIndicator();
}

function useSuggestion(text) {
  document.getElementById('chatInput').value = text;
  document.getElementById('sendBtn').disabled = false;
  document.getElementById('chatInput').focus();
}

function regenerate(idx) {
  if (state.isStreaming) return;
  // Remove last assistant message and resend
  state.messages = state.messages.slice(0, idx);
  renderMessages();
  // Re-trigger send with last user message
  const lastUser = state.messages.filter(m => m.role === 'user').pop();
  if (lastUser) {
    document.getElementById('chatInput').value = lastUser.content;
    state.messages.pop();
    sendMessage();
  }
}

function copyText(idx) {
  const text = state.messages[idx]?.content || '';
  navigator.clipboard.writeText(text);
}

function copyCode(btn) {
  const code = btn.closest('pre').querySelector('code').textContent;
  navigator.clipboard.writeText(code);
  btn.textContent = 'Copied!';
  btn.classList.add('copied');
  setTimeout(() => { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 2000);
}

function showTypingIndicator() {
  const inner = document.getElementById('chatMessagesInner');
  const typing = document.createElement('div');
  typing.id = 'typingIndicator';
  typing.className = 'typing-indicator';
  typing.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
  inner.appendChild(typing);
  scrollToBottom();
}

function hideTypingIndicator() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

function updateSendButton() {
  const btn = document.getElementById('sendBtn');
  if (state.isStreaming) {
    btn.className = 'chat-stop-btn';
    btn.innerHTML = '■';
    btn.onclick = stopGeneration;
    btn.disabled = false;
  } else {
    btn.className = 'chat-send-btn';
    btn.innerHTML = '▶';
    btn.onclick = sendMessage;
    btn.disabled = !document.getElementById('chatInput').value.trim();
  }
}

function scrollToBottom() {
  const el = document.getElementById('chatMessages');
  requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; });
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 150) + 'px';
  updateSendButton();
}

// ── Extensions ──
async function loadExtensions() {
  try {
    const resp = await fetch('/api/extensions');
    state.extensions = await resp.json();
    renderExtensions();
    updateRpExtensions();
  } catch (e) {
    console.error('Failed to load extensions:', e);
  }
}

function renderExtensions() {
  const list = document.getElementById('extensionsList');
  if (!list) return;
  if (state.extensions.length === 0) {
    list.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted);"><div style="font-size:40px;margin-bottom:12px;">🧩</div><div>No extensions installed yet.</div><div style="font-size:12px;margin-top:8px;">Extensions add new capabilities like code execution, file management, and more.</div></div>';
    return;
  }
  list.innerHTML = '';
  state.extensions.forEach(ext => {
    const card = document.createElement('div');
    card.className = `ext-card${ext.enabled ? ' enabled' : ''}`;
    card.innerHTML = `
      <div class="ext-card-header">
        <div class="ext-card-name">${ext.icon || '🧩'} ${escapeHtml(ext.name)}</div>
        <button class="ext-card-toggle${ext.enabled ? ' on' : ''}" onclick="event.stopPropagation();toggleExtension('${ext.id}')"></button>
      </div>
      <div class="ext-card-desc">${escapeHtml(ext.description || '')}</div>
      <div class="ext-card-tools">
        ${(ext.tools || []).map(t => `<span class="ext-tool-badge">${escapeHtml(t)}</span>`).join('')}
      </div>
    `;
    list.appendChild(card);
  });
}

async function toggleExtension(extId) {
  try {
    const resp = await fetch(`/api/extensions/${extId}/toggle`, { method: 'POST' });
    const updated = await resp.json();
    const idx = state.extensions.findIndex(e => e.id === extId);
    if (idx >= 0) state.extensions[idx] = updated;
    renderExtensions();
    updateRpExtensions();
  } catch (e) {
    console.error('Failed to toggle extension:', e);
  }
}

function updateRpExtensions() {
  const active = state.extensions.filter(e => e.enabled);
  document.getElementById('rpExtCount').textContent = active.length;
  const el = document.getElementById('rpActiveExt');
  if (active.length === 0) {
    el.innerHTML = '<span style="color:var(--text-muted)">None</span>';
  } else {
    el.innerHTML = active.map(e => `<div style="padding:4px 0;font-size:13px;">${e.icon || '🧩'} ${escapeHtml(e.name)}</div>`).join('');
  }
}

// ── Recipes ──
async function loadRecipes() {
  try {
    const resp = await fetch('/api/recipes');
    state.recipes = await resp.json();
    renderRecipes();
  } catch (e) {
    console.error('Failed to load recipes:', e);
  }
}

function renderRecipes() {
  const list = document.getElementById('recipesList');
  if (!list) return;
  if (state.recipes.length === 0) {
    list.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted);"><div style="font-size:40px;margin-bottom:12px;">📋</div><div>No recipes yet.</div><div style="font-size:12px;margin-top:8px;">Create reusable AI workflows with custom parameters.</div></div>';
    return;
  }
  list.innerHTML = '';
  state.recipes.forEach(recipe => {
    const card = document.createElement('div');
    card.className = 'recipe-card';
    card.innerHTML = `
      <div class="recipe-card-name">${escapeHtml(recipe.name || 'Untitled')}</div>
      <div class="recipe-card-desc">${escapeHtml(recipe.description || '')}</div>
      <button class="recipe-run-btn" onclick="event.stopPropagation();openRecipeRunner('${escapeHtml(recipe._file || '')}')">▶ Run</button>
    `;
    list.appendChild(card);
  });
}

let _currentRecipe = null;
function openRecipeRunner(file) {
  const recipe = state.recipes.find(r => r._file === file);
  if (!recipe) return;
  _currentRecipe = recipe;
  const paramsDiv = document.getElementById('recipeRunParams');
  const params = (recipe.parameters || []);
  if (params.length === 0) {
    paramsDiv.innerHTML = '<p style="color:var(--text-secondary);font-size:14px;">This recipe has no parameters. Click Run to execute.</p>';
  } else {
    paramsDiv.innerHTML = params.map(p => {
      const name = typeof p === 'string' ? p : p.name;
      const desc = typeof p === 'object' ? p.description || '' : '';
      return `<label class="modal-label">${escapeHtml(name)}${desc ? ` - ${escapeHtml(desc)}` : ''}</label><input class="modal-input recipe-param" data-param="${escapeHtml(name)}" placeholder="Enter ${escapeHtml(name)}">`;
    }).join('');
  }
  openModal('recipeRunModal');
}

async function executeRecipe() {
  if (!_currentRecipe) return;
  const params = {};
  document.querySelectorAll('.recipe-param').forEach(input => {
    params[input.dataset.param] = input.value;
  });
  closeModal('recipeRunModal');

  // Switch to chat and show recipe execution
  switchView('chat');
  state.messages.push({ role: 'user', content: `[Recipe: ${_currentRecipe.name}]\n${JSON.stringify(params, null, 2)}` });
  renderMessages();

  state.isStreaming = true;
  updateSendButton();
  showTypingIndicator();

  try {
    const recipeId = _currentRecipe._file.replace(/\.(yaml|yml)$/, '');
    const resp = await fetch(`/api/recipes/${recipeId}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ params }),
    });
    hideTypingIndicator();
    const data = await resp.json();
    state.messages.push({ role: 'assistant', content: data.content || data.error || 'No response' });
  } catch (e) {
    hideTypingIndicator();
    state.messages.push({ role: 'assistant', content: `Error: ${e.message}` });
  }

  state.isStreaming = false;
  updateSendButton();
  renderMessages();
  saveCurrentSession();
}

function openRecipeCreator() { openModal('recipeModal'); }

async function createRecipe() {
  const name = document.getElementById('recipeName').value.trim();
  const desc = document.getElementById('recipeDesc').value.trim();
  const instructions = document.getElementById('recipeInstructions').value.trim();
  const paramsStr = document.getElementById('recipeParams').value.trim();

  if (!name || !instructions) return alert('Name and instructions are required');

  const params = paramsStr ? paramsStr.split(',').map(p => p.trim()).filter(Boolean) : [];
  const yaml = `name: "${name}"\ndescription: "${desc}"\nmodel: auto\nmax_tokens: 4096\nparameters:\n${params.map(p => `  - name: "${p}"\n    description: ""`).join('\n')}\ninstructions: |\n  ${instructions.replace(/\n/g, '\n  ')}`;

  // Save via a simple POST (we'd need a server endpoint for this; for now we'll just refresh)
  try {
    await fetch('/api/recipes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, content: yaml }),
    });
  } catch (e) { /* Recipe creation via API not implemented yet */ }

  closeModal('recipeModal');
  loadRecipes();
}

// ── Subagents ──
function openSubagentSpawner() { openModal('subagentModal'); }

async function spawnSubagent() {
  const task = document.getElementById('subagentTask').value.trim();
  const model = document.getElementById('subagentModel').value;
  if (!task) return;

  closeModal('subagentModal');
  try {
    const resp = await fetch('/api/subagents/spawn', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task, model }),
    });
    const agent = await resp.json();
    state.subagents.push(agent);
    renderSubagents();
    document.getElementById('subagentTask').value = '';
  } catch (e) {
    console.error('Failed to spawn subagent:', e);
  }
}

function renderSubagents() {
  const list = document.getElementById('subagentsList');
  if (!list) return;
  if (state.subagents.length === 0) {
    list.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted);"><div style="font-size:40px;margin-bottom:12px;">🤖</div><div>No subagents running.</div><div style="font-size:12px;margin-top:8px;">Spawn agents for parallel task execution.</div></div>';
    return;
  }
  list.innerHTML = '';
  state.subagents.forEach(agent => {
    const card = document.createElement('div');
    card.className = 'subagent-card';
    card.innerHTML = `
      <div class="subagent-header">
        <div class="subagent-status ${agent.status}"></div>
        <div style="font-size:13px;font-weight:600;">${agent.id}</div>
        <div style="font-size:11px;color:var(--text-muted);margin-left:auto;">${agent.status}</div>
      </div>
      <div class="subagent-task">${escapeHtml(agent.task)}</div>
      ${agent.result ? `<div class="subagent-result">${renderMarkdown(agent.result)}</div>` : ''}
    `;
    list.appendChild(card);
  });
}

async function updateSubagentsPoll() {
  const hasRunning = state.subagents.some(a => a.status === 'running');
  if (hasRunning) {
    try {
      const resp = await fetch('/api/subagents');
      state.subagents = await resp.json();
      renderSubagents();
    } catch (e) { /* ignore */ }
  }
  setTimeout(updateSubagentsPoll, 3000);
}

// ── File Upload ──
async function handleFileSelect(files) {
  for (const file of files) {
    const formData = new FormData();
    formData.append('file', file);
    try {
      const resp = await fetch('/api/upload', { method: 'POST', body: formData });
      const data = await resp.json();
      state.attachedFiles.push({ name: file.name, saved: data.saved_as, preview: data.preview });
      renderAttachments();
    } catch (e) {
      console.error('Upload failed:', e);
    }
  }
  document.getElementById('fileInput').value = '';
}

function renderAttachments() {
  const el = document.getElementById('chatAttachments');
  el.innerHTML = state.attachedFiles.map((f, i) => `
    <div class="chat-attachment-badge">
      <span>📄</span>
      <span>${escapeHtml(f.name)}</span>
      <span class="remove-attach" onclick="removeAttachment(${i})">✕</span>
    </div>
  `).join('');
}

function removeAttachment(idx) {
  state.attachedFiles.splice(idx, 1);
  renderAttachments();
}

// ── Views ──
function switchView(view) {
  ['chat', 'extensions', 'recipes', 'subagents'].forEach(v => {
    const el = document.getElementById(`view${v.charAt(0).toUpperCase() + v.slice(1)}`);
    if (el) el.classList.toggle('hidden', v !== view);
  });
  document.querySelectorAll('.sidebar-nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.view === view);
  });
  switchTab(view);
}

function switchTab(tab) {
  document.querySelectorAll('.tab-item').forEach(el => {
    el.classList.toggle('active', el.id === `tab${tab.charAt(0).toUpperCase() + tab.slice(1)}`);
  });
  switchView_internal(tab);
}

function switchView_internal(view) {
  ['chat', 'extensions', 'recipes', 'subagents'].forEach(v => {
    const el = document.getElementById(`view${v.charAt(0).toUpperCase() + v.slice(1)}`);
    if (el) el.classList.toggle('hidden', v !== view);
  });
}

// ── Right Panel ──
function toggleRightPanel() {
  document.getElementById('rightPanel').classList.toggle('collapsed');
}

function switchRpTab(tab) {
  document.querySelectorAll('.rp-tab').forEach(el => {
    el.classList.toggle('active', el.dataset.rptab === tab);
  });
  ['info', 'tools', 'files'].forEach(t => {
    const el = document.getElementById(`rp${t.charAt(0).toUpperCase() + t.slice(1)}`);
    if (el) el.classList.toggle('hidden', t !== tab);
  });
}

// ── Sidebar ──
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('collapsed');
}

// ── Modals ──
function openModal(id) { document.getElementById(id).classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }
function openSettings() { openModal('settingsModal'); }
function closeSettings() { closeModal('settingsModal'); }
function openModelPicker() { populateProviderSelects(); openModal('modelPickerModal'); }
function closeModelPicker() { closeModal('modelPickerModal'); }

function updateModelSetting() {
  const model = document.getElementById('settingsModel').value;
  selectModel(model);
}

async function saveSettings() {
  state.settings.max_tokens = parseInt(document.getElementById('settingsTokens').value);
  state.settings.temperature = parseFloat(document.getElementById('settingsTemp').value);
  try {
    await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(state.settings),
    });
  } catch (e) { /* ignore */ }
  closeSettings();
}

// ── Event Listeners ──
function setupEventListeners() {
  const input = document.getElementById('chatInput');

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!state.isStreaming && input.value.trim()) sendMessage();
    }
  });

  input.addEventListener('input', () => updateSendButton());

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'n') { e.preventDefault(); createSession(); }
    if (e.ctrlKey && e.key === 'b') { e.preventDefault(); toggleSidebar(); }
    if (e.key === 'Escape' && state.isStreaming) { stopGeneration(); }
  });

  // Drag & drop
  const body = document.body;
  body.addEventListener('dragover', (e) => { e.preventDefault(); document.getElementById('dropOverlay').classList.add('show'); });
  body.addEventListener('dragleave', (e) => { if (e.target === document.getElementById('dropOverlay')) document.getElementById('dropOverlay').classList.remove('show'); });
  body.addEventListener('drop', (e) => {
    e.preventDefault();
    document.getElementById('dropOverlay').classList.remove('show');
    if (e.dataTransfer.files.length) handleFileSelect(e.dataTransfer.files);
  });

  // Click outside modals
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.classList.add('hidden');
    });
  });
}

// ── Utilities ──
function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const diff = now - d;
  if (diff < 60000) return 'now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`;
  return `${d.getMonth() + 1}/${d.getDate()}`;
}
