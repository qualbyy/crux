// Crux 2.0 — Frontend Controller with Rust IPC & AI Engine (Full Original Parity)

function sendIpc(cmd, data = {}) {
  try {
    if (window.ipc && window.ipc.postMessage) {
      window.ipc.postMessage(JSON.stringify({ cmd, ...data }));
    }
  } catch (err) {
    console.warn("IPC send failed:", err);
  }
}

// Global Browser State
let currentLanguage = "ru";
let currentTheme = "dark";
let tabOrientation = "vertical"; // 'vertical' | 'horizontal'
let uiMode = "minimal"; // 'minimal' | 'vim'
let searchEngine = "duckduckgo";
let currentAccent = "#a855f7";
let currentZoom = 1.0;
let isMobileMode = false;
let mobileWidth = 390;
let mobileHeight = 844;
let closedTabsStack = [];
let currentSettings = {};
let currentBookmarks = [];
let currentDownloads = [];
let currentHistory = [];

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
    is_playing_audio: false,
    is_split: false,
    split_url: 'crux://startpage',
    hide_split_url: false,
    is_active: true
  }
];

// Complete Canonical RU & EN Localization Dictionaries
const I18N = {
  ru: {
    zoom_label: "Масштаб:",
    mobile_mode: "Мобильный режим:",
    reader_mode: "Режим чтения",
    pip_mode: "Картинка в картинке / PiP",
    tab_layout: "Расположение вкладок",
    tab_vertical: "Вертикальные вкладки",
    tab_horizontal: "Горизонтальные вкладки",
    ui_mode: "Режим интерфейса",
    ui_minimal: "Минималистичный",
    ui_vim: "Vim-режим",
    new_tab: "Новая вкладка",
    reopen_closed: "Восстановить закрытую вкладку",
    container_tab: "Вкладка в контейнере",
    container_personal: "[ЛИЧНЫЙ] Личный",
    container_work: "[РАБОТА] Работа",
    container_banking: "[БАНКИНГ] Банкинг",
    container_shopping: "[ПОКУПКИ] Покупки",
    new_window: "Новое окно",
    incognito_window: "Новое окно инкогнито",
    find_in_page: "Поиск на странице",
    split_view: "Разделить экран",
    devtools: "Инструменты разработчика",
    downloads: "Загрузки",
    history: "История",
    bookmarks: "Закладки",
    ai_assistant: "AI-ассистент",
    adblock: "Блокировщик рекламы",
    settings: "Настройки браузера",
    vim_status: "[VIM-РЕЖИМ] Нажмите Esc для выхода | j/k: скролл, r: обновить, t: новая вкладка, x: закрыть",
    exit_vim: "ВЫЙТИ ИЗ VIM",
    split_placeholder: "Адрес или поиск во втором окне...",
    hide_url_bar: "Скрыть строку адреса",
    show_url_bar: "Показать строку адреса",
    downloads_title: "ЗАГРУЗКИ",
    bookmarks_title: "ЗАКЛАДКИ",
    all_downloads: "ВСЕ ЗАГРУЗКИ (crux://downloads)",
    all_bookmarks: "ВСЕ ЗАКЛАДКИ",
    open_folder: "ОТКРЫТЬ ПАПКУ",
    add_bookmark: "+ ДОБАВИТЬ СТРАНИЦУ",
    new_tab_btn: "НОВАЯ ВКЛАДКА",
    bookmarks_btn: "ЗАКЛАДКИ",
    downloads_btn: "ЗАГРУЗКИ",
    split_btn: "РАЗДЕЛИТЬ",
    reader_btn: "ЧТЕНИЕ",
    ai_btn: "ИИ",
    cmd_btn: "КОМАНДЫ",
    url_placeholder: "Поиск в DuckDuckGo или введите адрес...",
    find_placeholder: "Поиск на странице...",
    ctx_pin: "Закрепить вкладку",
    ctx_unpin: "Открепить вкладку",
    ctx_mute: "Отключить звук",
    ctx_unmute: "Включить звук",
    ctx_duplicate: "Дублировать вкладку",
    ctx_split: "Разделить экран",
    ctx_snooze: "Приостановить вкладку",
    ctx_close: "Закрыть вкладку"
  },
  en: {
    zoom_label: "Zoom:",
    mobile_mode: "Mobile Viewport:",
    reader_mode: "Reading Mode",
    pip_mode: "Picture in Picture / PiP",
    tab_layout: "Tab Layout",
    tab_vertical: "Vertical Tabs",
    tab_horizontal: "Horizontal Tabs",
    ui_mode: "UI Mode",
    ui_minimal: "Minimalist",
    ui_vim: "Vim Mode",
    new_tab: "New Tab",
    reopen_closed: "Reopen Closed Tab",
    container_tab: "New Tab in Container",
    container_personal: "[PERSONAL] Personal",
    container_work: "[WORK] Work",
    container_banking: "[BANKING] Banking",
    container_shopping: "[SHOPPING] Shopping",
    new_window: "New Window",
    incognito_window: "New Incognito Window",
    find_in_page: "Find in Page",
    split_view: "Split View",
    devtools: "Developer Tools",
    downloads: "Downloads",
    history: "History",
    bookmarks: "Bookmarks",
    ai_assistant: "AI Assistant",
    adblock: "Ad & Tracker Shield",
    settings: "Browser Settings",
    vim_status: "[VIM MODE] Press Esc to exit | j/k: scroll, r: reload, t: new tab, x: close",
    exit_vim: "EXIT VIM",
    split_placeholder: "Search or address in split pane...",
    hide_url_bar: "Hide Address Bar",
    show_url_bar: "Show Address Bar",
    downloads_title: "DOWNLOADS",
    bookmarks_title: "BOOKMARKS",
    all_downloads: "ALL DOWNLOADS (crux://downloads)",
    all_bookmarks: "ALL BOOKMARKS",
    open_folder: "OPEN FOLDER",
    add_bookmark: "+ ADD CURRENT PAGE",
    new_tab_btn: "NEW TAB",
    bookmarks_btn: "BOOKMARKS",
    downloads_btn: "DOWNLOADS",
    split_btn: "SPLIT",
    reader_btn: "READ",
    ai_btn: "AI",
    cmd_btn: "CMD",
    url_placeholder: "Search DuckDuckGo or enter address...",
    find_placeholder: "Find in page...",
    ctx_pin: "Pin Tab",
    ctx_unpin: "Unpin Tab",
    ctx_mute: "Mute Tab",
    ctx_unmute: "Unmute Tab",
    ctx_duplicate: "Duplicate Tab",
    ctx_split: "Split View",
    ctx_snooze: "Snooze Tab",
    ctx_close: "Close Tab"
  }
};

const elements = {
  tabsList: document.getElementById('tabsList'),
  btnNewTab: document.getElementById('btnNewTab'),
  btnToggleSidebar: document.getElementById('btnToggleSidebar'),
  sidebar: document.getElementById('sidebar'),
  urlInput: document.getElementById('urlInput'),
  webFrame: document.getElementById('webFrame'),
  splitPaneWrapper: document.getElementById('splitPaneWrapper'),
  urlInputSplit: document.getElementById('urlInputSplit'),
  splitToolbar: document.getElementById('splitToolbar'),
  btnToggleSplitUrl: document.getElementById('btnToggleSplitUrl'),
  btnFloatingShowSplitUrl: document.getElementById('btnFloatingShowSplitUrl'),
  btnCloseSplit: document.getElementById('btnCloseSplit'),
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
  btnBookmark: document.getElementById('btnBookmark'),
  bookmarksPopup: document.getElementById('bookmarksPopup'),
  bookmarksListPopup: document.getElementById('bookmarksListPopup'),
  btnAddCurrentBookmark: document.getElementById('btnAddCurrentBookmark'),
  btnDownloads: document.getElementById('btnDownloads'),
  downloadsPopup: document.getElementById('downloadsPopup'),
  downloadsListPopup: document.getElementById('downloadsListPopup'),
  btnOpenDownloadsFolder: document.getElementById('btnOpenDownloadsFolder'),
  btnViewAllDownloads: document.getElementById('btnViewAllDownloads'),
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
  toastNotification: document.getElementById('toastNotification'),
  // Zoom Elements
  btnZoomOut: document.getElementById('btnZoomOut'),
  btnZoomIn: document.getElementById('btnZoomIn'),
  btnZoomReset: document.getElementById('btnZoomReset'),
  btnFullscreen: document.getElementById('btnFullscreen'),
  zoomLevelLbl: document.getElementById('zoomLevelLbl'),
  // Mobile Viewport Elements
  menuMobileMode: document.getElementById('menuMobileMode'),
  lblMobileStatus: document.getElementById('lblMobileStatus'),
  viewportBar: document.getElementById('viewportBar'),
  vpPresetSelect: document.getElementById('vpPresetSelect'),
  vpWidthInput: document.getElementById('vpWidthInput'),
  vpHeightInput: document.getElementById('vpHeightInput'),
  btnVpRotate: document.getElementById('btnVpRotate'),
  btnVpClose: document.getElementById('btnVpClose'),
  // Horizontal Tab Bar Elements
  horizontalTabBar: document.getElementById('horizontalTabBar'),
  horizontalTabsList: document.getElementById('horizontalTabsList'),
  btnNewTabHoriz: document.getElementById('btnNewTabHoriz'),
  // Vim Mode Elements
  vimStatusBar: document.getElementById('vimStatusBar'),
  vimStatusText: document.getElementById('vimStatusText'),
  btnExitVim: document.getElementById('btnExitVim'),
  // Submenu Checkbox Elements
  optTabVert: document.getElementById('optTabVert'),
  optTabHoriz: document.getElementById('optTabHoriz'),
  chkTabVert: document.getElementById('chkTabVert'),
  chkTabHoriz: document.getElementById('chkTabHoriz'),
  optUiMinimal: document.getElementById('optUiMinimal'),
  optUiVim: document.getElementById('optUiVim'),
  chkUiMinimal: document.getElementById('chkUiMinimal'),
  chkUiVim: document.getElementById('chkUiVim'),
  optContainerPersonal: document.getElementById('optContainerPersonal'),
  optContainerWork: document.getElementById('optContainerWork'),
  optContainerBanking: document.getElementById('optContainerBanking'),
  optContainerShopping: document.getElementById('optContainerShopping'),
  // Backdrop & Resizer
  popupBackdrop: document.getElementById('popupBackdrop'),
  sidebarResizer: document.getElementById('sidebarResizer'),
  // Find in Page Elements
  findInPageBar: document.getElementById('findInPageBar'),
  findInput: document.getElementById('findInput'),
  findMatchesCount: document.getElementById('findMatchesCount'),
  btnFindPrev: document.getElementById('btnFindPrev'),
  btnFindNext: document.getElementById('btnFindNext'),
  btnFindClose: document.getElementById('btnFindClose'),
  // Tab Context Menu Elements
  tabContextMenu: document.getElementById('tabContextMenu'),
  ctxPinTab: document.getElementById('ctxPinTab'),
  ctxPinLabel: document.getElementById('ctxPinLabel'),
  ctxMuteTab: document.getElementById('ctxMuteTab'),
  ctxMuteLabel: document.getElementById('ctxMuteLabel'),
  ctxDuplicateTab: document.getElementById('ctxDuplicateTab'),
  ctxSplitTab: document.getElementById('ctxSplitTab'),
  ctxSnoozeTab: document.getElementById('ctxSnoozeTab'),
  ctxContainerDefault: document.getElementById('ctxContainerDefault'),
  ctxContainerPersonal: document.getElementById('ctxContainerPersonal'),
  ctxContainerWork: document.getElementById('ctxContainerWork'),
  ctxContainerBanking: document.getElementById('ctxContainerBanking'),
  ctxContainerShopping: document.getElementById('ctxContainerShopping'),
  ctxCloseTab: document.getElementById('ctxCloseTab'),
  // AdBlock Elements
  menuAdBlock: document.getElementById('menuAdBlock'),
  adblockCountTag: document.getElementById('adblockCountTag')
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

// Dynamic Adaptive Accent Color System
function applyAccentColor(color) {
  if (!color) return;
  currentAccent = color;
  document.documentElement.style.setProperty('--accent', color);
  document.documentElement.style.setProperty('--accent-hover', color);

  try {
    if (elements.webFrame && elements.webFrame.contentWindow) {
      elements.webFrame.contentWindow.postMessage({ type: 'set_accent', accent: color }, '*');
      if (elements.webFrame.contentDocument && elements.webFrame.contentDocument.documentElement) {
        elements.webFrame.contentDocument.documentElement.style.setProperty('--accent', color);
        elements.webFrame.contentDocument.documentElement.style.setProperty('--accent-warm', color);
      }
    }
  } catch (e) {}

  try {
    if (elements.webFrameSplit && elements.webFrameSplit.contentWindow) {
      elements.webFrameSplit.contentWindow.postMessage({ type: 'set_accent', accent: color }, '*');
      if (elements.webFrameSplit.contentDocument && elements.webFrameSplit.contentDocument.documentElement) {
        elements.webFrameSplit.contentDocument.documentElement.style.setProperty('--accent', color);
        elements.webFrameSplit.contentDocument.documentElement.style.setProperty('--accent-warm', color);
      }
    }
  } catch (e) {}
}

// Clean Paper Light / Minimal Dark Theme System
function applyTheme(th) {
  currentTheme = th === 'light' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', currentTheme);

  try {
    if (elements.webFrame && elements.webFrame.contentDocument && elements.webFrame.contentDocument.documentElement) {
      elements.webFrame.contentDocument.documentElement.setAttribute('data-theme', currentTheme);
    }
  } catch(e) {}

  try {
    if (elements.webFrameSplit && elements.webFrameSplit.contentDocument && elements.webFrameSplit.contentDocument.documentElement) {
      elements.webFrameSplit.contentDocument.documentElement.setAttribute('data-theme', currentTheme);
    }
  } catch(e) {}
}

// Full Language Localization System (RU / EN)
function applyLanguage(lang) {
  if (!lang || !I18N[lang]) lang = "ru";
  currentLanguage = lang;
  const dict = I18N[lang];

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const k = el.getAttribute('data-i18n');
    if (dict[k]) el.textContent = dict[k];
  });

  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const k = el.getAttribute('data-i18n-placeholder');
    if (dict[k]) el.placeholder = dict[k];
  });

  if (elements.lblMobileStatus) {
    elements.lblMobileStatus.textContent = isMobileMode ? (lang === 'ru' ? '[ВКЛ]' : '[ON]') : (lang === 'ru' ? '[ВЫКЛ]' : '[OFF]');
  }
}

// Prepare Internal HTML with Dynamic Accent and Theme
function prepareInternalHtml(html) {
  if (!html) return '';
  return html
    .replace(/--accent:\s*#[a-fA-F0-9]{3,6};/g, `--accent: ${currentAccent};`)
    .replace(/--accent-warm:\s*#[a-fA-F0-9]{3,6};/g, `--accent-warm: ${currentAccent};`)
    .replace(/var\(--accent,\s*#[a-fA-F0-9]{3,6}\)/g, `var(--accent, ${currentAccent})`)
    .replace(/<html([^>]*)>/i, `<html$1 data-theme="${currentTheme}">`);
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

// Per-Tab Split View Synchronizer
function syncTabSplitView(tab) {
  if (!tab) return;
  if (tab.is_split) {
    elements.webViewContainer.classList.add('split-mode');
    if (elements.splitPaneWrapper) elements.splitPaneWrapper.classList.remove('hidden');
    if (elements.btnSplitView) elements.btnSplitView.classList.add('active');

    if (elements.splitToolbar) {
      if (tab.hide_split_url) {
        elements.splitToolbar.classList.add('hidden');
        if (elements.btnFloatingShowSplitUrl) elements.btnFloatingShowSplitUrl.classList.remove('hidden');
      } else {
        elements.splitToolbar.classList.remove('hidden');
        if (elements.btnFloatingShowSplitUrl) elements.btnFloatingShowSplitUrl.classList.add('hidden');
      }
    }

    if (elements.webFrameSplit) {
      const splitUrl = tab.split_url || 'crux://startpage';
      if (elements.urlInputSplit) elements.urlInputSplit.value = splitUrl === 'crux://startpage' ? '' : splitUrl;
      if (splitUrl === 'crux://startpage' || splitUrl === 'about:blank') {
        elements.webFrameSplit.removeAttribute('src');
        elements.webFrameSplit.srcdoc = prepareInternalHtml(window.CRUX_STARTPAGE_HTML || '<h1>Crux Startpage</h1>');
      } else if (splitUrl.startsWith('http://') || splitUrl.startsWith('https://')) {
        elements.webFrameSplit.removeAttribute('srcdoc');
        elements.webFrameSplit.src = `http://127.0.0.1:39281/proxy?url=${encodeURIComponent(splitUrl)}`;
      } else {
        elements.webFrameSplit.removeAttribute('srcdoc');
        elements.webFrameSplit.src = splitUrl;
      }
    }
  } else {
    elements.webViewContainer.classList.remove('split-mode');
    if (elements.splitPaneWrapper) elements.splitPaneWrapper.classList.add('hidden');
    if (elements.btnSplitView) elements.btnSplitView.classList.remove('active');
    if (elements.btnFloatingShowSplitUrl) elements.btnFloatingShowSplitUrl.classList.add('hidden');
  }
}

function toggleSplitView() {
  const active = tabs.find(t => t.is_active);
  if (!active) return;
  active.is_split = !active.is_split;
  if (active.is_split && !active.split_url) {
    active.split_url = 'crux://startpage';
  }
  syncTabSplitView(active);
  showToast(active.is_split ? (currentLanguage === 'ru' ? "Разделение экрана: ВКЛ" : "Split View: ON") : (currentLanguage === 'ru' ? "Разделение экрана: ВЫКЛ" : "Split View: OFF"));
}

function navigateSplitTab(input) {
  const active = tabs.find(t => t.is_active);
  if (!active || !elements.webFrameSplit) return;

  let url = (input || "").trim();
  if (!url) {
    url = 'crux://startpage';
  } else if (!url.startsWith('crux://') && !url.startsWith('http://') && !url.startsWith('https://')) {
    if (url.includes('.') && !url.includes(' ')) {
      url = 'https://' + url;
    } else {
      url = getSearchUrl(url);
    }
  }

  active.split_url = url;
  if (elements.urlInputSplit) elements.urlInputSplit.value = url === 'crux://startpage' ? '' : url;

  if (url === 'crux://startpage') {
    elements.webFrameSplit.removeAttribute('src');
    elements.webFrameSplit.srcdoc = prepareInternalHtml(window.CRUX_STARTPAGE_HTML || '<h1>Crux Startpage</h1>');
  } else if (url.startsWith('http://') || url.startsWith('https://')) {
    elements.webFrameSplit.removeAttribute('srcdoc');
    elements.webFrameSplit.src = `http://127.0.0.1:39281/proxy?url=${encodeURIComponent(url)}`;
  } else {
    elements.webFrameSplit.removeAttribute('srcdoc');
    elements.webFrameSplit.src = url;
  }
}

function loadTabContent(tab) {
  if (!tab || !elements.webFrame) return;

  const url = tab.url || 'crux://startpage';

  if (url === 'crux://startpage' || url === 'about:blank') {
    elements.webFrame.removeAttribute('src');
    elements.webFrame.srcdoc = prepareInternalHtml(window.CRUX_STARTPAGE_HTML || '<h1>Crux Startpage</h1>');
    if (elements.urlInput) elements.urlInput.value = '';
    setTimeout(() => {
      applyAccentColor(currentAccent);
      applyTheme(currentTheme);
    }, 60);
  } else if (url.startsWith('crux://settings')) {
    elements.webFrame.removeAttribute('src');
    elements.webFrame.srcdoc = prepareInternalHtml(window.CRUX_SETTINGS_HTML || '<h1>Crux Settings</h1>');
    if (elements.urlInput) elements.urlInput.value = url;
    setTimeout(() => {
      sendIpc('get_settings');
      applyAccentColor(currentAccent);
      applyTheme(currentTheme);
    }, 60);
  } else if (url.startsWith('crux://history')) {
    elements.webFrame.removeAttribute('src');
    elements.webFrame.srcdoc = prepareInternalHtml(window.CRUX_HISTORY_HTML || '<h1>Crux History</h1>');
    if (elements.urlInput) elements.urlInput.value = url;
    setTimeout(() => {
      sendIpc('get_history');
      applyAccentColor(currentAccent);
      applyTheme(currentTheme);
    }, 60);
  } else if (url.startsWith('crux://downloads')) {
    elements.webFrame.removeAttribute('src');
    elements.webFrame.srcdoc = prepareInternalHtml(window.CRUX_DOWNLOADS_HTML || '<h1>Crux Downloads</h1>');
    if (elements.urlInput) elements.urlInput.value = url;
    setTimeout(() => {
      sendIpc('get_downloads');
      applyAccentColor(currentAccent);
      applyTheme(currentTheme);
    }, 60);
  } else if (url.startsWith('http://') || url.startsWith('https://')) {
    elements.webFrame.removeAttribute('srcdoc');
    // Load external site through embedded Rust proxy to bypass WebKit CSP & X-Frame-Options
    elements.webFrame.src = `http://127.0.0.1:39281/proxy?url=${encodeURIComponent(url)}`;
    if (elements.urlInput) elements.urlInput.value = url;
  } else {
    elements.webFrame.removeAttribute('srcdoc');
    elements.webFrame.src = url;
    if (elements.urlInput) elements.urlInput.value = url;
  }

  syncTabSplitView(tab);
  applyZoom(currentZoom);
}

// Letter Badge Helper for Compact Mode & Tab Favicon Fallback
function getTabBadgeLetter(tab) {
  const url = tab.url || '';
  if (url.startsWith('crux://startpage')) return 'C';
  if (url.startsWith('crux://settings')) return '⚙';
  if (url.startsWith('crux://history')) return 'H';
  if (url.startsWith('crux://downloads')) return 'D';
  try {
    const host = new URL(url).hostname.replace(/^www\./, '');
    if (host.length > 0) return host[0].toUpperCase();
  } catch(e) {}
  if (tab.title && tab.title.trim().length > 0) return tab.title.trim()[0].toUpperCase();
  return 'T';
}

// Tab Rendering (Vertical)
function renderTabs() {
  if (!elements.tabsList) return;
  elements.tabsList.innerHTML = '';
  tabs.forEach(tab => {
    const el = document.createElement('div');
    el.className = `tab-item ${tab.is_active ? 'active' : ''}`;

    // Always render domain initial badge for compact mode & crisp recognition
    const badge = document.createElement('span');
    badge.className = 'tab-badge';
    badge.textContent = getTabBadgeLetter(tab);
    badge.title = tab.title || tab.url;
    el.appendChild(badge);

    if (tab.is_pinned) {
      const pin = document.createElement('span');
      pin.className = 'tab-pin-badge';
      pin.innerHTML = ICONS.pin;
      pin.title = "Pinned Tab";
      el.appendChild(pin);
    }

    if (tab.container && tab.container !== 'default') {
      const cBadge = document.createElement('span');
      cBadge.className = 'tab-pin-badge';
      cBadge.style.fontSize = '9px';
      cBadge.style.color = 'var(--accent)';
      cBadge.textContent = `[${tab.container.toUpperCase()}]`;
      el.appendChild(cBadge);
    }

    const title = document.createElement('span');
    title.className = 'tab-title';
    title.textContent = tab.title || (tab.url === 'crux://startpage' ? 'Crux Startpage' : 'New Tab');
    el.appendChild(title);

    // Speaker / Mute icon ONLY shown when playing audio or muted
    if (tab.is_muted || tab.is_playing_audio) {
      const muteBtn = document.createElement('button');
      muteBtn.className = `tab-mute ${tab.is_muted ? 'muted' : ''}`;
      muteBtn.innerHTML = tab.is_muted ? ICONS.volumeMuted : ICONS.volume;
      muteBtn.title = tab.is_muted ? 'Unmute Tab' : 'Mute Tab';
      muteBtn.onclick = (e) => {
        e.stopPropagation();
        tab.is_muted = !tab.is_muted;
        sendIpc('toggle_mute', { id: tab.id });
        renderTabs();
        renderHorizontalTabs();
      };
      el.appendChild(muteBtn);
    }

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
    el.oncontextmenu = (e) => {
      e.preventDefault();
      e.stopPropagation();
      openTabContextMenu(e, tab);
    };

    elements.tabsList.appendChild(el);
  });
  updateNavButtons();
}

// Horizontal Tabs Rendering
function renderHorizontalTabs() {
  if (!elements.horizontalTabsList) return;
  elements.horizontalTabsList.innerHTML = '';
  tabs.forEach(tab => {
    const el = document.createElement('div');
    el.className = `horizontal-tab-item ${tab.is_active ? 'active' : ''}`;

    const badge = document.createElement('span');
    badge.className = 'tab-badge';
    badge.style.width = '16px';
    badge.style.height = '16px';
    badge.style.fontSize = '9px';
    badge.style.marginRight = '4px';
    badge.textContent = getTabBadgeLetter(tab);
    el.appendChild(badge);

    if (tab.is_pinned) {
      const pin = document.createElement('span');
      pin.className = 'tab-pin-badge';
      pin.innerHTML = ICONS.pin;
      pin.style.marginRight = '4px';
      el.appendChild(pin);
    }

    if (tab.container && tab.container !== 'default') {
      const cBadge = document.createElement('span');
      cBadge.style.fontSize = '9px';
      cBadge.style.color = 'var(--accent)';
      cBadge.style.marginRight = '4px';
      cBadge.textContent = `[${tab.container.toUpperCase()}]`;
      el.appendChild(cBadge);
    }

    const title = document.createElement('span');
    title.className = 'tab-title';
    title.textContent = tab.title || (tab.url === 'crux://startpage' ? 'Startpage' : 'New Tab');
    el.appendChild(title);

    // Audio icon only if muted or playing
    if (tab.is_muted || tab.is_playing_audio) {
      const muteBtn = document.createElement('button');
      muteBtn.className = `tab-mute ${tab.is_muted ? 'muted' : ''}`;
      muteBtn.innerHTML = tab.is_muted ? ICONS.volumeMuted : ICONS.volume;
      muteBtn.onclick = (e) => {
        e.stopPropagation();
        tab.is_muted = !tab.is_muted;
        sendIpc('toggle_mute', { id: tab.id });
        renderTabs();
        renderHorizontalTabs();
      };
      el.appendChild(muteBtn);
    }

    if (!tab.is_pinned) {
      const close = document.createElement('button');
      close.className = 'tab-close';
      close.innerHTML = ICONS.close;
      close.onclick = (e) => {
        e.stopPropagation();
        closeTab(tab.id);
      };
      el.appendChild(close);
    }

    el.onclick = () => activateTab(tab.id);
    el.oncontextmenu = (e) => {
      e.preventDefault();
      e.stopPropagation();
      openTabContextMenu(e, tab);
    };

    elements.horizontalTabsList.appendChild(el);
  });
}

function setTabOrientation(orient) {
  tabOrientation = orient === 'horizontal' ? 'horizontal' : 'vertical';
  if (tabOrientation === 'horizontal') {
    if (elements.sidebar) elements.sidebar.classList.add('hidden');
    if (elements.horizontalTabBar) elements.horizontalTabBar.classList.remove('hidden');
    renderHorizontalTabs();
  } else {
    if (elements.sidebar) elements.sidebar.classList.remove('hidden');
    if (elements.horizontalTabBar) elements.horizontalTabBar.classList.add('hidden');
    renderTabs();
  }
  if (elements.chkTabVert) elements.chkTabVert.textContent = tabOrientation === 'vertical' ? '[x]' : '[ ]';
  if (elements.chkTabHoriz) elements.chkTabHoriz.textContent = tabOrientation === 'horizontal' ? '[x]' : '[ ]';
  sendIpc('save_setting', { key: 'tab_orientation', value: tabOrientation });
}

function setUiMode(mode) {
  uiMode = mode === 'vim' ? 'vim' : 'minimal';
  const topNav = document.getElementById('topNav');

  if (uiMode === 'vim') {
    if (topNav) topNav.classList.add('hidden');
    if (elements.sidebar) elements.sidebar.classList.add('hidden');
    if (elements.horizontalTabBar) elements.horizontalTabBar.classList.add('hidden');
    if (elements.vimStatusBar) elements.vimStatusBar.classList.remove('hidden');
    showToast(currentLanguage === 'ru' ? "Vim-режим: Нажмите Esc для выхода" : "Vim Mode: Press Esc to exit");
  } else {
    if (topNav) topNav.classList.remove('hidden');
    if (elements.vimStatusBar) elements.vimStatusBar.classList.add('hidden');
    setTabOrientation(tabOrientation);
    showToast(currentLanguage === 'ru' ? "Минималистичный режим" : "Minimal UI Mode");
  }

  if (elements.chkUiMinimal) elements.chkUiMinimal.textContent = uiMode === 'minimal' ? '[x]' : '[ ]';
  if (elements.chkUiVim) elements.chkUiVim.textContent = uiMode === 'vim' ? '[x]' : '[ ]';
  sendIpc('save_setting', { key: 'ui_mode', value: uiMode });
}

function activateTab(id) {
  tabs.forEach(t => t.is_active = (t.id === id));
  renderTabs();
  renderHorizontalTabs();
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
  } else if (url.startsWith('crux://')) {
    // Keep internal URLs
  } else if (!url.startsWith('http://') && !url.startsWith('https://')) {
    if (url.includes('.') && !url.includes(' ')) {
      url = 'https://' + url;
    } else {
      url = getSearchUrl(url);
    }
  }

  active.url = url;
  if (url === 'crux://startpage') {
    active.title = 'Crux Startpage';
  } else if (url.startsWith('crux://settings')) {
    active.title = 'Crux Settings';
  } else if (url.startsWith('crux://history')) {
    active.title = 'Crux History';
  } else if (url.startsWith('crux://downloads')) {
    active.title = 'Crux Downloads';
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
  renderHorizontalTabs();
  sendIpc('navigate', { url });
}

function createTab(url = 'crux://startpage', container = 'default') {
  const newId = (tabs.length ? Math.max(...tabs.map(t => t.id)) : 0) + 1;
  tabs.forEach(t => t.is_active = false);

  let title = 'New Tab';
  if (url === 'crux://startpage') title = 'Crux Startpage';
  else if (url.startsWith('crux://settings')) title = 'Crux Settings';
  else if (url.startsWith('crux://history')) title = 'Crux History';
  else if (url.startsWith('crux://downloads')) title = 'Crux Downloads';

  const tab = {
    id: newId,
    title,
    url,
    history: [url],
    historyIndex: 0,
    container,
    is_pinned: false,
    is_muted: false,
    is_playing_audio: false,
    is_split: false,
    split_url: 'crux://startpage',
    hide_split_url: false,
    is_active: true
  };
  tabs.push(tab);
  renderTabs();
  renderHorizontalTabs();
  activateTab(newId);
  sendIpc('create_tab', { url, container });
}

function closeTab(id) {
  const idx = tabs.findIndex(t => t.id === id);
  if (idx === -1) return;

  const closed = tabs[idx];
  closedTabsStack.push(closed);

  tabs.splice(idx, 1);
  if (tabs.length === 0) {
    createTab('crux://startpage');
    return;
  }

  if (closed.is_active) {
    const nextIdx = Math.max(0, idx - 1);
    tabs[nextIdx].is_active = true;
    loadTabContent(tabs[nextIdx]);
  }

  renderTabs();
  renderHorizontalTabs();
  sendIpc('close_tab', { id });
}

function reopenLastClosedTab() {
  if (closedTabsStack.length === 0) {
    showToast(currentLanguage === 'ru' ? "Нет закрытых вкладок для восстановления" : "No recently closed tabs");
    return;
  }
  const last = closedTabsStack.pop();
  createTab(last.url, last.container);
  showToast(currentLanguage === 'ru' ? `Восстановлена вкладка: ${last.title}` : `Reopened: ${last.title}`);
}

function getSearchUrl(query) {
  const q = encodeURIComponent(query);
  switch (searchEngine) {
    case 'google': return `https://www.google.com/search?q=${q}`;
    case 'searxng': return `https://searx.be/search?q=${q}`;
    case 'brave': return `https://search.brave.com/search?q=${q}`;
    case 'duckduckgo':
    default:
      return `https://duckduckgo.com/?q=${q}`;
  }
}

// Live Responsive Viewport & Mobile Mode System
function applyMobileViewport() {
  if (!isMobileMode || !elements.webFrame) return;

  const isCustomResponsive = elements.vpPresetSelect && elements.vpPresetSelect.value === 'custom';

  if (isCustomResponsive) {
    elements.webFrame.style.width = '100%';
    elements.webFrame.style.height = '100%';
    elements.webFrame.style.maxWidth = '100%';
    elements.webFrame.style.maxHeight = '100%';
    elements.webFrame.style.transform = '';
    return;
  }

  const containerW = (elements.webViewContainer ? elements.webViewContainer.clientWidth : window.innerWidth) - 40;
  const containerH = (elements.webViewContainer ? elements.webViewContainer.clientHeight : window.innerHeight) - 40;

  let scale = 1.0;
  if (mobileWidth > containerW || mobileHeight > containerH) {
    scale = Math.min(containerW / mobileWidth, containerH / mobileHeight);
  }

  elements.webFrame.style.width = `${mobileWidth}px`;
  elements.webFrame.style.height = `${mobileHeight}px`;
  elements.webFrame.style.maxWidth = `${mobileWidth}px`;
  elements.webFrame.style.maxHeight = `${mobileHeight}px`;
  elements.webFrame.style.transform = scale < 1.0 ? `scale(${scale.toFixed(3)})` : '';
  elements.webFrame.style.transformOrigin = 'center center';
}

function setMobileMode(active, width = 390, height = 844) {
  isMobileMode = active;
  mobileWidth = width;
  mobileHeight = height;

  if (elements.viewportBar) {
    if (isMobileMode) elements.viewportBar.classList.remove('hidden');
    else elements.viewportBar.classList.add('hidden');
  }

  if (elements.webViewContainer) {
    if (isMobileMode) {
      elements.webViewContainer.classList.add('mobile-mode');
    } else {
      elements.webViewContainer.classList.remove('mobile-mode');
    }
  }

  if (isMobileMode) {
    applyMobileViewport();
  } else if (elements.webFrame) {
    elements.webFrame.style.width = '100%';
    elements.webFrame.style.height = '100%';
    elements.webFrame.style.maxWidth = '100%';
    elements.webFrame.style.maxHeight = '100%';
    elements.webFrame.style.transform = '';
    elements.webFrame.style.border = 'none';
    elements.webFrame.style.boxShadow = 'none';
    applyZoom(currentZoom);
  }

  if (elements.vpWidthInput) elements.vpWidthInput.value = mobileWidth;
  if (elements.vpHeightInput) elements.vpHeightInput.value = mobileHeight;
  if (elements.lblMobileStatus) {
    elements.lblMobileStatus.textContent = isMobileMode ? (currentLanguage === 'ru' ? '[ВКЛ]' : '[ON]') : (currentLanguage === 'ru' ? '[ВЫКЛ]' : '[OFF]');
    elements.lblMobileStatus.style.color = isMobileMode ? '#10b981' : 'var(--text-muted)';
  }
}

window.addEventListener('resize', () => {
  if (isMobileMode) applyMobileViewport();
});

function toggleMobileMode() {
  setMobileMode(!isMobileMode, mobileWidth, mobileHeight);
  showToast(isMobileMode ? `Mobile Viewport: ${mobileWidth}x${mobileHeight}` : "Desktop Viewport");
}

// Live Smooth Zoom System
function applyZoom(z) {
  currentZoom = Math.min(2.5, Math.max(0.5, Math.round(z * 10) / 10));
  if (elements.zoomLevelLbl) elements.zoomLevelLbl.textContent = `${Math.round(currentZoom * 100)}%`;

  if (elements.webFrame && !isMobileMode) {
    if (Math.abs(currentZoom - 1.0) < 0.01) {
      elements.webFrame.style.transform = '';
      elements.webFrame.style.transformOrigin = '';
      elements.webFrame.style.width = '100%';
      elements.webFrame.style.height = '100%';
    } else {
      elements.webFrame.style.transformOrigin = '0 0';
      elements.webFrame.style.transform = `scale(${currentZoom})`;
      elements.webFrame.style.width = `${(100 / currentZoom).toFixed(3)}%`;
      elements.webFrame.style.height = `${(100 / currentZoom).toFixed(3)}%`;
    }
  }

  try {
    if (elements.webFrame && elements.webFrame.contentDocument && elements.webFrame.contentDocument.body) {
      elements.webFrame.contentDocument.body.style.zoom = currentZoom;
    }
  } catch (e) {}
}

// Navigation & Tab Controls Listeners
if (elements.btnNewTab) elements.btnNewTab.addEventListener('click', () => createTab('crux://startpage'));
if (elements.btnNewTabHoriz) elements.btnNewTabHoriz.addEventListener('click', () => createTab('crux://startpage'));

if (elements.btnToggleSidebar) {
  elements.btnToggleSidebar.addEventListener('click', () => {
    elements.sidebar.classList.toggle('compact');
  });
}

if (elements.btnBack) {
  elements.btnBack.addEventListener('click', () => {
    const active = tabs.find(t => t.is_active);
    if (!active || active.historyIndex <= 0) return;
    active.historyIndex--;
    const prevUrl = active.history[active.historyIndex];
    active.url = prevUrl;
    loadTabContent(active);
    updateNavButtons();
  });
}

if (elements.btnForward) {
  elements.btnForward.addEventListener('click', () => {
    const active = tabs.find(t => t.is_active);
    if (!active || active.historyIndex >= active.history.length - 1) return;
    active.historyIndex++;
    const nextUrl = active.history[active.historyIndex];
    active.url = nextUrl;
    loadTabContent(active);
    updateNavButtons();
  });
}

if (elements.btnReload) {
  elements.btnReload.addEventListener('click', () => {
    const active = tabs.find(t => t.is_active);
    if (!active) return;
    loadTabContent(active);
    showToast(currentLanguage === 'ru' ? "Страница обновлена" : "Page reloaded");
  });
}

if (elements.urlInput) {
  elements.urlInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      navigateActiveTab(elements.urlInput.value);
    }
  });
}

if (elements.urlInputSplit) {
  elements.urlInputSplit.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      navigateSplitTab(elements.urlInputSplit.value);
    }
  });
}

if (elements.btnToggleSplitUrl) {
  elements.btnToggleSplitUrl.addEventListener('click', () => {
    const active = tabs.find(t => t.is_active);
    if (active) {
      active.hide_split_url = true;
      syncTabSplitView(active);
    }
  });
}

if (elements.btnFloatingShowSplitUrl) {
  elements.btnFloatingShowSplitUrl.addEventListener('click', () => {
    const active = tabs.find(t => t.is_active);
    if (active) {
      active.hide_split_url = false;
      syncTabSplitView(active);
    }
  });
}

if (elements.btnCloseSplit) {
  elements.btnCloseSplit.addEventListener('click', () => {
    toggleSplitView();
  });
}

if (elements.btnSplitView) {
  elements.btnSplitView.addEventListener('click', toggleSplitView);
}

// Mobile Viewport Controls
if (elements.vpPresetSelect) {
  elements.vpPresetSelect.addEventListener('change', (e) => {
    const val = e.target.value;
    if (val === 'custom') {
      applyMobileViewport();
    } else {
      const parts = val.split('x');
      const w = parseInt(parts[0]);
      const h = parseInt(parts[1]);
      if (!isNaN(w) && !isNaN(h)) {
        mobileWidth = w;
        mobileHeight = h;
        if (elements.vpWidthInput) elements.vpWidthInput.value = w;
        if (elements.vpHeightInput) elements.vpHeightInput.value = h;
        applyMobileViewport();
      }
    }
  });
}

if (elements.vpWidthInput) {
  elements.vpWidthInput.addEventListener('input', (e) => {
    const w = parseInt(e.target.value);
    if (!isNaN(w) && w >= 200) {
      mobileWidth = w;
      applyMobileViewport();
    }
  });
}

if (elements.vpHeightInput) {
  elements.vpHeightInput.addEventListener('input', (e) => {
    const h = parseInt(e.target.value);
    if (!isNaN(h) && h >= 200) {
      mobileHeight = h;
      applyMobileViewport();
    }
  });
}

if (elements.btnVpRotate) {
  elements.btnVpRotate.addEventListener('click', () => {
    const tmp = mobileWidth;
    mobileWidth = mobileHeight;
    mobileHeight = tmp;
    if (elements.vpWidthInput) elements.vpWidthInput.value = mobileWidth;
    if (elements.vpHeightInput) elements.vpHeightInput.value = mobileHeight;
    applyMobileViewport();
  });
}

if (elements.btnVpClose) {
  elements.btnVpClose.addEventListener('click', () => {
    setMobileMode(false);
  });
}

// Fullscreen Button
if (elements.btnFullscreen) {
  elements.btnFullscreen.addEventListener('click', () => {
    sendIpc('toggle_fullscreen');
  });
}

// Exit Vim Button
if (elements.btnExitVim) {
  elements.btnExitVim.addEventListener('click', () => {
    setUiMode('minimal');
  });
}

// Zoom Controls
if (elements.btnZoomIn) elements.btnZoomIn.addEventListener('click', () => applyZoom(currentZoom + 0.1));
if (elements.btnZoomOut) elements.btnZoomOut.addEventListener('click', () => applyZoom(currentZoom - 0.1));
if (elements.btnZoomReset) elements.btnZoomReset.addEventListener('click', () => applyZoom(1.0));
if (elements.btnFullscreen) {
  elements.btnFullscreen.addEventListener('click', () => {
    closeAppMenu();
    sendIpc('window_maximize');
  });
}

// Unified Popups & Backdrop Controller
function closeAllPopups() {
  if (elements.appMenu) elements.appMenu.classList.add('hidden');
  if (elements.bookmarksPopup) elements.bookmarksPopup.classList.add('hidden');
  if (elements.downloadsPopup) elements.downloadsPopup.classList.add('hidden');
  if (elements.tabContextMenu) elements.tabContextMenu.classList.add('hidden');
  if (elements.popupBackdrop) elements.popupBackdrop.classList.add('hidden');
}

if (elements.popupBackdrop) {
  elements.popupBackdrop.addEventListener('click', closeAllPopups);
}

function openInternalPage(url) {
  closeAllPopups();
  createTab(url);
}

function toggleBookmarksPopup(e) {
  if (e) e.stopPropagation();
  const isHidden = elements.bookmarksPopup ? elements.bookmarksPopup.classList.contains('hidden') : true;
  closeAllPopups();
  if (isHidden && elements.bookmarksPopup) {
    sendIpc('get_bookmarks');
    elements.bookmarksPopup.classList.remove('hidden');
    if (elements.popupBackdrop) elements.popupBackdrop.classList.remove('hidden');
  }
}

function closeBookmarksPopup() {
  if (elements.bookmarksPopup) elements.bookmarksPopup.classList.add('hidden');
}

function renderBookmarksList(bookmarks) {
  if (!elements.bookmarksListPopup) return;
  elements.bookmarksListPopup.innerHTML = '';

  if (!bookmarks || bookmarks.length === 0) {
    elements.bookmarksListPopup.innerHTML = `<div class="popup-empty">${currentLanguage === 'ru' ? 'Нет сохраненных закладок' : 'No saved bookmarks'}</div>`;
    return;
  }

  bookmarks.forEach(bm => {
    const item = document.createElement('div');
    item.className = 'popup-item';

    const info = document.createElement('div');
    info.className = 'popup-item-info';

    const title = document.createElement('div');
    title.className = 'popup-item-title';
    title.textContent = bm.title || bm.url;

    const url = document.createElement('div');
    url.className = 'popup-item-url';
    url.textContent = bm.url;

    info.appendChild(title);
    info.appendChild(url);
    item.appendChild(info);

    const delBtn = document.createElement('button');
    delBtn.className = 'popup-item-delete';
    delBtn.innerHTML = ICONS.close;
    delBtn.title = "Delete Bookmark";
    delBtn.onclick = (e) => {
      e.stopPropagation();
      sendIpc('delete_bookmark', { url: bm.url });
      item.remove();
      showToast(currentLanguage === 'ru' ? "Закладка удалена" : "Bookmark deleted");
    };
    item.appendChild(delBtn);

    item.onclick = () => {
      closeAllPopups();
      navigateActiveTab(bm.url);
    };

    elements.bookmarksListPopup.appendChild(item);
  });
}

if (elements.btnBookmark) elements.btnBookmark.addEventListener('click', toggleBookmarksPopup);

if (elements.btnAddCurrentBookmark) {
  elements.btnAddCurrentBookmark.addEventListener('click', () => {
    const active = tabs.find(t => t.is_active);
    if (!active) return;
    sendIpc('add_bookmark', { url: active.url, title: active.title });
    showToast(currentLanguage === 'ru' ? `Добавлено в закладки: ${active.title}` : `Bookmarked: ${active.title}`);
    setTimeout(() => sendIpc('get_bookmarks'), 50);
  });
}

function toggleDownloadsPopup(e) {
  if (e) e.stopPropagation();
  const isHidden = elements.downloadsPopup ? elements.downloadsPopup.classList.contains('hidden') : true;
  closeAllPopups();
  if (isHidden && elements.downloadsPopup) {
    sendIpc('get_downloads');
    elements.downloadsPopup.classList.remove('hidden');
    if (elements.popupBackdrop) elements.popupBackdrop.classList.remove('hidden');
  }
}

function closeDownloadsPopup() {
  if (elements.downloadsPopup) elements.downloadsPopup.classList.add('hidden');
}

function renderDownloadsList(downloads) {
  if (!elements.downloadsListPopup) return;
  elements.downloadsListPopup.innerHTML = '';

  if (!downloads || downloads.length === 0) {
    elements.downloadsListPopup.innerHTML = `<div class="popup-empty">${currentLanguage === 'ru' ? 'Загрузок пока нет' : 'No recent downloads'}</div>`;
    return;
  }

  downloads.forEach(dl => {
    const item = document.createElement('div');
    item.className = 'popup-item';

    const info = document.createElement('div');
    info.className = 'popup-item-info';

    const title = document.createElement('div');
    title.className = 'popup-item-title';
    title.textContent = dl.filename || dl.url;

    const size = document.createElement('div');
    size.className = 'popup-item-url';
    const mb = dl.total_bytes ? `${(dl.total_bytes / (1024 * 1024)).toFixed(1)} MB • ` : '';
    size.textContent = `${mb}${dl.status || 'Completed'}`;

    info.appendChild(title);
    info.appendChild(size);
    item.appendChild(info);

    item.onclick = () => {
      closeAllPopups();
      if (dl.save_path) {
        sendIpc('open_file', { path: dl.save_path });
      } else {
        sendIpc('open_downloads_folder');
      }
    };

    elements.downloadsListPopup.appendChild(item);
  });
}

if (elements.btnDownloads) elements.btnDownloads.addEventListener('click', toggleDownloadsPopup);
if (elements.btnOpenDownloadsFolder) elements.btnOpenDownloadsFolder.addEventListener('click', () => sendIpc('open_downloads_folder'));
if (elements.btnViewAllDownloads) elements.btnViewAllDownloads.addEventListener('click', () => openInternalPage('crux://downloads'));

// App Menu Controller
function toggleAppMenu(e) {
  if (e) e.stopPropagation();
  const isHidden = elements.appMenu ? elements.appMenu.classList.contains('hidden') : true;
  closeAllPopups();
  if (isHidden && elements.appMenu) {
    elements.appMenu.classList.remove('hidden');
    if (elements.popupBackdrop) elements.popupBackdrop.classList.remove('hidden');
  }
}

function closeAppMenu() {
  if (elements.appMenu) elements.appMenu.classList.add('hidden');
}

if (elements.btnMenu) elements.btnMenu.addEventListener('click', toggleAppMenu);

// Developer Tools
function openDevTools() {
  sendIpc('open_devtools');
  showToast(currentLanguage === 'ru' ? "Инструменты разработчика WebKitGTK открыты" : "WebKitGTK Developer Tools opened");
}

// Distraction-Free Reader Mode
function toggleReaderMode() {
  if (!elements.readerOverlay) return;
  const isHidden = elements.readerOverlay.classList.contains('hidden');

  if (isHidden) {
    const active = tabs.find(t => t.is_active);
    if (!active) return;
    const url = active.url;

    if (url.startsWith('crux://') || url === 'about:blank') {
      showToast(currentLanguage === 'ru' ? "Режим чтения недоступен для системных страниц" : "Reader mode unavailable for internal pages");
      return;
    }

    elements.readerTitle.textContent = active.title || 'Reader View';
    elements.readerContent.innerHTML = `
      <h2 style="font-size: 22px; margin-bottom: 8px;">${escapeHtml(active.title || 'Loading Article...')}</h2>
      <p style="color: var(--text-muted); font-size: 12px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 10px;">Source: ${escapeHtml(url)}</p>
      <div style="font-size: 14px; line-height: 1.8; color: var(--text-muted);">
        ${currentLanguage === 'ru' ? 'Извлечение чистого текста статьи...' : 'Extracting clean article text...'}
      </div>
    `;
    elements.readerOverlay.classList.remove('hidden');
    sendIpc('fetch_reader_content', { url });
  } else {
    elements.readerOverlay.classList.add('hidden');
  }
}

if (elements.btnReaderMode) elements.btnReaderMode.addEventListener('click', toggleReaderMode);
if (elements.btnCloseReader) elements.btnCloseReader.addEventListener('click', () => elements.readerOverlay.classList.add('hidden'));

// Tab Context Menu Controller
let contextTargetTabId = null;

function openTabContextMenu(e, tab) {
  contextTargetTabId = tab.id;
  closeAllPopups();
  if (!elements.tabContextMenu) return;

  if (elements.ctxPinLabel) {
    elements.ctxPinLabel.textContent = tab.is_pinned
      ? (currentLanguage === 'ru' ? 'Открепить вкладку' : 'Unpin Tab')
      : (currentLanguage === 'ru' ? 'Закрепить вкладку' : 'Pin Tab');
  }

  if (elements.ctxMuteLabel) {
    elements.ctxMuteLabel.textContent = tab.is_muted
      ? (currentLanguage === 'ru' ? 'Включить звук' : 'Unmute Tab')
      : (currentLanguage === 'ru' ? 'Отключить звук' : 'Mute Tab');
  }

  const x = Math.min(e.clientX, window.innerWidth - 240);
  const y = Math.min(e.clientY, window.innerHeight - 300);
  elements.tabContextMenu.style.left = `${x}px`;
  elements.tabContextMenu.style.top = `${y}px`;
  elements.tabContextMenu.classList.remove('hidden');

  if (elements.popupBackdrop) elements.popupBackdrop.classList.remove('hidden');
}

if (elements.ctxPinTab) {
  elements.ctxPinTab.addEventListener('click', () => {
    const tab = tabs.find(t => t.id === contextTargetTabId);
    if (tab) {
      tab.is_pinned = !tab.is_pinned;
      sendIpc('toggle_pin', { id: tab.id });
      renderTabs();
      renderHorizontalTabs();
    }
    closeAllPopups();
  });
}

if (elements.ctxMuteTab) {
  elements.ctxMuteTab.addEventListener('click', () => {
    const tab = tabs.find(t => t.id === contextTargetTabId);
    if (tab) {
      tab.is_muted = !tab.is_muted;
      sendIpc('toggle_mute', { id: tab.id });
      renderTabs();
      renderHorizontalTabs();
    }
    closeAllPopups();
  });
}

if (elements.ctxDuplicateTab) {
  elements.ctxDuplicateTab.addEventListener('click', () => {
    const tab = tabs.find(t => t.id === contextTargetTabId);
    if (tab) createTab(tab.url, tab.container);
    closeAllPopups();
  });
}

if (elements.ctxSplitTab) {
  elements.ctxSplitTab.addEventListener('click', () => {
    activateTab(contextTargetTabId);
    toggleSplitView();
    closeAllPopups();
  });
}

if (elements.ctxSnoozeTab) {
  elements.ctxSnoozeTab.addEventListener('click', () => {
    showToast(currentLanguage === 'ru' ? "Вкладка приостановлена" : "Tab snoozed");
    closeAllPopups();
  });
}

function setTabContainer(name) {
  const tab = tabs.find(t => t.id === contextTargetTabId);
  if (tab) {
    tab.container = name;
    renderTabs();
    renderHorizontalTabs();
    showToast(currentLanguage === 'ru' ? `Контейнер: ${name}` : `Container: ${name}`);
  }
  closeAllPopups();
}

if (elements.ctxContainerDefault) elements.ctxContainerDefault.addEventListener('click', () => setTabContainer('default'));
if (elements.ctxContainerPersonal) elements.ctxContainerPersonal.addEventListener('click', () => setTabContainer('personal'));
if (elements.ctxContainerWork) elements.ctxContainerWork.addEventListener('click', () => setTabContainer('work'));
if (elements.ctxContainerBanking) elements.ctxContainerBanking.addEventListener('click', () => setTabContainer('banking'));
if (elements.ctxContainerShopping) elements.ctxContainerShopping.addEventListener('click', () => setTabContainer('shopping'));

if (elements.ctxCloseTab) {
  elements.ctxCloseTab.addEventListener('click', () => {
    if (contextTargetTabId) closeTab(contextTargetTabId);
    closeAllPopups();
  });
}

// Sidebar Drag-to-Resize Handler
let isResizingSidebar = false;

if (elements.sidebarResizer) {
  elements.sidebarResizer.addEventListener('mousedown', (e) => {
    isResizingSidebar = true;
    elements.sidebarResizer.classList.add('resizing');
    document.body.style.cursor = 'col-resize';
    e.preventDefault();
  });
}

document.addEventListener('mousemove', (e) => {
  if (!isResizingSidebar || !elements.sidebar) return;
  const newWidth = Math.max(140, Math.min(e.clientX, 480));
  elements.sidebar.style.width = `${newWidth}px`;
});

document.addEventListener('mouseup', () => {
  if (!isResizingSidebar) return;
  isResizingSidebar = false;
  if (elements.sidebarResizer) elements.sidebarResizer.classList.remove('resizing');
  document.body.style.cursor = '';
  if (elements.sidebar) {
    sendIpc('save_setting', { key: 'sidebar_width', value: elements.sidebar.style.width });
  }
});

// Find in Page Controller (Ctrl+F)
function toggleFindInPage() {
  if (!elements.findInPageBar) return;
  const isHidden = elements.findInPageBar.classList.contains('hidden');
  if (isHidden) {
    elements.findInPageBar.classList.remove('hidden');
    if (elements.findInput) {
      elements.findInput.focus();
      elements.findInput.select();
    }
    doFind(true);
  } else {
    elements.findInPageBar.classList.add('hidden');
    if (elements.webFrame) elements.webFrame.focus();
  }
}

function doFind(forward = true) {
  if (!elements.findInput) return;
  const query = elements.findInput.value.trim();
  if (!query) {
    if (elements.findMatchesCount) elements.findMatchesCount.textContent = '';
    return;
  }

  let found = false;
  try {
    if (elements.webFrame && elements.webFrame.contentWindow && elements.webFrame.contentWindow.find) {
      found = elements.webFrame.contentWindow.find(query, false, !forward, true, false, false, false);
    }
  } catch(e) {}

  if (!found) {
    try {
      found = window.find(query, false, !forward, true, false, false, false);
    } catch(e) {}
  }

  if (elements.findMatchesCount) {
    elements.findMatchesCount.textContent = found ? (currentLanguage === 'ru' ? 'найдено' : 'match') : (currentLanguage === 'ru' ? '0 совп.' : '0 matches');
    elements.findMatchesCount.style.color = found ? '#10b981' : '#ef4444';
  }
}

if (elements.findInput) {
  elements.findInput.addEventListener('input', () => doFind(true));
  elements.findInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      doFind(!e.shiftKey);
    } else if (e.key === 'Escape') {
      toggleFindInPage();
    }
  });
}
if (elements.btnFindPrev) elements.btnFindPrev.addEventListener('click', () => doFind(false));
if (elements.btnFindNext) elements.btnFindNext.addEventListener('click', () => doFind(true));
if (elements.btnFindClose) elements.btnFindClose.addEventListener('click', toggleFindInPage);

// Full Interactive App Menu Actions
const menuActions = {
  menuMobileMode: toggleMobileMode,
  menuReader: toggleReaderMode,
  menuPip: () => {
    try {
      if (elements.webFrame && elements.webFrame.contentDocument) {
        const video = elements.webFrame.contentDocument.querySelector('video');
        if (video) {
          if (document.pictureInPictureElement) {
            document.exitPictureInPicture();
          } else if (video.requestPictureInPicture) {
            video.requestPictureInPicture();
          }
          return;
        }
      }
    } catch(e) {}
    showToast(currentLanguage === 'ru' ? "Видео для режима картинка-в-картинке не найдено" : "No video found for Picture-in-Picture");
  },
  menuNewTab: () => createTab('crux://startpage'),
  menuReopenClosed: reopenLastClosedTab,
  menuNewWindow: () => showToast(currentLanguage === 'ru' ? "Новое окно Crux активно" : "Crux window active"),
  menuIncognitoWindow: () => {
    createTab('crux://startpage', 'incognito');
    showToast(currentLanguage === 'ru' ? "Создана вкладка инкогнито" : "Incognito container tab created");
  },
  menuFindInPage: toggleFindInPage,
  menuSplit: toggleSplitView,
  menuDevTools: openDevTools,
  menuDownloads: (e) => toggleDownloadsPopup(e),
  menuHistory: () => openInternalPage('crux://history'),
  menuBookmarks: (e) => toggleBookmarksPopup(e),
  menuAi: () => toggleAiPanel(),
  menuAdBlock: () => sendIpc('toggle_adblock'),
  menuSettings: () => openInternalPage('crux://settings'),
  // Submenu Actions
  optTabVert: () => setTabOrientation('vertical'),
  optTabHoriz: () => setTabOrientation('horizontal'),
  optUiMinimal: () => setUiMode('minimal'),
  optUiVim: () => setUiMode('vim'),
  optContainerPersonal: () => createTab('crux://startpage', 'personal'),
  optContainerWork: () => createTab('crux://startpage', 'work'),
  optContainerBanking: () => createTab('crux://startpage', 'banking'),
  optContainerShopping: () => createTab('crux://startpage', 'shopping')
};

Object.entries(menuActions).forEach(([id, action]) => {
  const el = document.getElementById(id);
  if (el) {
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      closeAllPopups();
      action(e);
    });
  }
});

// Dismiss popups on click outside
document.addEventListener('click', (e) => {
  if (elements.appMenu && !elements.appMenu.contains(e.target) && e.target !== elements.btnMenu && !elements.btnMenu.contains(e.target) &&
      elements.bookmarksPopup && !elements.bookmarksPopup.contains(e.target) && e.target !== elements.btnBookmark && !elements.btnBookmark.contains(e.target) &&
      elements.downloadsPopup && !elements.downloadsPopup.contains(e.target) && e.target !== elements.btnDownloads && !elements.btnDownloads.contains(e.target) &&
      elements.tabContextMenu && !elements.tabContextMenu.contains(e.target)) {
    closeAllPopups();
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

// Crux AI Panel
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
  { name: 'New Tab (Ctrl+T)', action: () => createTab('crux://startpage') },
  { name: 'Reopen Closed Tab (Ctrl+Shift+T)', action: reopenLastClosedTab },
  { name: 'Open Preferences & Settings (Ctrl+,)', action: () => openInternalPage('crux://settings') },
  { name: 'Open Browsing History (Ctrl+H)', action: () => openInternalPage('crux://history') },
  { name: 'Open Downloads Manager (Ctrl+Shift+D)', action: () => openInternalPage('crux://downloads') },
  { name: 'Toggle Bookmarks Popup (Ctrl+Shift+O)', action: toggleBookmarksPopup },
  { name: 'Toggle Downloads Popup', action: toggleDownloadsPopup },
  { name: 'Toggle Developer Tools (F12)', action: openDevTools },
  { name: 'Toggle Split View (Ctrl+\\)', action: toggleSplitView },
  { name: 'Toggle Reading Mode (Ctrl+Alt+R)', action: toggleReaderMode },
  { name: 'Toggle Tab Orientation (Vertical / Horizontal)', action: () => setTabOrientation(tabOrientation === 'vertical' ? 'horizontal' : 'vertical') },
  { name: 'Toggle UI Mode (Minimal / Vim)', action: () => setUiMode(uiMode === 'minimal' ? 'vim' : 'minimal') },
  { name: 'Toggle Mobile Viewport (Ctrl+Shift+M)', action: toggleMobileMode },
  { name: 'Toggle Compact Sidebar', action: () => elements.sidebar.classList.toggle('compact') },
  { name: 'Toggle Crux AI Panel (Ctrl+B)', action: toggleAiPanel },
  { name: 'Open Downloads Folder', action: () => sendIpc('open_downloads_folder') },
  { name: 'Choose Default Download Directory', action: () => sendIpc('choose_download_dir') },
  { name: 'Clear SQLite History', action: () => {
    sendIpc('clear_history');
    showToast("History cleared");
  }},
  { name: 'Clear SQLite Downloads', action: () => {
    sendIpc('clear_downloads');
    showToast("Downloads cleared");
  }}
];

function renderCommands(query) {
  if (!elements.paletteResults) return;
  elements.paletteResults.innerHTML = '';
  const filtered = commands.filter(c => c.name.toLowerCase().includes(query.toLowerCase()));
  filtered.forEach((cmd, idx) => {
    const li = document.createElement('li');
    li.className = `palette-item ${idx === 0 ? 'selected' : ''}`;
    li.textContent = cmd.name;
    li.onclick = () => {
      elements.commandPalette.classList.add('hidden');
      cmd.action();
    };
    elements.paletteResults.appendChild(li);
  });
}

if (elements.paletteInput) {
  elements.paletteInput.addEventListener('input', (e) => {
    renderCommands(e.target.value);
  });

  elements.paletteInput.addEventListener('keydown', (e) => {
    const items = elements.paletteResults.querySelectorAll('.palette-item');
    let sel = Array.from(items).findIndex(i => i.classList.contains('selected'));
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (sel < items.length - 1) {
        items[sel].classList.remove('selected');
        items[sel + 1].classList.add('selected');
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (sel > 0) {
        items[sel].classList.remove('selected');
        items[sel - 1].classList.add('selected');
      }
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (sel >= 0 && items[sel]) items[sel].click();
    }
  });
}

if (elements.btnCommandPalette) elements.btnCommandPalette.addEventListener('click', toggleCommandPalette);

// Global Keyboard Shortcuts (Including Vim Mode, Zoom & Find)
function handleGlobalShortcut(e) {
  const isInput = e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable);

  // If typing in find bar, do not hijack normal typing
  if (e.target && e.target.id === 'findInput' && e.key !== 'Escape') {
    return;
  }

  // Escape key always closes overlays, popups, and exits Vim mode
  if (e.key === 'Escape') {
    closeAllPopups();
    if (elements.commandPalette && !elements.commandPalette.classList.contains('hidden')) {
      elements.commandPalette.classList.add('hidden');
    }
    if (elements.readerOverlay && !elements.readerOverlay.classList.contains('hidden')) {
      elements.readerOverlay.classList.add('hidden');
    }
    if (elements.findInPageBar && !elements.findInPageBar.classList.contains('hidden')) {
      elements.findInPageBar.classList.add('hidden');
    }
    if (uiMode === 'vim') {
      setUiMode('minimal');
    }
    return;
  }

  if (e.key === 'F11') {
    if (e.preventDefault) e.preventDefault();
    sendIpc('toggle_fullscreen');
    return;
  }

  // Vim Mode hotkeys (when not typing in an input)
  if (uiMode === 'vim' && !isInput && !e.ctrlKey && !e.altKey && !e.metaKey) {
    if (e.key === 'j') {
      try { elements.webFrame.contentWindow.scrollBy(0, 150); } catch(ex){}
      return;
    } else if (e.key === 'k') {
      try { elements.webFrame.contentWindow.scrollBy(0, -150); } catch(ex){}
      return;
    } else if (e.key === 'd') {
      try { elements.webFrame.contentWindow.scrollBy(0, 450); } catch(ex){}
      return;
    } else if (e.key === 'u') {
      try { elements.webFrame.contentWindow.scrollBy(0, -450); } catch(ex){}
      return;
    } else if (e.key === 'r') {
      const active = tabs.find(t => t.is_active);
      if (active) loadTabContent(active);
      return;
    } else if (e.key === 't') {
      createTab('crux://startpage');
      return;
    } else if (e.key === 'x') {
      const active = tabs.find(t => t.is_active);
      if (active) closeTab(active.id);
      return;
    } else if (e.key === 'J') {
      // Next tab
      const curIdx = tabs.findIndex(t => t.is_active);
      if (curIdx >= 0 && curIdx < tabs.length - 1) activateTab(tabs[curIdx + 1].id);
      return;
    } else if (e.key === 'K') {
      // Previous tab
      const curIdx = tabs.findIndex(t => t.is_active);
      if (curIdx > 0) activateTab(tabs[curIdx - 1].id);
      return;
    }
  }

  const ctrl = e.ctrlKey || e.metaKey;
  const key = (e.key || '').toLowerCase();

  // Zoom hotkeys (Ctrl++, Ctrl+=, Ctrl+-, Ctrl+0)
  if (ctrl && (key === '=' || key === '+')) {
    if (e.preventDefault) e.preventDefault();
    applyZoom(currentZoom + 0.1);
  } else if (ctrl && key === '-') {
    if (e.preventDefault) e.preventDefault();
    applyZoom(currentZoom - 0.1);
  } else if (ctrl && key === '0') {
    if (e.preventDefault) e.preventDefault();
    applyZoom(1.0);
  } else if (ctrl && e.shiftKey && key === 'm') {
    if (e.preventDefault) e.preventDefault();
    toggleMobileMode();
  } else if (ctrl && e.altKey && key === 't') {
    if (e.preventDefault) e.preventDefault();
    setTabOrientation(tabOrientation === 'vertical' ? 'horizontal' : 'vertical');
  } else if (ctrl && key === 'm') {
    if (e.preventDefault) e.preventDefault();
    setUiMode(uiMode === 'minimal' ? 'vim' : 'minimal');
  } else if (ctrl && e.shiftKey && key === 'p') {
    if (e.preventDefault) e.preventDefault();
    toggleCommandPalette();
  } else if (ctrl && key === 't' && !e.shiftKey) {
    if (e.preventDefault) e.preventDefault();
    createTab('crux://startpage');
  } else if (ctrl && e.shiftKey && key === 't') {
    if (e.preventDefault) e.preventDefault();
    reopenLastClosedTab();
  } else if (ctrl && e.shiftKey && key === 'o') {
    if (e.preventDefault) e.preventDefault();
    toggleBookmarksPopup();
  } else if (ctrl && e.shiftKey && key === 'd') {
    if (e.preventDefault) e.preventDefault();
    toggleDownloadsPopup();
  } else if (ctrl && key === 'h' && !e.shiftKey) {
    if (e.preventDefault) e.preventDefault();
    openInternalPage('crux://history');
  } else if (ctrl && key === 'b') {
    if (e.preventDefault) e.preventDefault();
    toggleAiPanel();
  } else if (ctrl && key === 'f') {
    if (e.preventDefault) e.preventDefault();
    toggleFindInPage();
  } else if (ctrl && key === 'l') {
    if (e.preventDefault) e.preventDefault();
    if (elements.urlInput) {
      elements.urlInput.focus();
      elements.urlInput.select();
    }
  } else if (ctrl && key === ',') {
    if (e.preventDefault) e.preventDefault();
    openInternalPage('crux://settings');
  } else if (ctrl && (key === '\\' || e.code === 'Backslash')) {
    if (e.preventDefault) e.preventDefault();
    toggleSplitView();
  } else if (ctrl && e.altKey && key === 'r') {
    if (e.preventDefault) e.preventDefault();
    toggleReaderMode();
  } else if (ctrl && key === 'w' && !e.shiftKey) {
    if (e.preventDefault) e.preventDefault();
    const active = tabs.find(t => t.is_active);
    if (active) closeTab(active.id);
  } else if (e.key === 'F12' || (ctrl && e.shiftKey && key === 'i')) {
    if (e.preventDefault) e.preventDefault();
    openDevTools();
  }
}

document.addEventListener('keydown', handleGlobalShortcut);

// Internal Page Communication Bridge
function handleCruxInternalCommand(cmdUrl) {
  if (!cmdUrl) return;

  if (cmdUrl.startsWith('crux://apply-settings?')) {
    const qs = cmdUrl.substring('crux://apply-settings?'.length);
    const params = new URLSearchParams(qs);
    for (const [key, value] of params.entries()) {
      sendIpc('save_setting', { key, value });
      currentSettings[key] = value;
      if (key === 'search_engine') searchEngine = value;
      if (key === 'accent_color') applyAccentColor(value);
      if (key === 'theme') applyTheme(value);
      if (key === 'language') applyLanguage(value);
      if (key === 'tab_orientation') setTabOrientation(value);
      if (key === 'ui_mode') setUiMode(value);
    }
    showToast(currentLanguage === 'ru' ? "Настройки сохранены" : "Settings saved");
    return;
  }

  if (cmdUrl.startsWith('crux://live-setting?')) {
    const qs = cmdUrl.substring('crux://live-setting?'.length);
    const params = new URLSearchParams(qs);
    const key = params.get('key');
    const value = params.get('value');
    if (key && value !== null) {
      sendIpc('save_setting', { key, value });
      currentSettings[key] = value;
      if (key === 'search_engine') searchEngine = value;
      if (key === 'accent_color') applyAccentColor(value);
      if (key === 'theme') applyTheme(value);
      if (key === 'language') applyLanguage(value);
      if (key === 'tab_orientation') setTabOrientation(value);
      if (key === 'ui_mode') setUiMode(value);
    }
    return;
  }

  if (cmdUrl.startsWith('crux://action/delete-history?')) {
    const qs = cmdUrl.substring('crux://action/delete-history?'.length);
    const params = new URLSearchParams(qs);
    const url = params.get('url');
    if (url) {
      sendIpc('delete_history', { url });
      showToast(currentLanguage === 'ru' ? "Запись удалена" : "History item deleted");
      setTimeout(() => sendIpc('get_history'), 50);
    }
    return;
  }

  if (cmdUrl === 'crux://action/clear-history') {
    sendIpc('clear_history');
    showToast(currentLanguage === 'ru' ? "История очищена" : "History cleared");
    setTimeout(() => sendIpc('get_history'), 50);
    return;
  }

  if (cmdUrl === 'crux://action/open-downloads-folder') {
    sendIpc('open_downloads_folder');
    return;
  }

  if (cmdUrl === 'crux://action/clear-downloads') {
    sendIpc('clear_downloads');
    showToast(currentLanguage === 'ru' ? "Список загрузок очищен" : "Downloads cleared");
    setTimeout(() => sendIpc('get_downloads'), 50);
    return;
  }

  if (cmdUrl.startsWith('crux://action/open-file?')) {
    const qs = cmdUrl.substring('crux://action/open-file?'.length);
    const params = new URLSearchParams(qs);
    const path = params.get('path');
    if (path) sendIpc('open_file', { path });
    return;
  }

  if (cmdUrl.startsWith('crux://new-tab?')) {
    const qs = cmdUrl.substring('crux://new-tab?'.length);
    const params = new URLSearchParams(qs);
    const targetUrl = params.get('url') || 'crux://startpage';
    createTab(targetUrl);
    return;
  }

  if (cmdUrl.startsWith('crux://') || cmdUrl.startsWith('http://') || cmdUrl.startsWith('https://')) {
    navigateActiveTab(cmdUrl);
    return;
  }
}

// Listen to messages from internal page iframes & bypass proxy
window.addEventListener('message', (e) => {
  if (!e.data) return;
  if (e.data.type === 'crux_navigated' && e.data.url) {
    const active = tabs.find(t => t.is_active);
    if (active && active.url !== e.data.url) {
      active.url = e.data.url;
      if (active.history[active.history.length - 1] !== e.data.url) {
        active.history.push(e.data.url);
        active.historyIndex = active.history.length - 1;
      }
      if (elements.urlInput) elements.urlInput.value = e.data.url;
      sendIpc('navigate', { url: e.data.url });
      renderTabs();
      renderHorizontalTabs();
    }
  } else if (e.data.type === 'crux_key') {
    handleGlobalShortcut(e.data);
  } else if (e.data.type === 'crux_click') {
    closeAllPopups();
  } else if (e.data.type === 'navigate' && e.data.url) {
    navigateActiveTab(e.data.url);
  } else if (e.data.type === 'crux_cmd' && e.data.url) {
    handleCruxInternalCommand(e.data.url);
  }
});

// Callbacks from Rust Event Loop
window.onAiResponse = function(text, success) {
  appendAiMessage("assistant", text);
};

window.onBookmarksLoaded = function(bookmarks) {
  currentBookmarks = bookmarks || [];
  renderBookmarksList(currentBookmarks);
};

window.onHistoryLoaded = function(history) {
  currentHistory = history || [];
  if (elements.webFrame && elements.webFrame.contentWindow && elements.webFrame.contentWindow.renderHistory) {
    elements.webFrame.contentWindow.renderHistory(currentHistory);
  }
};

window.onDownloadsLoaded = function(downloads) {
  currentDownloads = downloads || [];
  renderDownloadsList(currentDownloads);
  if (elements.webFrame && elements.webFrame.contentWindow && elements.webFrame.contentWindow.renderDownloads) {
    elements.webFrame.contentWindow.renderDownloads(currentDownloads);
  }
};

window.onAdBlockToggled = function(enabled) {
  if (elements.adblockCountTag) {
    elements.adblockCountTag.textContent = enabled
      ? (currentLanguage === 'ru' ? '[АКТИВЕН]' : '[ACTIVE]')
      : (currentLanguage === 'ru' ? '[ОТКЛЮЧЕН]' : '[DISABLED]');
    elements.adblockCountTag.style.color = enabled ? '#10b981' : '#ef4444';
  }
  showToast(enabled
    ? (currentLanguage === 'ru' ? "Блокировщик рекламы: ВКЛ" : "AdBlock: ON")
    : (currentLanguage === 'ru' ? "Блокировщик рекламы: ВЫКЛ" : "AdBlock: OFF"));
};

window.onSettingsLoaded = function(settings) {
  if (!settings) return;
  currentSettings = settings;

  if (settings.sidebar_width && elements.sidebar) {
    elements.sidebar.style.width = settings.sidebar_width;
  }
  if (settings.adblock_enabled !== undefined && elements.adblockCountTag) {
    const isEn = settings.adblock_enabled !== 'false';
    elements.adblockCountTag.textContent = isEn
      ? (currentLanguage === 'ru' ? '[АКТИВЕН]' : '[ACTIVE]')
      : (currentLanguage === 'ru' ? '[ОТКЛЮЧЕН]' : '[DISABLED]');
    elements.adblockCountTag.style.color = isEn ? '#10b981' : '#ef4444';
  }
  if (settings.search_engine) searchEngine = settings.search_engine;
  if (settings.accent_color) applyAccentColor(settings.accent_color);
  if (settings.theme) applyTheme(settings.theme);
  if (settings.language) applyLanguage(settings.language);
  if (settings.tab_orientation) setTabOrientation(settings.tab_orientation);
  if (settings.ui_mode) setUiMode(settings.ui_mode);

  if (elements.webFrame && elements.webFrame.contentWindow && elements.webFrame.contentWindow.populateSettings) {
    elements.webFrame.contentWindow.populateSettings(settings);
  }
};

window.onDownloadDirSelected = function(path) {
  showToast(`Default download folder: ${path}`);
  if (elements.webFrame && elements.webFrame.contentWindow && elements.webFrame.contentWindow.populateSettings) {
    currentSettings.download_dir = path;
    elements.webFrame.contentWindow.populateSettings(currentSettings);
  }
};

window.onReaderContentLoaded = function(data) {
  if (!elements.readerOverlay || !data) return;
  elements.readerTitle.textContent = data.title || 'Reader View';
  const paragraphs = data.paragraphs || [];
  const parasHtml = paragraphs.length > 0
    ? paragraphs.map(p => `<p style="margin-bottom: 16px; font-size: 15px; line-height: 1.8; color: #f5f5f0;">${escapeHtml(p)}</p>`).join('')
    : '<p style="color: var(--text-muted); font-size: 14px;">No standard article paragraphs could be automatically extracted from this page.</p>';

  elements.readerContent.innerHTML = `
    <h2 style="font-size: 24px; font-weight: bold; margin-bottom: 8px; color: #f5f5f0;">${escapeHtml(data.title || 'Article')}</h2>
    <p style="color: var(--accent); font-size: 12px; margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 12px;">${escapeHtml(data.url)}</p>
    <div class="reader-body">
      ${parasHtml}
    </div>
  `;
};

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, function(m) {
    return ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    })[m];
  });
}

// Initial Render and Boot
renderTabs();
renderHorizontalTabs();
const initialTab = tabs.find(t => t.is_active);
if (initialTab) {
  loadTabContent(initialTab);
}
applyLanguage(currentLanguage);
sendIpc('get_settings');
console.log("Crux 2.0 Rust Architecture initialized with full original parity.");
