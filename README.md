# Sonde

A lightweight, modern, keyboard-driven web browser built with Rust, Wry/WebKitGTK, and native hardware acceleration for Linux and Windows.

Sonde provides distinct interface paradigms, isolated multi-account containers, an integrated superuser-protected password and cookie vault, native request-level content blocking, customizable color themes (with Sand as default), bottom status bar with link preview, Google Gemini and Ollama AI inference tools without background telemetry or bloatware.

---

## Architecture and Interface Modes

Sonde provides dedicated, switchable operational paradigms:

1. **Minimal Mode (Default)**
   - High-density square aesthetic with strict 0px border-radius, 1px borders, and monospace typography.
   - **Switchable Tab Orientation (`Ctrl+Alt+T`)**:
     - *Vertical Sidebar*: Fixed-width tabs on the left with color-coded container badges. Collapsible to a compact icon strip (`Ctrl+[`).
     - *Horizontal Top Tabs*: Traditional horizontal tab bar positioned above the webview with crisp square close buttons.
   - Discrete status indicators, bottom mini status bar with real-time hover link preview and progress bar.

2. **Vim Mode**
   - Distraction-free browsing.
   - Full keyboard navigation works on both Russian and English keyboard layouts (`j`, `k`, `d`, `u`, `r`, `t`, `x`, `J`, `K`).
   - Dedicated `[EXIT VIM]` corner button and `Escape` key return path to standard mode.

Switch between modes at any time using `Ctrl+M`, the status bar mode menu, or Settings (`Ctrl+,`).

---

## Visual Theming and Accent Colors

Sonde supports dynamic system theming without requiring application restarts:

- **Themes:** Claude Code Minimal Dark and Clean Paper Light.
- **Accent Presets:**
   - Desert Sand (`#d4a373`) — *Default (Balanced contrast, warm desert sand)*
   - Amber Orange (`#fe8019`)
   - Emerald Green (`#10b981`)
   - Sky Blue (`#38bdf8`)
   - Nordic Purple (`#a855f7`)
   - Monochrome Slate (`#94a3b8`)

Configure your appearance via Settings (`Ctrl+,`) or during initial first-launch onboarding modal (`sonde://welcome`).

---

- **Bottom Mini Status Bar**: Compact bottom status bar displaying real-time hovered hyperlink destinations, animated page loading progress bar, current zoom level, and security status badge (`🔒 SECURE` / `⚠️ HTTP` / `⚡ SONDE`).
- **Interactive Hotkey Configuration**: View and customize keyboard shortcuts directly in Settings (`Ctrl+,`), with persistent storage in SQLite.
- **First-Run Onboarding Modal**: First-launch onboarding modal to configure interface language, accent color, search engine, and UI mode.
- **Custom URL Scheme Handler (`sonde://`)**: Native protocol handler for internal settings, history, and downloads (with automatic backward-compatibility aliasing for `crux://` and `zephyrium://`).
- **Google Gemini & Ollama AI Integration**: Built-in AI panel with Google Gemini 2.5 Flash, 1.5 Pro, 1.5 Flash, DeepSeek, OpenAI, Ollama, and custom model inputs.
- **Secure Credentials Vault**: Password storage protected by system authentication with native IPC routing ensuring sensitive data is never exposed to the address bar.
- **Distraction-Free Reader Mode**: Clean typography and instant toggle (`Ctrl+Alt+R`) converting noisy articles into readable layouts.
- **Picture-in-Picture (PiP)**: Pop out HTML5 videos into a persistent floating window (`Ctrl+Alt+P`).
- **Native AdBlocker and Privacy Engine**: Network-level request interceptor with a persistent whitelist, URL tracking parameter stripping (`utm_*`, `fbclid`, `gclid`).
- **Automatic File & Userscript Downloads**: Direct downloads into `~/Downloads/` (and `~/.config/sonde/scripts/` for userscripts like Better xCloud).
- **Multilingual Support (i18n)**: Full localization engine covering 10 major languages: English, Russian, Simplified Chinese, Spanish, German, French, Japanese, Portuguese, Italian, and Turkish.
- **Wayland and Desktop Integration**: Linux process name registered as `crux` via `prctl(PR_SET_NAME)`. Conforms to `StartupWMClass=crux` for Waybar, Hyprland, Sway, GNOME, and KDE task managers.

---

## Keybindings

### Global Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + M` | Cycle layout modes (Minimal <-> Vim) |
| `Ctrl + Alt + T` | Toggle tab orientation (Vertical / Horizontal) |
| `Ctrl + Alt + R` | Toggle Reader Mode |
| `Ctrl + Alt + P` | Toggle Picture-in-Picture (PiP) |
| `Ctrl + [` | Toggle vertical sidebar compact mode (50px / 240px) |
| `Ctrl + ,` | Open Settings and Credentials Vault |
| `Ctrl + K` | Open Command Palette / Keybinds |
| `Ctrl + L` | Focus and select URL bar |
| `Ctrl + T` | New tab in default container |
| `Ctrl + W` | Close active tab (closes window if last tab) |
| `Ctrl + \` | Toggle split-view container |
| `Ctrl + B` | Toggle AI Assistant and Notes sidebar |
| `Ctrl + Shift + D` | Toggle Downloads manager |
| `Alt + Shift + W` | Open new tab in Work container |
| `Alt + Shift + D` | Open new tab in Dev container |
| `Alt + Shift + I` | Open new tab in Incognito container |
| `Ctrl + R` / `F5` | Reload active page |
| `Ctrl + Shift + R` | Hard reload bypassing cache |
| `Ctrl + +` / `Ctrl + -` | Zoom in / Zoom out |
| `Ctrl + 0` | Reset zoom to 100% |
| `F11` | Toggle fullscreen |

### Vim Mode Commands

| Key / Command | Action |
| :--- | :--- |
| `:` | Open statusline command prompt |
| `o` | Prompt for URL / search navigation |
| `t` | Prompt for new tab URL |
| `d` | Close active tab |
| `J` / `K` | Switch to next / previous tab |
| `r` / `R` | Reload page / Hard reload |
| `yy` | Copy current page URL to system clipboard |
| `H` / `L` | Navigate back / forward in history |
| `Escape` | Close command prompt or exit Vim mode |

---

## Installation and Execution

### System Requirements

- Linux (x86_64) or Windows 10/11 (x86_64)
- Python 3.10+
- Qt6 libraries and Qt6 WebEngine

### Quick Launch

The executable wrappers `crux` and `crux-browser` (along with `zephyrium` and `zinc` symlinks) are installed in `~/.local/bin/`:

```bash
# Launch in default Minimal mode:
crux

# Open specific URL:
crux https://wiki.archlinux.org

# Launch in specific mode:
crux --mode minimal
crux --mode vim

# Launch inside an isolated container:
crux --container dev https://github.com
```

### Running from Source

```bash
git clone https://github.com/qualbyy/crux.git
cd crux
./run.sh
```

---

## Configuration Files

All configuration data is stored strictly within the user directory in accordance with the XDG Base Directory Specification:

- Configuration & Settings: `~/.config/crux/settings.json`
- AdBlock Whitelist: `~/.config/crux/adblock_whitelist.json`
- Password Vault: `~/.config/crux/passwords.json`
- Cookies Store: `~/.config/crux/cookies.json`
- Bookmarks: `~/.config/crux/bookmarks.json`
- History: `~/.config/crux/history.json`
- Container Profiles: `~/.config/crux/profiles/`
- User Custom CSS: `~/.config/crux/custom.qss`

---

## Release Notes (v1.3.6)

Crux 1.3.6 brings full project rebranding, critical stability hardening, expanded AI provider capabilities, and enhanced keyboard and container controls:

- **Crux Rebranding & Geometric Purple Aesthetics**: Elegant geometric star icon, default Crux Purple accent (`#a855f7`), and unified `crux://` internal navigation.
- **Primary Browser Menu (`☰`)**: Clean compact browser dropdown menu replacing the settings button, grouping Reader Mode, Picture-in-Picture, Tab orientation toggle, Layout modes (Minimal / Vim), Keybindings cheat sheet, and Command Palette shortcuts with Preferences at the bottom.
- **Multi-Account Containers UI**: Dedicated Containers section in Settings (`[10] CONTAINERS`), dropdown and right-click menu on `+ NEW TAB` to launch into any container, and tab context menu `Reopen in Container...` to migrate existing tabs between isolated profiles.
- **DevTools Resizing, Theme & Tab Tracking**: DevTools dock is embedded in a vertical `QSplitter` with drag handle for smooth resizing; automatically binds to whatever tab is currently active; context menu "Inspect Element" opens and focuses DevTools; fixed close button and dark theme styling.
- **Ollama Local LLM Support**: Automatic local Ollama detection on `http://localhost:11434`, provider switcher `[GEMINI / OLLAMA]` in AI sidebar, dynamic model population (`llama3`, `mistral`, `deepseek-r1`), in-settings connection test, and CLI commands (`/provider`, `/ollama`, `/gemini`).
- **Tab Hibernation Safety & URL Restoration**: Active tabs cannot be put to sleep (guarding against crashes from UI, hotkeys, and task manager); waking tabs restores original URL and title without leaking `data:text/html` into the omnibar.
- **Ephemeral Incognito Mode**: Fully isolated in-memory `QWebEngineProfile` instances for incognito windows and tabs, avoiding persistent SQLite/LevelDB disk locks.
- **Userscript Safety**: Non-blocking asynchronous install prompt for `.user.js` files, preventing download engine deadlocks and crashes.
- **Smart System File Manager**: Linux directory opener prefers native file managers (`dolphin`, `nautilus`, `thunar`) over disk analyzer Filelight.
- **Task Manager Redesign**: `crux://tasks` redesigned in Claude Code Minimal Dark aesthetic with live statistics cards and disabled suspension for active tabs.
- **Google Account Autofill**: Multi-step SPA login compatibility for Google authentication with password vault integration.

---

## Author & Contacts

- **Author:** qualbyy
- **Email:** qualbyy@gmail.com 

---

*Developed with the assistance of Gemini 3.8 Flash.*
