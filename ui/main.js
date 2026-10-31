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

let searchEngine = "duckduckgo";
let isSplitView = false;

let tabs = [
  {
    id: 1,
    title: 'Crux Startpage',
    url: 'crux://startpage',
    history: ['crux://startpage'],
    historyIndex: 0,
    container: 'default',
    is_pinned: false,
    is_muted: false,
    is_active: true
  }
];

const elements = {
  tabsList: document.getElementById('tabsList'),
  btnNewTab: document.getElementById('btnNewTab'),
  btnToggleSidebar: document.getElementById('btnToggleSidebar'),
  sidebar: document.getElementById('sidebar'),
  urlInput: document.getElementById('urlInput'),
  webFrame: document.getElementById('webFrame'),
  webFrameSplit: document.getElementById('webFrameSplit'),
  webViewContainer: document.getElementById('webViewContainer'),
  progressBar: document.getElementById('progressBar'),
  commandPalette: document.getElementById('commandPalette'),
  paletteInput: document.getElementById('paletteInput'),
  paletteResults: document.getElementById('paletteResults'),
  btnCommandPalette: document.getElementById('btnCommandPalette'),
  btnSplitView: document.getElementById('btnSplitView'),
  btnReaderMode: document.getElementById('btnReaderMode'),
  readerOverlay: document.getElementById('readerOverlay'),
  btnCloseReader: document.getElementById('btnCloseReader'),
  readerTitle: document.getElementById('readerTitle'),
  readerContent: document.getElementById('readerContent'),
  btnMenu: document.getElementById('btnMenu'),
  appMenu: document.getElementById('appMenu'),
  settingsModal: document.getElementById('settingsModal'),
  btnCloseSettings: document.getElementById('btnCloseSettings'),
  btnSaveSettings: document.getElementById('btnSaveSettings'),
  btnBrowseDownload: document.getElementById('btnBrowseDownload'),
  searchEngineSelect: document.getElementById('searchEngineSelect'),
  adblockToggle: document.getElementById('adblockToggle'),
  txtDownloadDir: document.getElementById('txtDownloadDir'),
  txtAiApiKey: document.getElementById('txtAiApiKey'),
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
  btnReload: document.getElementById('btnReload'),
  btnWinMin: document.getElementById('btnWinMin'),
  btnWinMax: document.getElementById('btnWinMax'),
  btnWinClose: document.getElementById('btnWinClose'),
  dragRegion: document.getElementById('dragRegion'),
  toastNotification: document.getElementById('toastNotification')
};

// SVG Icon Helpers
const ICONS = {
  volume: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>`,
  volumeMuted: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>`,
  close: `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
  pin: `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a1 1 0 0 0 0-2H8a1 1 0 0 0 0 2h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"/></svg>`
};

function showToast(message) {
  if (!elements.toastNotification) return;
  elements.toastNotification.textContent = message;
  elements.toastNotification.classList.remove('hidden');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => {
    elements.toastNotification.classList.add('hidden');
  }, 2200);
}

function updateNavButtons() {
  const active = tabs.find(t => t.is_active);
  if (!active) return;
  if (elements.btnBack) {
    elements.btnBack.style.opacity = active.historyIndex > 0 ? "1" : "0.35";
    elements.btnBack.style.cursor = active.historyIndex > 0 ? "pointer" : "default";
  }
  if (elements.btnForward) {
    elements.btnForward.style.opacity = active.historyIndex < active.history.length - 1 ? "1" : "0.35";
    elements.btnForward.style.cursor = active.historyIndex < active.history.length - 1 ? "pointer" : "default";
  }
}

function loadTabContent(tab) {
  if (!tab || !elements.webFrame) return;
  if (tab.url === 'crux://startpage' || !tab.url || tab.url === 'about:blank') {
    elements.webFrame.removeAttribute('src');
    elements.webFrame.srcdoc = window.CRUX_STARTPAGE_HTML || '<!DOCTYPE html><html><body style="background:#18181b;color:#f5f5f0;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh;"><h1>Crux Startpage</h1></body></html>';
    if (elements.urlInput) elements.urlInput.value = '';
  } else {
    elements.webFrame.removeAttribute('srcdoc');
    elements.webFrame.src = tab.url;
    if (elements.urlInput) elements.urlInput.value = tab.url;
  }
}

function renderTabs() {
  if (!elements.tabsList) return;
  elements.tabsList.innerHTML = '';
  tabs.forEach(tab => {
    const el = document.createElement('div');
    el.className = `tab-item ${tab.is_active ? 'active' : ''}`;
    
    if (tab.is_pinned) {
      const pin = document.createElement('span');
      pin.className = 'tab-pin-badge';
      pin.innerHTML = ICONS.pin;
      pin.title = "Pinned Tab";
      el.appendChild(pin);
    }

    const title = document.createElement('span');
    title.className = 'tab-title';
    title.textContent = tab.title || (tab.url === 'crux://startpage' ? 'Crux Startpage' : 'New Tab');
    el.appendChild(title);

    // Audio Mute toggle button with SVG icons
    const muteBtn = document.createElement('button');
    muteBtn.className = `tab-mute ${tab.is_muted ? 'muted' : ''}`;
    muteBtn.innerHTML = tab.is_muted ? ICONS.volumeMuted : ICONS.volume;
    muteBtn.title = tab.is_muted ? 'Unmute Tab' : 'Mute Tab';
    muteBtn.onclick = (e) => {
      e.stopPropagation();
      tab.is_muted = !tab.is_muted;
      sendIpc('toggle_mute', { id: tab.id });
      renderTabs();
    };
    el.appendChild(muteBtn);

    if (!tab.is_pinned) {
      const close = document.createElement('button');
      close.className = 'tab-close';
      close.innerHTML = ICONS.close;
      close.title = "Close Tab";
      close.onclick = (e) => {
        e.stopPropagation();
        closeTab(tab.id);
      };
      el.appendChild(close);
    }

    el.onclick = () => activateTab(tab.id);
    elements.tabsList.appendChild(el);
  });
  updateNavButtons();
}

function activateTab(id) {
  tabs.forEach(t => t.is_active = (t.id === id));
  renderTabs();
  const current = tabs.find(t => t.id === id);
  if (current) {
    loadTabContent(current);
    updateNavButtons();
    sendIpc('activate_tab', { id });
  }
}

function navigateActiveTab(input) {
  const active = tabs.find(t => t.is_active);
  if (!active) return;

  let url = (input || "").trim();
  if (!url) {
    url = 'crux://startpage';
  } else if (!url.startsWith('http://') && !url.startsWith('https://') && !url.startsWith('crux://')) {
    if (url.includes('.') && !url.includes(' ')) {
      url = 'https://' + url;
    } else {
      url = getSearchUrl(url);
    }
  }

  active.url = url;
  if (url === 'crux://startpage') {
    active.title = 'Crux Startpage';
  } else {
    try {
      const u = new URL(url);
      active.title = u.hostname.replace(/^www\./, '');
    } catch {
      active.title = url;
    }
  }

  if (active.history[active.historyIndex] !== url) {
    active.history = active.history.slice(0, active.historyIndex + 1);
    active.history.push(url);
    active.historyIndex = active.history.length - 1;
  }

  loadTabContent(active);
  updateNavButtons();
  renderTabs();
  sendIpc('navigate', { url });
}

function createTab(url = 'crux://startpage') {
  const newId = (tabs.length ? Math.max(...tabs.map(t => t.id)) : 0) + 1;
  tabs.forEach(t => t.is_active = false);
  const tab = {
    id: newId,
    title: url === 'crux://startpage' ? 'Crux Startpage' : 'New Tab',
    url,
    history: [url],
    historyIndex: 0,
    container: 'default',
    is_pinned: false,
    is_muted: false,
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
    if (tabs.length === 0) {
      createTab('crux://startpage');
      return;
    }
    if (wasActive) {
      const nextIdx = Math.min(idx, tabs.length - 1);
      tabs[nextIdx].is_active = true;
      activateTab(tabs[nextIdx].id);
    } else {
      renderTabs();
    }
  }
}

// Search Engine Formatting
function getSearchUrl(query) {
  switch (searchEngine) {
    case 'google':
      return `https://www.google.com/search?q=${encodeURIComponent(query)}`;
    case 'searxng':
      return `https://searx.be/search?q=${encodeURIComponent(query)}`;
    case 'brave':
      return `https://search.brave.com/search?q=${encodeURIComponent(query)}`;
    default:
      return `https://duckduckgo.com/?q=${encodeURIComponent(query)}`;
  }
}

// Listen to messages from startpage iframe
window.addEventListener('message', (e) => {
  if (e.data && e.data.type === 'navigate' && e.data.url) {
    navigateActiveTab(e.data.url);
  }
});

// Navigation Buttons Handlers
if (elements.btnBack) {
  elements.btnBack.addEventListener('click', () => {
    const active = tabs.find(t => t.is_active);
    if (active && active.historyIndex > 0) {
      active.historyIndex--;
      const targetUrl = active.history[active.historyIndex];
      active.url = targetUrl;
      loadTabContent(active);
      updateNavButtons();
      renderTabs();
      sendIpc('navigate', { url: targetUrl });
    }
  });
}

if (elements.btnForward) {
  elements.btnForward.addEventListener('click', () => {
    const active = tabs.find(t => t.is_active);
    if (active && active.historyIndex < active.history.length - 1) {
      active.historyIndex++;
      const targetUrl = active.history[active.historyIndex];
      active.url = targetUrl;
      loadTabContent(active);
      updateNavButtons();
      renderTabs();
      sendIpc('navigate', { url: targetUrl });
    }
  });
}

if (elements.btnReload) {
  elements.btnReload.addEventListener('click', () => {
    const active = tabs.find(t => t.is_active);
    if (active && elements.webFrame) {
      loadTabContent(active);
      showToast("Reloading page...");
    }
  });
}

if (elements.btnNewTab) elements.btnNewTab.addEventListener('click', () => createTab('crux://startpage'));
if (elements.btnToggleSidebar) {
  elements.btnToggleSidebar.addEventListener('click', () => elements.sidebar.classList.toggle('compact'));
}

if (elements.urlInput) {
  elements.urlInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      navigateActiveTab(elements.urlInput.value);
    }
  });
}

// Top Bar Bookmark Button
if (elements.btnBookmark) {
  elements.btnBookmark.addEventListener('click', () => {
    const active = tabs.find(t => t.is_active);
    if (active) {
      sendIpc('add_bookmark', { url: active.url, title: active.title });
      showToast(`★ Bookmarked: ${active.title || active.url}`);
    }
  });
}

// Split View
function toggleSplitView() {
  isSplitView = !isSplitView;
  if (isSplitView) {
    elements.webViewContainer.classList.add('split-mode');
    elements.webFrameSplit.classList.remove('hidden');
    elements.webFrameSplit.src = 'https://duckduckgo.com';
    elements.btnSplitView.classList.add('active');
    showToast("Split view enabled");
  } else {
    elements.webViewContainer.classList.remove('split-mode');
    elements.webFrameSplit.classList.add('hidden');
    elements.btnSplitView.classList.remove('active');
    showToast("Split view disabled");
  }
}

if (elements.btnSplitView) elements.btnSplitView.addEventListener('click', toggleSplitView);

// Reader Mode
function toggleReaderMode() {
  if (!elements.readerOverlay) return;
  const isHidden = elements.readerOverlay.classList.contains('hidden');
  if (isHidden) {
    const active = tabs.find(t => t.is_active);
    const url = active ? active.url : "";
    elements.readerTitle.textContent = active ? (active.title || active.url) : 'Reading Mode';
    elements.readerContent.innerHTML = `
      <h2 style="font-size: 24px; margin-bottom: 8px;">${active ? (active.title || 'Reader View') : 'Article'}</h2>
      <p style="color: var(--text-muted); font-size: 12px; margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 12px;">Source: ${url}</p>
      <div style="font-size: 16px; line-height: 1.8; color: #f5f5f0;">
        Distraction-free reading view enabled for Crux 2.0. Clean typography eliminates banners, popups, and intrusive telemetry for focused article consumption.
      </div>
    `;
    elements.readerOverlay.classList.remove('hidden');
  } else {
    elements.readerOverlay.classList.add('hidden');
  }
}

if (elements.btnReaderMode) elements.btnReaderMode.addEventListener('click', toggleReaderMode);
if (elements.btnCloseReader) elements.btnCloseReader.addEventListener('click', () => elements.readerOverlay.classList.add('hidden'));

// Settings Modal
function toggleSettingsModal() {
  if (!elements.settingsModal) return;
  const isHidden = elements.settingsModal.classList.contains('hidden');
  if (isHidden) {
    sendIpc('get_settings');
    elements.settingsModal.classList.remove('hidden');
  } else {
    elements.settingsModal.classList.add('hidden');
  }
}

if (elements.btnCloseSettings) elements.btnCloseSettings.addEventListener('click', toggleSettingsModal);

if (elements.btnBrowseDownload) {
  elements.btnBrowseDownload.addEventListener('click', () => {
    sendIpc('choose_download_dir');
  });
}

if (elements.btnSaveSettings) {
  elements.btnSaveSettings.addEventListener('click', () => {
    if (elements.searchEngineSelect) {
      searchEngine = elements.searchEngineSelect.value;
      sendIpc('save_setting', { key: 'search_engine', value: searchEngine });
    }
    if (elements.adblockToggle) {
      sendIpc('save_setting', { key: 'adblock_enabled', value: elements.adblockToggle.checked ? 'true' : 'false' });
    }
    if (elements.txtAiApiKey && elements.txtAiApiKey.value) {
      sendIpc('save_setting', { key: 'ai_api_key', value: elements.txtAiApiKey.value.trim() });
    }
    toggleSettingsModal();
    showToast("Settings saved to SQLite");
  });
}

// App Dropdown Menu (Anchored to Top Right)
function toggleAppMenu() {
  if (!elements.appMenu) return;
  elements.appMenu.classList.toggle('hidden');
}

function closeAppMenu() {
  if (elements.appMenu && !elements.appMenu.classList.contains('hidden')) {
    elements.appMenu.classList.add('hidden');
  }
}

if (elements.btnMenu) {
  elements.btnMenu.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleAppMenu();
  });
}

// Menu Items Click Handlers
const menuActions = {
  menuNewTab: () => createTab('crux://startpage'),
  menuSplit: toggleSplitView,
  menuReader: toggleReaderMode,
  menuPalette: () => toggleCommandPalette(),
  menuDevTools: () => showToast("Developer Tools toggled (F12)"),
  menuDownloads: () => sendIpc('choose_download_dir'),
  menuHistory: () => sendIpc('get_history'),
  menuBookmarks: () => sendIpc('get_bookmarks'),
  menuAi: () => toggleAiPanel(),
  menuAdBlock: () => showToast("Shield: AdBlocker is active"),
  menuSettings: () => toggleSettingsModal()
};

Object.entries(menuActions).forEach(([id, action]) => {
  const el = document.getElementById(id);
  if (el) {
    el.addEventListener('click', () => {
      closeAppMenu();
      action();
    });
  }
});

document.addEventListener('click', (e) => {
  if (elements.appMenu && !elements.appMenu.contains(e.target) && e.target !== elements.btnMenu && !elements.btnMenu.contains(e.target)) {
    closeAppMenu();
  }
});

// Window Controls (Frameless Top Bar)
if (elements.btnWinMin) elements.btnWinMin.addEventListener('click', () => sendIpc('window_minimize'));
if (elements.btnWinMax) elements.btnWinMax.addEventListener('click', () => sendIpc('window_maximize'));
if (elements.btnWinClose) elements.btnWinClose.addEventListener('click', () => sendIpc('window_close'));

if (elements.dragRegion) {
  elements.dragRegion.addEventListener('mousedown', (e) => {
    if (e.button === 0 && (e.target === elements.dragRegion || e.target.classList.contains('url-bar-container'))) {
      if (e.target.id !== 'urlInput') {
        sendIpc('window_drag');
      }
    }
  });
  elements.dragRegion.addEventListener('dblclick', (e) => {
    if (e.target === elements.dragRegion) {
      sendIpc('window_maximize');
    }
  });
}

// Crux AI Panel Logic
function toggleAiPanel() {
  if (!elements.aiPanel) return;
  elements.aiPanel.classList.toggle('hidden');
}

if (elements.btnToggleAi) elements.btnToggleAi.addEventListener('click', toggleAiPanel);
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
      prompt: `Please summarize the key points of webpage: ${url}`,
      provider: "ollama",
      model: "llama3"
    });
  });
}

if (elements.btnAiExplain) {
  elements.btnAiExplain.addEventListener('click', () => {
    const active = tabs.find(t => t.is_active);
    const url = active ? active.url : "";
    appendAiMessage("user", `Explain concepts on: ${url}`);
    sendIpc('ask_ai', {
      prompt: `Explain the technical concepts and topic covered by: ${url}`,
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
  { name: 'New Tab', action: () => createTab('crux://startpage') },
  { name: 'Toggle Compact Sidebar', action: () => elements.sidebar.classList.toggle('compact') },
  { name: 'Toggle Split View (Side-by-side)', action: toggleSplitView },
  { name: 'Toggle Reading Mode', action: toggleReaderMode },
  { name: 'Open Settings', action: toggleSettingsModal },
  { name: 'Toggle Crux AI Panel', action: toggleAiPanel },
  { name: 'Bookmark Current Page', action: () => elements.btnBookmark && elements.btnBookmark.click() },
  { name: 'Show SQLite Bookmarks', action: () => sendIpc('get_bookmarks') },
  { name: 'Show SQLite History', action: () => sendIpc('get_history') },
  { name: 'Choose Default Download Directory (Rust RFD)', action: () => sendIpc('choose_download_dir') },
  { name: 'Pin / Unpin Current Tab', action: () => {
    const active = tabs.find(t => t.is_active);
    if (active) {
      active.is_pinned = !active.is_pinned;
      renderTabs();
      sendIpc('toggle_pin', { id: active.id });
    }
  }},
  { name: 'Clear SQLite History', action: () => {
    sendIpc('clear_history');
    showToast("History cleared");
  }}
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
  } else if (e.ctrlKey && e.key.toLowerCase() === 't') {
    e.preventDefault();
    createTab('crux://startpage');
  } else if (e.ctrlKey && e.key.toLowerCase() === 'w') {
    e.preventDefault();
    const active = tabs.find(t => t.is_active);
    if (active) closeTab(active.id);
  } else if (e.key === 'Escape') {
    closeAppMenu();
    if (elements.commandPalette && !elements.commandPalette.classList.contains('hidden')) {
      elements.commandPalette.classList.add('hidden');
    }
    if (elements.settingsModal && !elements.settingsModal.classList.contains('hidden')) {
      elements.settingsModal.classList.add('hidden');
    }
    if (elements.readerOverlay && !elements.readerOverlay.classList.contains('hidden')) {
      elements.readerOverlay.classList.add('hidden');
    }
  }
});

// Window Callbacks from Rust Event Loop
window.onAiResponse = function(text, success) {
  appendAiMessage("assistant", text);
};

window.onBookmarksLoaded = function(bookmarks) {
  if (!bookmarks || !bookmarks.length) {
    showToast("No bookmarks saved in SQLite yet");
    return;
  }
  const lines = bookmarks.map(b => `• ${b.title || b.url} (${b.url})`);
  appendAiMessage("system", `Saved Bookmarks (${bookmarks.length}):\n` + lines.join("\n"));
  if (elements.aiPanel && elements.aiPanel.classList.contains('hidden')) {
    toggleAiPanel();
  }
};

window.onHistoryLoaded = function(history) {
  if (!history || !history.length) {
    showToast("History is empty");
    return;
  }
  const lines = history.slice(0, 10).map(h => `• ${h.title || h.url} [${h.visited_at}]`);
  appendAiMessage("system", `Recent SQLite History (${history.length}):\n` + lines.join("\n"));
  if (elements.aiPanel && elements.aiPanel.classList.contains('hidden')) {
    toggleAiPanel();
  }
};

window.onSettingsLoaded = function(settings) {
  if (!settings) return;
  if (elements.searchEngineSelect && settings.search_engine) {
    elements.searchEngineSelect.value = settings.search_engine;
    searchEngine = settings.search_engine;
  }
  if (elements.adblockToggle && settings.adblock_enabled !== undefined) {
    elements.adblockToggle.checked = settings.adblock_enabled !== 'false';
  }
  if (elements.txtDownloadDir && settings.download_dir) {
    elements.txtDownloadDir.value = settings.download_dir;
  }
  if (elements.txtAiApiKey && settings.ai_api_key) {
    elements.txtAiApiKey.value = settings.ai_api_key;
  }
};

window.onDownloadDirSelected = function(path) {
  if (elements.txtDownloadDir) {
    elements.txtDownloadDir.value = path;
  }
  showToast(`Download folder set to: ${path}`);
};

// Initial Render
renderTabs();
const initialTab = tabs.find(t => t.is_active);
if (initialTab) {
  loadTabContent(initialTab);
}
console.log("Crux 2.0 Rust Architecture initialized with original startpage.");
