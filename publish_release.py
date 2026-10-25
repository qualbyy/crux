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
TAG = "v1.0.1"
TITLE = "Zephyrium v1.0.1 — Fullscreen Video Support & UI Refinements"

BODY = """## Zephyrium v1.0.1 — Минорный релиз

Обновление легковесного веб-браузера **Zephyrium** с полноценной поддержкой HTML5 Fullscreen API для YouTube, видеоплееров и улучшениями интерфейса.

### 🎬 Что нового в v1.0.1:
- **Поддержка полноэкранного режима HTML5 (YouTube / видеоплееры)**:
  - Активирован атрибут `FullScreenSupportEnabled` в настройках движка Chromium.
  - Реализован перехватчик сигнала `page.fullScreenRequested(request)`: при клике на иконку полного экрана браузер переходит в настоящий полноэкранный режим с автоматическим скрытием системных панелей навигации, вкладок и бокового сайдбара.
  - Поддержка горячих клавиш `Escape` и `F11` для выхода и переключения полноэкранного режима.
- **Улучшения интерфейса и AI-чата**:
  - Скроллируемый выпадающий список выбора AI-моделей в боковой панели (до 10 строк с моноширинным скроллбаром).
  - Улучшенный алгоритм автозаполнения форм авторизации с фильтрацией поисковых строк и поддержкой двухэтапного входа Google.
  - Защита хранилища паролей с системной проверкой sudo.

### 📦 Установка и запуск (Linux x86_64):
```bash
tar -xzf zephyrium-v1.0.1-linux-x86_64.tar.gz
./zephyrium/zephyrium
```
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
    skip_large = "--skip-large-asset" in sys.argv
    upload_large = "--upload-large-asset" in sys.argv

    print("1. Creating GitHub Release v1.0.1...")
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
    release_url = release.get("html_url")
    print(f"Release created: {release_url}")
    upload_url = release["upload_url"]
    base_upload_url = upload_url.split("{")[0]

    dist_dir = Path(__file__).resolve().parent / "dist"
    archive_file = dist_dir / "zephyrium-v1.0.1-linux-x86_64.tar.gz"
    sha_file = dist_dir / "zephyrium-v1.0.1-linux-x86_64.tar.gz.sha256"

    # Upload SHA256 checksum first
    if sha_file.exists():
        print("2. Uploading sha256 checksum...")
        upload_asset(upload_url, sha_file, "text/plain")

    archive_name = archive_file.name
    curl_command = (
        f'curl -L -X POST \\\n'
        f'  -H "Authorization: token {TOKEN}" \\\n'
        f'  -H "Content-Type: application/gzip" \\\n'
        f'  --data-binary @dist/{archive_name} \\\n'
        f'  "{base_upload_url}?name={archive_name}"'
    )

    if upload_large and archive_file.exists():
        print("3. Uploading large release archive...")
        upload_asset(upload_url, archive_file, "application/gzip")
    else:
        print("\n" + "=" * 70)
        print("Команда для быстрой самостоятельной загрузки большого архива без VPN:")
        print("=" * 70)
        print(curl_command)
        print("=" * 70)

    print(f"\nSUCCESS! Release URL: {release_url}")

if __name__ == "__main__":
    main()
