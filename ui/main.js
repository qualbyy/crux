// Crux 2.0 — Frontend Controller with Rust IPC & AI Engine

function sendIpc(cmd, data = {}) {
  try {
    if (window.ipc && window.ipc.postMessage) {
      window.ipc.postMessage(JSON.stringify({ cmd, ...data }));
    }
  } catch (err) {
    console.warn("IPC send failed:", err);
  }
}

let tabs = [
  { id: 1, title: 'Crux Startpage', url: 'https://duckduckgo.com', container: 'default', is_pinned: false, is_active: true }
];

const elements = {
  tabsList: document.getElementById('tabsList'),
  btnNewTab: document.getElementById('btnNewTab'),
  btnToggleSidebar: document.getElementById('btnToggleSidebar'),
  sidebar: document.getElementById('sidebar'),
  urlInput: document.getElementById('urlInput'),
  webFrame: document.getElementById('webFrame'),
  progressBar: document.getElementById('progressBar'),
  commandPalette: document.getElementById('commandPalette'),
  paletteInput: document.getElementById('paletteInput'),
  paletteResults: document.getElementById('paletteResults'),
  btnCommandPalette: document.getElementById('btnCommandPalette'),
  btnAiSidebar: document.getElementById('btnAiSidebar'),
  btnBookmark: document.getElementById('btnBookmark'),
  btnToggleAi: document.getElementById('btnToggleAi'),
  aiPanel: document.getElementById('aiPanel'),
  btnCloseAi: document.getElementById('btnCloseAi'),
  aiModelSelect: document.getElementById('aiModelSelect'),
  aiChatHistory: document.getElementById('aiChatHistory'),
  aiInput: document.getElementById('aiInput'),
  btnAiSend: document.getElementById('btnAiSend'),
  btnAiSummarize: document.getElementById('btnAiSummarize'),
  btnAiExplain: document.getElementById('btnAiExplain'),
  btnBack: document.getElementById('btnBack'),
  btnForward: document.getElementById('btnForward'),
  btnReload: document.getElementById('btnReload')
};

function renderTabs() {
  if (!elements.tabsList) return;
  elements.tabsList.innerHTML = '';
  tabs.forEach(tab => {
    const el = document.createElement('div');
    el.className = `tab-item ${tab.is_active ? 'active' : ''}`;
    
    if (tab.is_pinned) {
      const pin = document.createElement('span');
      pin.className = 'tab-pin-badge';
      pin.textContent = 'PIN';
      el.appendChild(pin);
    }

    const title = document.createElement('span');
    title.className = 'tab-title';
    title.textContent = tab.title || 'New Tab';
    el.appendChild(title);

    if (!tab.is_pinned) {
      const close = document.createElement('button');
      close.className = 'tab-close';
      close.innerHTML = '&times;';
      close.onclick = (e) => {
        e.stopPropagation();
        closeTab(tab.id);
      };
      el.appendChild(close);
    }

    el.onclick = () => activateTab(tab.id);
    elements.tabsList.appendChild(el);
  });
}

function activateTab(id) {
  tabs.forEach(t => t.is_active = (t.id === id));
  renderTabs();
  const current = tabs.find(t => t.id === id);
  if (current) {
    if (elements.urlInput) elements.urlInput.value = current.url;
    if (elements.webFrame) elements.webFrame.src = current.url;
    sendIpc('activate_tab', { id });
  }
}

function createTab(url = 'https://duckduckgo.com') {
  const newId = (tabs.length ? Math.max(...tabs.map(t => t.id)) : 0) + 1;
  tabs.forEach(t => t.is_active = false);
  const tab = {
    id: newId,
    title: 'New Tab',
    url,
    container: 'default',
    is_pinned: false,
    is_active: true
  };
  tabs.push(tab);
  renderTabs();
  activateTab(newId);
  sendIpc('create_tab', { url, container: 'default' });
}

function closeTab(id) {
  const idx = tabs.findIndex(t => t.id === id);
  if (idx !== -1) {
    const wasActive = tabs[idx].is_active;
    tabs.splice(idx, 1);
    sendIpc('close_tab', { id });
    if (wasActive && tabs.length > 0) {
      const nextIdx = Math.min(idx, tabs.length - 1);
      tabs[nextIdx].is_active = true;
      activateTab(tabs[nextIdx].id);
    } else {
      renderTabs();
    }
  }
}

// Navigation Events
if (elements.btnNewTab) elements.btnNewTab.addEventListener('click', () => createTab());
if (elements.btnToggleSidebar) {
  elements.btnToggleSidebar.addEventListener('click', () => elements.sidebar.classList.toggle('compact'));
}

if (elements.urlInput) {
  elements.urlInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      let input = elements.urlInput.value.trim();
      if (!input.startsWith('http://') && !input.startsWith('https://') && !input.startsWith('crux://')) {
        if (input.includes('.') && !input.includes(' ')) {
          input = 'https://' + input;
        } else {
          input = 'https://duckduckgo.com/?q=' + encodeURIComponent(input);
        }
      }
      const active = tabs.find(t => t.is_active);
      if (active) {
        active.url = input;
        if (elements.webFrame) elements.webFrame.src = input;
        sendIpc('navigate', { url: input });
      }
    }
  });
}

if (elements.btnReload) {
  elements.btnReload.addEventListener('click', () => {
    if (elements.webFrame) elements.webFrame.src = elements.webFrame.src;
  });
}

if (elements.btnBookmark) {
  elements.btnBookmark.addEventListener('click', () => {
    const active = tabs.find(t => t.is_active);
    if (active) {
      sendIpc('add_bookmark', { url: active.url, title: active.title });
      appendAiMessage("system", `Bookmarked: ${active.url}`);
    }
  });
}

// Crux AI Panel Logic
function toggleAiPanel() {
  if (!elements.aiPanel) return;
  elements.aiPanel.classList.toggle('hidden');
}

if (elements.btnToggleAi) elements.btnToggleAi.addEventListener('click', toggleAiPanel);
if (elements.btnAiSidebar) elements.btnAiSidebar.addEventListener('click', toggleAiPanel);
if (elements.btnCloseAi) elements.btnCloseAi.addEventListener('click', toggleAiPanel);

function appendAiMessage(role, text) {
  if (!elements.aiChatHistory) return;
  const msg = document.createElement('div');
  msg.className = `ai-msg ${role}`;
  msg.textContent = text;
  elements.aiChatHistory.appendChild(msg);
  elements.aiChatHistory.scrollTop = elements.aiChatHistory.scrollHeight;
}

function handleAiSend() {
  const text = elements.aiInput ? elements.aiInput.value.trim() : "";
  if (!text) return;
  elements.aiInput.value = "";
  appendAiMessage("user", text);

  const model = elements.aiModelSelect ? elements.aiModelSelect.value : "llama3";
  const provider = model.includes("gpt") ? "openai" : (model.includes("deepseek-chat") ? "deepseek" : "ollama");

  appendAiMessage("assistant", `Crux AI (${model}): Processing request...`);
  sendIpc('ask_ai', { prompt: text, provider, model });
}

if (elements.btnAiSend) elements.btnAiSend.addEventListener('click', handleAiSend);
if (elements.aiInput) {
  elements.aiInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleAiSend();
  });
}

if (elements.btnAiSummarize) {
  elements.btnAiSummarize.addEventListener('click', () => {
    const active = tabs.find(t => t.is_active);
    const url = active ? active.url : "";
    appendAiMessage("user", `Summarize page: ${url}`);
    sendIpc('ask_ai', {
      prompt: `Please summarize the purpose and key points of webpage: ${url}`,
      provider: "ollama",
      model: "llama3"
    });
  });
}

// Command Palette (Ctrl+Shift+P)
function toggleCommandPalette() {
  if (!elements.commandPalette) return;
  elements.commandPalette.classList.toggle('hidden');
  if (!elements.commandPalette.classList.contains('hidden')) {
    elements.paletteInput.value = '';
    elements.paletteInput.focus();
    renderCommands('');
  }
}

const commands = [
  { name: 'New Tab', action: () => createTab() },
  { name: 'Toggle Compact Sidebar', action: () => elements.sidebar.classList.toggle('compact') },
  { name: 'Toggle Crux AI Panel', action: toggleAiPanel },
  { name: 'Bookmark Current Page', action: () => elements.btnBookmark && elements.btnBookmark.click() },
  { name: 'Choose Default Download Directory (Rust RFD)', action: () => sendIpc('choose_download_dir') },
  { name: 'Pin / Unpin Current Tab', action: () => {
    const active = tabs.find(t => t.is_active);
    if (active) {
      active.is_pinned = !active.is_pinned;
      renderTabs();
      sendIpc('toggle_pin', { id: active.id });
    }
  }},
  { name: 'Clear SQLite History', action: () => sendIpc('clear_history') }
];

function renderCommands(query) {
  if (!elements.paletteResults) return;
  elements.paletteResults.innerHTML = '';
  const filtered = commands.filter(c => c.name.toLowerCase().includes(query.toLowerCase()));
  filtered.forEach(cmd => {
    const li = document.createElement('li');
    li.className = 'palette-item';
    li.textContent = cmd.name;
    li.onclick = () => {
      cmd.action();
      elements.commandPalette.classList.add('hidden');
    };
    elements.paletteResults.appendChild(li);
  });
}

if (elements.paletteInput) {
  elements.paletteInput.addEventListener('input', (e) => {
    renderCommands(e.target.value);
  });
}

if (elements.btnCommandPalette) {
  elements.btnCommandPalette.addEventListener('click', toggleCommandPalette);
}

window.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'p') {
    e.preventDefault();
    toggleCommandPalette();
  } else if (e.key === 'Escape' && elements.commandPalette && !elements.commandPalette.classList.contains('hidden')) {
    elements.commandPalette.classList.add('hidden');
  }
});

// Initial Render
renderTabs();
console.log("Crux 2.0 Rust Architecture initialized.");
