#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

TOKEN = os.environ.get("GITHUB_TOKEN", "")
if not TOKEN:
    print("Error: GITHUB_TOKEN environment variable is required.")
    sys.exit(1)
REPO = "qualbyy/zephyrium"
TAG = "v1.0.0"
TITLE = "Zephyrium v1.0.0 — Minimalist Keyboard-Driven Web Browser"

BODY = """## Zephyrium v1.0.0 — Официальный релиз

Первый официальный релиз легковесного инженерного веб-браузера **Zephyrium** для Linux x86_64 в эстетике **Anthropic Minimal Dark** (квадратный дизайн, 0px border-radius, моноширинная типографика, высокая контрастность).

### 🚀 Основные возможности:
- **Эстетика и дизайн**:
  - Строгий инженерный Anthropic Minimal Dark стиль (0px скругления, 1px границы).
  - Полная поддержка русской и английской локализации интерфейса.
  - Вертикальные и горизонтальные вкладки с мгновенным переключением.
  - Живое применение настроек оформления и акцентных цветов без блокировки или перезагрузки страниц.
- **Режимы работы**:
  - **Minimal Mode**: чистый компактный интерфейс с панелью навигации и историей/загрузками во вкладках.
  - **Vim Mode**: полный минимализм без тулбаров, клавиатурная навигация (`j`/`k`/`gg`/`G`/`o`/`t`/`d`/`H`/`L`/`f`), командная строка и быстрая кнопка выхода из Vim в строке состояния.
- **Встроенный AI Assistant**:
  - Боковая панель чата с Google Gemini API.
  - Прокручиваемый список выбора моделей (`gemini-2.5-flash`, `gemini-flash-lite`, `gemini-2.5-pro`).
  - Быстрое резюмирование веб-страниц в 1 клик.
- **Хранилище паролей и автозаполнение**:
  - Локальное защищенное хранилище паролей с авторизацией по паролю sudo.
  - Продвинутый алгоритм автозаполнения логинов (с поддержкой двухэтапного входа Google и SPA).
  - Всплывающее окно сохранения учетных данных с функцией «Больше не спрашивать для этого сайта».
- **Приватность**:
  - Встроенная блокировка рекламы и трекеров.
  - Автоматическая очистка отслеживающих UTM/GCLID параметров из ссылок.

### 📦 Установка и запуск (Linux x86_64):
```bash
# Распаковать бинарный архив
tar -xzf zephyrium-v1.0.0-linux-x86_64.tar.gz

# Запустить браузер
./zephyrium/zephyrium
```

### 🔐 Контрольная сумма SHA-256:
- `zephyrium-v1.0.0-linux-x86_64.tar.gz`: `acf000e9be3a1a22827d262b158d049d42faf825bad6a3d0394a09ec67720f66`
"""

def make_request(url, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    headers.setdefault("Authorization", f"token {TOKEN}")
    headers.setdefault("User-Agent", "Zephyrium-Release-Publisher")
    headers.setdefault("Accept", "application/vnd.github+json")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return resp.getcode(), resp.read()

def upload_asset(upload_url_template, file_path, content_type="application/octet-stream"):
    base_upload_url = upload_url_template.split("{")[0]
    file_name = file_path.name
    full_url = f"{base_upload_url}?name={urllib.parse.quote(file_name)}"
    
    file_size = file_path.stat().st_size
    print(f"Uploading {file_name} ({file_size / (1024*1024):.2f} MB)...", flush=True)

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    headers = {
        "Authorization": f"token {TOKEN}",
        "User-Agent": "Zephyrium-Release-Publisher",
        "Content-Type": content_type,
        "Content-Length": str(file_size)
    }

    req = urllib.request.Request(full_url, data=file_bytes, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        print(f"Uploaded {file_name}: HTTP {resp.getcode()}", flush=True)
        return json.loads(resp.read().decode())

def main():
    print("1. Creating GitHub Release...")
    rel_payload = json.dumps({
        "tag_name": TAG,
        "target_commitish": "main",
        "name": TITLE,
        "body": BODY,
        "draft": False,
        "prerelease": False
    }).encode("utf-8")

    code, resp_bytes = make_request(
        f"https://api.github.com/repos/{REPO}/releases",
        method="POST",
        data=rel_payload,
        headers={"Content-Type": "application/json"}
    )
    release = json.loads(resp_bytes.decode())
    print(f"Release created: {release.get('html_url')}")
    upload_url = release["upload_url"]

    dist_dir = Path(__file__).resolve().parent / "dist"
    archive_file = dist_dir / "zephyrium-v1.0.0-linux-x86_64.tar.gz"
    sha_file = dist_dir / "zephyrium-v1.0.0-linux-x86_64.tar.gz.sha256"

    print("2. Uploading release archive...")
    upload_asset(upload_url, archive_file, "application/gzip")

    print("3. Uploading sha256 checksum...")
    upload_asset(upload_url, sha_file, "text/plain")

    print(f"\nSUCCESS! Release published at: {release.get('html_url')}")

if __name__ == "__main__":
    main()
