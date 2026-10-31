<p align="center">
  <img src="resources/sonde.svg" width="96" height="96" alt="Sonde Logo" />
</p>

<h1 align="center">Sonde 2.0</h1>

<p align="center">
  <strong>High-performance, lightweight, keyboard-driven web browser built with Rust, Wry & WebKitGTK.</strong>
</p>

<p align="center">
  <a href="https://github.com/qualbyy/sonde/releases"><img src="https://img.shields.io/github/v/release/qualbyy/sonde?color=d4a373&label=Release&style=flat-square" alt="Latest Release" /></a>
  <a href="https://github.com/qualbyy/sonde/actions"><img src="https://img.shields.io/github/actions/workflow/status/qualbyy/sonde/build-rust.yml?branch=rust-dev&label=CI%20Build&style=flat-square" alt="CI Status" /></a>
  <a href="https://github.com/qualbyy/sonde"><img src="https://img.shields.io/badge/Language-Rust%20%2F%20WebKitGTK-orange?style=flat-square" alt="Language" /></a>
  <a href="https://github.com/qualbyy/sonde/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue?style=flat-square" alt="License" /></a>
</p>

<p align="center">
  <a href="https://github.com/qualbyy/sonde/releases"><b>[ СКАЧАТЬ / DOWNLOAD ]</b></a> •
  <a href="https://github.com/qualbyy/sonde"><b>[ GITHUB ]</b></a> •
  <a href="https://t.me/qualbyy"><b>[ TELEGRAM ]</b></a>
</p>

---

## О браузере / Overview

**Sonde 2.0** — современный инженерный веб-браузер нового поколения, полностью переписанный на системном языке **Rust** с использованием нативного движка WebKitGTK/Wry. 

Браузер спроектирован с упором на максимальное быстродействие, нулевой оверхед по памяти, абсолютную приватность и строгий минималистичный дизайн с прямоугольной геометрией (0px border-radius), моноширинной типографикой и песочным акцентным оттенком **Desert Sand (`#d4a373`)**.

---

## Ключевые возможности / Features

- ⚡ **Нативная архитектура Rust + Wry**: Мгновенный запуск, ультра-низкое потребление ОЗУ и стабильная работа под Wayland и X11.
- 🎨 **Два режима интерфейса**:
  - **Minimal Mode**: Компактный тулбар, адаптивная строка поиска, переключаемые вертикальные (`Ctrl+Alt+T`) или горизонтальные вкладки.
  - **Vim Mode (`Ctrl+M`)**: Полноценное управление с клавиатуры без лишних графических элементов (`j`/`k` скролл, `t` новая вкладка, `x` закрыть, `r` обновить, `yy` скопировать URL, `/` поиск).
- 📱 **Продвинутый мобильный и адаптивный режим (`#viewportBar`)**:
  - Быстрые пресеты устройств (iPhone, Pixel, iPad, Desktop).
  - Числовые поля точной настройки ширины и высоты (`W:`, `H:`) с автоматическим центрированием.
  - Адаптивное меню тулбара с автоматическим скрытием кнопок в меню **`⋯`** на узких экранах.
- 🛠️ **Вкладка «Продвинутые / Для разработчиков» ([08] ADVANCED)**:
  - **Смена User-Agent на лету**: Готовые пресеты (Chrome Linux, Windows 11, macOS, Firefox, iPhone Safari, Pixel Android) и произвольный ввод.
  - **Расширения и скрипты**: Автоматическая инъекция пользовательских скриптов Violentmonkey/Greasemonkey (`.user.js`) и стилей (`.user.css`) из каталога `~/.config/sonde/scripts/`.
  - Встроенный веб-инспектор **DevTools**.
- 🤖 **Встроенный AI-ассистент**:
  - Поддержка Google Gemini (2.5 Flash, 1.5 Pro), DeepSeek V3/R1, OpenAI GPT-4o и локальных моделей через Ollama.
  - Возможность указания любой произвольной модели в поле ввода.
- 🛡️ **Блокировщик рекламы и приватность**:
  - Встроенный сетевой фильтр рекламы и трекеров с белым списком.
  - Автоматическая очистка трекинговых UTM-меток из ссылок.
  - Защищённое хранилище паролей и автозаполнение форм с подтверждением прав администратора.
- 🔄 **Проверка обновлений и облачная синхронизация**:
  - Прямая проверка релизов через GitHub Releases API с кнопкой обновления.
  - Задел под распределённую сквозную синхронизацию на базе Cloudflare Workers & D1 (в версии 2.1.0).

---

## Горячие клавиши / Keybindings

| Комбинация | Действие |
| :--- | :--- |
| `Ctrl + M` | Переключение режима интерфейса (Minimal / Vim) |
| `Ctrl + Alt + T` | Смена ориентации вкладок (Вертикальные / Горизонтальные) |
| `Ctrl + [` | Свернуть/развернуть боковую панель вкладок |
| `Ctrl + ,` | Открыть настройки браузера (`sonde://settings`) |
| `Ctrl + K` | Командная строка / палитра команд |
| `Ctrl + L` | Фокус и выделение адресной строки |
| `Ctrl + T` | Новая вкладка |
| `Ctrl + W` | Закрыть текущую вкладку |
| `Ctrl + \` | Разделить экран (Split View) |
| `Ctrl + B` | Открыть боковую панель Sonde AI |
| `Ctrl + Shift + D` | Меню и история загрузок |
| `F11` | Полноэкранный режим |

---

## Сборка и запуск / Build & Run

### 1. Быстрая сборка под Linux:
```bash
# Установка системных библиотек (Ubuntu/Debian)
sudo apt-get install -y libwebkit2gtk-4.1-dev libgtk-3-dev libsoup-3.0-dev

# Сборка бинарника и установка в ~/.local/bin/sonde
./build_linux.sh
```

### 2. Сборка под Windows (Native):
```cmd
build_windows.bat
```

### 3. Сборка под Windows через Wine (Linux):
```bash
./build_wine.sh
```

### Запуск браузера:
```bash
sonde
# или
sonde-rs
```

---

## Конфигурация и данные

Все пользовательские данные хранятся локально в `~/.config/sonde/`:
- База данных SQLite: `~/.config/sonde/sonde.db` (настройки, история, закладки, загрузки, пароли).
- Пользовательские скрипты и расширения: `~/.config/sonde/scripts/`.

---

<p align="center">
  <sub>Sonde Browser Project • Developed by <a href="https://github.com/qualbyy">qualbyy</a></sub>
</p>
