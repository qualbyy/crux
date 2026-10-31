// Crux 2.0 — Frontend Controller

const isTauri = window.__TAURI__ !== undefined;

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
  btnCommandPalette: document.getElementById('btnCommandPalette')
};

function renderTabs() {
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
    elements.urlInput.value = current.url;
    elements.webFrame.src = current.url;
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
}

function closeTab(id) {
  const idx = tabs.findIndex(t => t.id === id);
  if (idx !== -1) {
    const wasActive = tabs[idx].is_active;
    tabs.splice(idx, 1);
    if (wasActive && tabs.length > 0) {
      const nextIdx = Math.min(idx, tabs.length - 1);
      tabs[nextIdx].is_active = true;
      activateTab(tabs[nextIdx].id);
    } else {
      renderTabs();
    }
  }
}

// Event Listeners
elements.btnNewTab.addEventListener('click', () => createTab());

elements.btnToggleSidebar.addEventListener('click', () => {
  elements.sidebar.classList.toggle('compact');
});

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
      elements.webFrame.src = input;
    }
  }
});

// Command Palette (Ctrl+Shift+P)
function toggleCommandPalette() {
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
  { name: 'Clear History', action: () => alert('History cleared') },
  { name: 'Open Settings', action: () => createTab('crux://settings') },
  { name: 'Pin / Unpin Current Tab', action: () => {
    const active = tabs.find(t => t.is_active);
    if (active) {
      active.is_pinned = !active.is_pinned;
      renderTabs();
    }
  }}
];

function renderCommands(query) {
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

elements.paletteInput.addEventListener('input', (e) => {
  renderCommands(e.target.value);
});

elements.btnCommandPalette.addEventListener('click', toggleCommandPalette);

window.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'p') {
    e.preventDefault();
    toggleCommandPalette();
  } else if (e.key === 'Escape' && !elements.commandPalette.classList.contains('hidden')) {
    elements.commandPalette.classList.add('hidden');
  }
});

// Initial Render
renderTabs();
