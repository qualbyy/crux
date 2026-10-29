# Crux

A lightweight, modular, engineer-focused web browser built on PyQt6-WebEngine for Linux and Windows.

Crux provides three distinct interface paradigms, isolated multi-account containers, an integrated superuser-protected password and cookie vault, native request-level content blocking, customizable color themes, and Gemini/Ollama AI inference tools without background telemetry or bloatware.

---

## Architecture and Interface Modes

Crux provides two dedicated, switchable operational paradigms:

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

Crux supports dynamic system theming without requiring application restarts:

- **Themes:** Claude Code Minimal Dark and Clean Paper Light.
- **Accent Presets:**
  - Crux Purple (`#a855f7`) — *Default*
  - Emerald Green (`#10b981`)
  - Sky Blue (`#38bdf8`)
  - Zephyrium Amber (`#fe8019`)
  - Nordic Rose (`#f43f5e`)
  - Monochrome Slate (`#94a3b8`)

Configure your appearance via Settings (`Ctrl+,`) or during initial first-launch onboarding (`crux://welcome`).

---

## Mandatory Design Code

Crux enforces a strict design code across all interface elements:

1. **Zero Emojis Policy**:
   - Strictly no graphical emojis across any menus, buttons, badges, status bars, or dialogs.
   - All indicators and badges must use clean monospace text or ASCII/geometric glyphs: `[PIN]`, `[SLEEP]`, `[BM]`, `[VOL]`, `[MUTE]`, `[SECURE]`, `[WARN]`, `[OK]`, `[+]`, `[-]`, `[x]`, `←`, `→`, `⟳`.
2. **Unified Monospace Typography**:
   - Universal font across all UI controls: `"Iosevka Nerd Font", "JetBrains Mono", monospace`.
   - Consistent font size (12px), uniform padding, and cohesive styling for all buttons and menus.
3. **Uncluttered Navigation Toolbar**:
   - Toolbar is reserved exclusively for primary controls: navigation buttons (`←`, `→`, `⟳`), security badge (`HTTPS`), omnibar URL input, and the primary dropdown menu (`MENU`).
   - Secondary tools, reading modes, layout switchers, zoom, and developer features reside cleanly inside the `MENU` dropdown.
4. **Sharp Geometry & Dark Palette**:
   - Technical aesthetic: 0px border-radius, crisp 1px borders (`#3f3f46` / `#27272a`).
   - Brand key accent: Crux Purple (`#a855f7`).

---

- **Pinned Tabs & Visual Tab Groups**: Pin tabs to protect them against accidental closure with a dedicated `[PIN]` indicator. Organize workflows into named, colored tab groups directly from the sidebar context menu.
- **Smart Omnibox URL Auto-Complete**: Dynamic search suggestions and URL auto-completion powered by local browsing history, bookmarks, and popular domains without third-party tracking.
- **Distraction-Free Reader Mode**: Clean typography, customizable aesthetic, and instant toggle (`Ctrl+Alt+R` or toolbar button) converting noisy articles into readable, minimalist layouts.
- **Picture-in-Picture (PiP)**: Pop out HTML5 videos into a persistent floating window (`Ctrl+Alt+P` or toolbar button) to watch media while working across tabs.
- **AI Quick Actions**: Selected text context menu actions (`✦ Crux AI` -> Explain, Translate to Russian, Summarize TL;DR) powered by the Google Gemini API directly inside the AI sidebar without heavy local models.
- **Custom URL Scheme Handler (`crux://`)**: Native Chromium protocol handler for internal settings, history, and downloads, ensuring 100% bug-free rendering on both Windows/Wine and Linux (with automatic aliasing for `zephyrium://`).
- **Protected Credentials Vault**: Dedicated settings tab (`04 // Passwords & Cookies`) secured by Linux `sudo` authentication. View, reveal, copy, and export stored credentials to CSV or JSON, and cookies to Netscape format.
- **Universal Browser Importer**: Automatic detection of native and Flatpak installations of Google Chrome, Chromium, Microsoft Edge, Brave, and Mozilla Firefox. Imports bookmarks, history, cookies, and login credentials, with support for CSV password imports.
- **Tab Suspension and Memory Optimization**: Background tabs automatically enter sleep mode after 20 minutes of inactivity, unloading DOM trees to conserve RAM while preserving restoration state. Manual suspension is available via tab context menu.
- **Native AdBlocker and Privacy Engine**: Interceptor-based network blocking with a persistent domain whitelist (`~/.config/crux/adblock_whitelist.json`). Automatic stripping of URL tracking parameters (`utm_*`, `fbclid`, `gclid`). SOCKS5/Tor proxy toggle (`127.0.0.1:9050`).
- **Single-Instance IPC Architecture**: A local domain socket (`crux_ipc_sock`) handles subsequent CLI invocations (`crux <url>`), passing requests to the running process without spawning redundant browser processes.
- **Dual AI Assistant (Gemini & Ollama)**: Integrated sidebar chat capable of analyzing active web page DOM contexts (`@page <query>`). Choose between Google Gemini (API key) and local Ollama (`http://localhost:11434`) models (`llama3`, `mistral`, `deepseek-r1`).
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
git clone https://github.com/qualbyy/zephyrium.git
cd zephyrium
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
- **Email:** qualbybox@gmail.com
- **GitHub:** [https://github.com/qualbyy](https://github.com/qualbyy)

---

*Developed with the assistance of Gemini 3.8 Flash.*
