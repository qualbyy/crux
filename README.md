# Zephyrium

A lightweight, modular, engineer-focused web browser built on PyQt6-WebEngine for Linux and Windows.

Zephyrium provides three distinct interface paradigms, isolated multi-account containers, an integrated superuser-protected password and cookie vault, native request-level content blocking, customizable color themes, and Gemini API inference tools without background telemetry or bloatware.

---

## Architecture and Interface Modes

Zephyrium provides two dedicated, switchable operational paradigms:

1. **Minimal Mode (Default)**
   - High-density square aesthetic with strict 0px border-radius, 1px borders, and monospace typography.
   - **Switchable Tab Orientation (`Ctrl+Alt+T`)**:
     - *Vertical Sidebar*: Fixed-width tabs on the left with color-coded container badges. Collapsible to a 50px compact icon strip (`Ctrl+[`).
     - *Horizontal Top Tabs*: Traditional horizontal tab bar positioned above the webview with crisp square close buttons.
   - Discrete status indicators and minimal navigation bar.

2. **Vim Mode**
   - Distraction-free full-window browsing. Navigation toolbar and tab strips are hidden.
   - Command input and feedback via a bottom statusline prompt (`:`).
   - Dedicated `[EXIT VIM]` corner button and `Escape` key return path to standard mode.
   - Single-key hotkeys for rapid navigation (`o`, `t`, `d`, `J`, `K`, `r`, `yy`, `H`, `L`).

Switch between modes at any time using `Ctrl+M`, the status bar mode menu, or CLI flag `--mode {minimal,vim}`.

---

## Visual Theming and Accent Colors

Zephyrium supports dynamic system theming without requiring application restarts:

- **Themes:** Claude Code Minimal Dark and Clean Paper Light.
- **Accent Presets:**
  - Zephyrium Amber (`#fe8019`)
  - Emerald Green (`#10b981`)
  - Sky Blue (`#38bdf8`)
  - Lavender Purple (`#a855f7`)
  - Nordic Rose (`#f43f5e`)
  - Monochrome Slate (`#94a3b8`)

Configure your appearance via Settings (`Ctrl+,`) or during initial first-launch onboarding (`zephyrium://welcome`).

---

- **Pinned Tabs & Visual Tab Groups**: Pin tabs to protect them against accidental closure with a dedicated `[PIN]` indicator. Organize workflows into named, colored tab groups directly from the sidebar context menu.
- **Smart Omnibox URL Auto-Complete**: Dynamic search suggestions and URL auto-completion powered by local browsing history, bookmarks, and popular domains without third-party tracking.
- **Distraction-Free Reader Mode**: Clean typography, customizable aesthetic, and instant toggle (`Ctrl+Alt+R` or toolbar button) converting noisy articles into readable, minimalist layouts.
- **Picture-in-Picture (PiP)**: Pop out HTML5 videos into a persistent floating window (`Ctrl+Alt+P` or toolbar button) to watch media while working across tabs.
- **AI Quick Actions**: Selected text context menu actions (`✦ Zephyrium AI` -> Explain, Translate to Russian, Summarize TL;DR) powered by the Google Gemini API directly inside the AI sidebar without heavy local models.
- **Custom URL Scheme Handler (`zephyrium://`)**: Native Chromium protocol handler for internal settings, history, and downloads, ensuring 100% bug-free rendering on both Windows/Wine and Linux.
- **Protected Credentials Vault**: Dedicated settings tab (`04 // Passwords & Cookies`) secured by Linux `sudo` authentication. View, reveal, copy, and export stored credentials to CSV or JSON, and cookies to Netscape format.
- **Universal Browser Importer**: Automatic detection of native and Flatpak installations of Google Chrome, Chromium, Microsoft Edge, Brave, and Mozilla Firefox. Imports bookmarks, history, cookies, and login credentials, with support for CSV password imports.
- **Tab Suspension and Memory Optimization**: Background tabs automatically enter sleep mode after 20 minutes of inactivity, unloading DOM trees to conserve RAM while preserving restoration state. Manual suspension is available via tab context menu.
- **Native AdBlocker and Privacy Engine**: Interceptor-based network blocking with a persistent domain whitelist (`~/.config/zephyrium/adblock_whitelist.json`). Automatic stripping of URL tracking parameters (`utm_*`, `fbclid`, `gclid`). SOCKS5/Tor proxy toggle (`127.0.0.1:9050`).
- **Single-Instance IPC Architecture**: A local domain socket (`zephyrium_ipc_sock`) handles subsequent CLI invocations (`zephyrium <url>`), passing requests to the running process without spawning redundant browser processes.
- **Dynamic AI Assistant (Gemini API)**: Integrated sidebar chat capable of analyzing active web page DOM contexts (`@page <query>`). Automatically fetches available models from Google Generative Language API and ranks fast models (`gemini-3.8-flash-lite`, `gemini-2.5-flash`) at the top.
- **Multilingual Support (i18n)**: Full localization engine covering 10 major languages: English, Russian, Simplified Chinese, Spanish, German, French, Japanese, Portuguese, Italian, and Turkish.
- **Wayland and Desktop Integration**: Linux process name registered as `zephyrium` via `prctl(PR_SET_NAME)`. Conforms to `StartupWMClass=zephyrium` for Waybar, Hyprland, Sway, GNOME, and KDE task managers.

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

The executable wrappers `zephyrium` and `zephyrium-browser` (along with `zinc` symlink) are installed in `~/.local/bin/`:

```bash
# Launch in default Minimal mode:
zephyrium

# Open specific URL:
zephyrium https://wiki.archlinux.org

# Launch in specific mode:
zephyrium --mode minimal
zephyrium --mode vim

# Launch inside an isolated container:
zephyrium --container dev https://github.com
```

### Running from Source

```bash
git clone https://github.com/qualbyy/zephyrium.git
cd zephyrium
./run.sh
```

---

## Configuration Files

All configuration data is stored strictly within the user directory in accordance with the XDG Base Directory Specification:

- Configuration & Settings: `~/.config/zephyrium/settings.json`
- AdBlock Whitelist: `~/.config/zephyrium/adblock_whitelist.json`
- Password Vault: `~/.config/zephyrium/passwords.json`
- Cookies Store: `~/.config/zephyrium/cookies.json`
- Bookmarks: `~/.config/zephyrium/bookmarks.json`
- History: `~/.config/zephyrium/history.json`
- Container Profiles: `~/.config/zephyrium/profiles/`
- User Custom CSS: `~/.config/zephyrium/custom.qss`

---

## Release Notes (v1.3.6)

Zephyrium 1.3.6 brings critical stability hardening, expanded AI provider capabilities, and enhanced keyboard and container controls:

- **Primary Browser Menu (`☰`)**: Clean compact browser dropdown menu replacing the settings button, grouping Reader Mode, Picture-in-Picture, Tab orientation toggle, Layout modes (Minimal / Vim), Keybindings cheat sheet, and Command Palette shortcuts with Preferences at the bottom.
- **Multi-Account Containers UI**: Dedicated Containers section in Settings (`[10] CONTAINERS`), dropdown and right-click menu on `+ NEW TAB` to launch into any container, and tab context menu `Reopen in Container...` to migrate existing tabs between isolated profiles.
- **DevTools Resizing, Theme & Tab Tracking**: DevTools dock is embedded in a vertical `QSplitter` with drag handle for smooth resizing; automatically binds to whatever tab is currently active; context menu "Inspect Element" opens and focuses DevTools; fixed close button and dark theme styling.
- **Ollama Local LLM Support**: Automatic local Ollama detection on `http://localhost:11434`, provider switcher `[GEMINI / OLLAMA]` in AI sidebar, dynamic model population (`llama3`, `mistral`, `deepseek-r1`), in-settings connection test, and CLI commands (`/provider`, `/ollama`, `/gemini`).
- **Tab Hibernation Safety & URL Restoration**: Active tabs cannot be put to sleep (guarding against crashes from UI, hotkeys, and task manager); waking tabs restores original URL and title without leaking `data:text/html` into the omnibar.
- **Ephemeral Incognito Mode**: Fully isolated in-memory `QWebEngineProfile` instances for incognito windows and tabs, avoiding persistent SQLite/LevelDB disk locks.
- **Userscript Safety**: Non-blocking asynchronous install prompt for `.user.js` files, preventing download engine deadlocks and crashes.
- **Smart System File Manager**: Linux directory opener prefers native file managers (`dolphin`, `nautilus`, `thunar`) over disk analyzer Filelight.
- **Task Manager Redesign**: `zephyrium://tasks` redesigned in Claude Code Minimal Dark aesthetic with live statistics cards and disabled suspension for active tabs.
- **Google Account Autofill**: Multi-step SPA login compatibility for Google authentication with password vault integration.

---

## Author & Contacts

- **Author:** qualbyy
- **Email:** qualbybox@gmail.com
- **GitHub:** [https://github.com/qualbyy](https://github.com/qualbyy)

---

*Developed with the assistance of Gemini 3.8 Flash.*
