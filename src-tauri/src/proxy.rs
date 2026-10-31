use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::sync::Arc;
use std::time::Duration;
use crate::adblock::AdBlocker;

fn percent_decode(input: &str) -> String {
    let mut bytes = Vec::new();
    let mut chars = input.bytes();
    while let Some(b) = chars.next() {
        if b == b'%' {
            let h1 = chars.next();
            let h2 = chars.next();
            if let (Some(h1), Some(h2)) = (h1, h2) {
                let hex_str = [h1, h2];
                if let Ok(s) = std::str::from_utf8(&hex_str) {
                    if let Ok(val) = u8::from_str_radix(s, 16) {
                        bytes.push(val);
                        continue;
                    }
                }
            }
        } else if b == b'+' {
            bytes.push(b' ');
            continue;
        }
        bytes.push(b);
    }
    String::from_utf8_lossy(&bytes).to_string()
}

fn parse_query_url(path: &str) -> Option<String> {
    if let Some(pos) = path.find("url=") {
        let after = &path[pos + 4..];
        let end = after.find('&').unwrap_or(after.len());
        let raw = &after[..end];
        let decoded = percent_decode(raw);
        if !decoded.trim().is_empty() {
            return Some(decoded.trim().to_string());
        }
    }
    None
}

pub fn start_proxy(adblocker: Arc<AdBlocker>, port: u16) {
    let client = match reqwest::blocking::Client::builder()
        .user_agent("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Sonde/2.0")
        .timeout(Duration::from_secs(15))
        .redirect(reqwest::redirect::Policy::limited(10))
        .build()
    {
        Ok(c) => Arc::new(c),
        Err(e) => {
            eprintln!("[Sonde Proxy] Failed to build HTTP client: {}", e);
            return;
        }
    };

    std::thread::spawn(move || {
        let addr = format!("127.0.0.1:{}", port);
        let listener = match TcpListener::bind(&addr) {
            Ok(l) => l,
            Err(e) => {
                eprintln!("[Sonde Proxy] Failed to bind to {}: {}", addr, e);
                return;
            }
        };
        println!("[Sonde Proxy] WebKit CSP/Frame-Bypass proxy listening on http://{}", addr);

        for stream in listener.incoming() {
            if let Ok(stream) = stream {
                let adb = Arc::clone(&adblocker);
                let cli = Arc::clone(&client);
                std::thread::spawn(move || {
                    handle_client(stream, adb, cli);
                });
            }
        }
    });
}

fn handle_client(mut stream: TcpStream, adblocker: Arc<AdBlocker>, client: Arc<reqwest::blocking::Client>) {
    let _ = stream.set_read_timeout(Some(Duration::from_secs(12)));
    let _ = stream.set_write_timeout(Some(Duration::from_secs(20)));

    let mut buf = [0u8; 8192];
    let n = match stream.read(&mut buf) {
        Ok(n) if n > 0 => n,
        _ => return,
    };

    let req_str = String::from_utf8_lossy(&buf[..n]);
    let mut lines = req_str.lines();
    let req_line = match lines.next() {
        Some(l) => l,
        None => return,
    };

    let mut parts = req_line.split_whitespace();
    let method = parts.next().unwrap_or("GET");
    let path = parts.next().unwrap_or("/");

    let mut referer: Option<String> = None;
    let mut accept_header: Option<String> = None;
    let mut cookie_header: Option<String> = None;
    let mut x_requested_with: Option<String> = None;
    let mut turbo_frame: Option<String> = None;
    let mut content_length: usize = 0;

    for line in lines {
        let lower = line.to_lowercase();
        if lower.starts_with("referer:") {
            referer = Some(line[8..].trim().to_string());
        } else if lower.starts_with("accept:") {
            accept_header = Some(line[7..].trim().to_string());
        } else if lower.starts_with("cookie:") {
            cookie_header = Some(line[7..].trim().to_string());
        } else if lower.starts_with("x-requested-with:") {
            x_requested_with = Some(line[17..].trim().to_string());
        } else if lower.starts_with("turbo-frame:") {
            turbo_frame = Some(line[12..].trim().to_string());
        } else if lower.starts_with("content-length:") {
            if let Ok(cl) = line[15..].trim().parse::<usize>() {
                content_length = cl;
            }
        }
    }

    let mut target_url: Option<String> = parse_query_url(path);

    // Fallback: If not /proxy?url=..., check if referer was a proxy request
    if target_url.is_none() {
        if let Some(ref ref_val) = referer {
            if let Some(ref_target) = parse_query_url(ref_val) {
                if let Ok(parsed_ref) = reqwest::Url::parse(&ref_target) {
                    if let Ok(joined) = parsed_ref.join(path) {
                        target_url = Some(joined.to_string());
                    }
                }
            }
        }
    }

    let target = match target_url {
        Some(t) => {
            let trimmed = t.trim();
            if trimmed.starts_with("http://") || trimmed.starts_with("https://") {
                trimmed.to_string()
            } else {
                format!("https://{}", trimmed)
            }
        }
        None => {
            let body = "Sonde Proxy: No target URL specified.";
            let resp = format!(
                "HTTP/1.1 400 Bad Request\r\nContent-Type: text/plain\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                body.len(),
                body
            );
            let _ = stream.write_all(resp.as_bytes());
            return;
        }
    };

    if adblocker.should_block(&target) {
        println!("[Sonde Proxy] AdBlock blocked: {}", target);
        let resp = "HTTP/1.1 204 No Content\r\nConnection: close\r\n\r\n";
        let _ = stream.write_all(resp.as_bytes());
        return;
    }

    // Build forwarded request with appropriate client headers
    let mut req_builder = if method == "POST" && content_length > 0 {
        let header_end = req_str.find("\r\n\r\n").map(|i| i + 4).unwrap_or(n);
        let body_in_buf = &buf[header_end..n];
        let mut post_body = body_in_buf.to_vec();
        while post_body.len() < content_length {
            let mut chunk = [0u8; 4096];
            match stream.read(&mut chunk) {
                Ok(read_n) if read_n > 0 => {
                    post_body.extend_from_slice(&chunk[..read_n]);
                }
                _ => break,
            }
        }
        client.post(&target).body(post_body)
    } else {
        client.get(&target)
    };

    if let Some(ref acc) = accept_header {
        req_builder = req_builder.header("Accept", acc);
    }
    if let Some(ref cook) = cookie_header {
        req_builder = req_builder.header("Cookie", cook);
    }
    if let Some(ref xrw) = x_requested_with {
        req_builder = req_builder.header("X-Requested-With", xrw);
    }
    if let Some(ref tf) = turbo_frame {
        req_builder = req_builder.header("Turbo-Frame", tf);
    }

    let resp = match req_builder.send() {
        Ok(r) => r,
        Err(e) => {
            send_error_page(&mut stream, &target, &format!("Failed to load web page: {}", e));
            return;
        }
    };

    let status = resp.status();
    let content_type = resp
        .headers()
        .get("content-type")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("text/html")
        .to_string();

    let content_disp = resp
        .headers()
        .get("content-disposition")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("")
        .to_string();

    // Check if this response is a file download or a userscript (.user.js)
    let is_download = content_disp.to_lowercase().contains("attachment")
        || target.ends_with(".user.js")
        || target.ends_with(".zip")
        || target.ends_with(".tar.gz")
        || target.ends_with(".deb")
        || target.ends_with(".rpm")
        || target.ends_with(".AppImage")
        || content_type.starts_with("application/octet-stream");

    if is_download {
        let final_url = resp.url().to_string();
        let bytes = match resp.bytes() {
            Ok(b) => b,
            Err(e) => {
                send_error_page(&mut stream, &target, &format!("Failed to download file: {}", e));
                return;
            }
        };

        let filename = extract_filename(&final_url, &content_disp);
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        let downloads_dir = PathBuf::from(&home).join("Downloads");
        std::fs::create_dir_all(&downloads_dir).ok();
        let target_file_path = downloads_dir.join(&filename);

        let mut saved = false;
        if let Ok(mut f) = std::fs::File::create(&target_file_path) {
            if f.write_all(&bytes).is_ok() {
                saved = true;
            }
        }

        // If it's a userscript, also save to ~/.config/sonde/scripts/
        if filename.ends_with(".user.js") {
            let scripts_dir = PathBuf::from(&home).join(".config").join("sonde").join("scripts");
            std::fs::create_dir_all(&scripts_dir).ok();
            let script_target = scripts_dir.join(&filename);
            let _ = std::fs::write(script_target, &bytes);
        }

        send_download_complete_page(&mut stream, &filename, target_file_path.to_str().unwrap_or(""), saved, bytes.len());
        return;
    }

    let is_html = content_type.to_lowercase().contains("text/html");

    if is_html {
        let final_url = resp.url().to_string();
        let body = match resp.text() {
            Ok(t) => t,
            Err(_) => String::new(),
        };

        let body_lower = body.to_lowercase();
        let is_full_document = body_lower.contains("<head") || body_lower.contains("<html");

        let modified_body = if is_full_document {
            // Injected script for link interception, key forwarding & frame communication
            let injection = format!(
                r#"<base href="{final_url}">
<script>
(function() {{
  try {{
    window.top.postMessage({{ type: 'sonde_navigated', url: {final_url_json} }}, '*');
    window.top.postMessage({{ type: 'crux_navigated', url: {final_url_json} }}, '*');
  }} catch(e) {{}}

  // Forward keyboard events to Sonde host
  window.addEventListener('keydown', function(e) {{
    try {{
      window.top.postMessage({{
        type: 'sonde_key',
        key: e.key,
        code: e.code,
        ctrlKey: e.ctrlKey,
        altKey: e.altKey,
        shiftKey: e.shiftKey,
        metaKey: e.metaKey
      }}, '*');
    }} catch(e) {{}}
  }}, true);

  // Click notification to dismiss any host popups
  window.addEventListener('click', function() {{
    try {{
      window.top.postMessage({{ type: 'sonde_click' }}, '*');
    }} catch(e) {{}}
  }}, true);

  // Link hover preview for Sonde mini bottom status bar
  document.addEventListener('mouseover', function(e) {{
    var a = e.target.closest('a');
    if (a && a.href) {{
      var targetUrl = a.href;
      if (targetUrl.indexOf('/proxy?url=') !== -1) {{
        try {{
          var u = new URL(targetUrl);
          targetUrl = decodeURIComponent(u.searchParams.get('url') || targetUrl);
        }} catch(ex) {{}}
      }}
      try {{
        window.top.postMessage({{ type: 'sonde_link_hover', url: targetUrl }}, '*');
      }} catch(ex) {{}}
    }}
  }}, true);

  document.addEventListener('mouseout', function(e) {{
    var a = e.target.closest('a');
    if (a) {{
      try {{
        window.top.postMessage({{ type: 'sonde_link_hover', url: '' }}, '*');
      }} catch(ex) {{}}
    }}
  }}, true);

  // Listen for smooth scroll messages from Vim mode
  window.addEventListener('message', function(e) {{
    if (e.data && e.data.type === 'sonde_scroll' && typeof e.data.dy === 'number') {{
      window.scrollBy({{ top: e.data.dy, behavior: 'smooth' }});
    }}
  }});

  // Intercept anchor clicks to route through proxy, ignoring in-page anchors
  document.addEventListener('click', function(e) {{
    var a = e.target.closest('a');
    if (!a) return;
    var rawHref = a.getAttribute('href') || '';
    if (rawHref.startsWith('#') || rawHref.startsWith('javascript:')) {{
      return; // Smooth in-page anchor jump
    }}
    if (a.hash && a.origin === window.location.origin && a.pathname === window.location.pathname && a.search === window.location.search) {{
      return; // In-page anchor jump
    }}
    if (a.href && !a.href.startsWith('javascript:')) {{
      e.preventDefault();
      window.location.href = 'http://127.0.0.1:39281/proxy?url=' + encodeURIComponent(a.href);
    }}
  }}, true);

  // Intercept GET form submissions
  document.addEventListener('submit', function(e) {{
    var form = e.target;
    if (form && form.action) {{
      var method = (form.method || 'get').toLowerCase();
      if (method === 'get') {{
        e.preventDefault();
        var formData = new FormData(form);
        var params = new URLSearchParams(formData).toString();
        var delim = form.action.indexOf('?') !== -1 ? '&' : '?';
        var target = form.action + delim + params;
        window.location.href = 'http://127.0.0.1:39281/proxy?url=' + encodeURIComponent(target);
      }}
    }}
  }}, true);
}})();
</script>"#,
                final_url = final_url,
                final_url_json = serde_json::to_string(&final_url).unwrap_or_else(|_| "\"\"".to_string())
            );

            let mut mod_body = body;
            if let Some(idx) = mod_body.to_lowercase().find("<head>") {
                mod_body.insert_str(idx + 6, &injection);
            } else if let Some(idx) = mod_body.to_lowercase().find("<html>") {
                mod_body.insert_str(idx + 6, &format!("<head>{}</head>", injection));
            } else {
                mod_body.insert_str(0, &injection);
            }
            mod_body
        } else {
            // Partial fragment (e.g. GitHub PJAX / Turbo Frame / contributors / releases):
            // Return raw HTML without injecting full HTML base/scripts which corrupts fragment DOM!
            body
        };

        let body_bytes = modified_body.as_bytes();
        let header = format!(
            "HTTP/1.1 {} {}\r\nContent-Type: {}\r\nContent-Length: {}\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n",
            status.as_u16(),
            status.canonical_reason().unwrap_or("OK"),
            content_type,
            body_bytes.len()
        );

        let _ = stream.write_all(header.as_bytes());
        let _ = stream.write_all(body_bytes);
    } else {
        // Binary / media / asset content: pass bytes directly
        let bytes = match resp.bytes() {
            Ok(b) => b,
            Err(_) => return,
        };

        let header = format!(
            "HTTP/1.1 {} {}\r\nContent-Type: {}\r\nContent-Length: {}\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n",
            status.as_u16(),
            status.canonical_reason().unwrap_or("OK"),
            content_type,
            bytes.len()
        );

        let _ = stream.write_all(header.as_bytes());
        let _ = stream.write_all(&bytes);
    }
}

fn extract_filename(url: &str, content_disp: &str) -> String {
    if !content_disp.is_empty() {
        if let Some(pos) = content_disp.find("filename=") {
            let sub = &content_disp[pos + 9..];
            let name = sub.trim().trim_matches('"').trim_matches('\'');
            let end = name.find(';').unwrap_or(name.len());
            let clean = name[..end].trim();
            if !clean.is_empty() {
                return clean.to_string();
            }
        }
    }
    if let Ok(u) = reqwest::Url::parse(url) {
        if let Some(segments) = u.path_segments() {
            if let Some(last) = segments.last() {
                if !last.trim().is_empty() {
                    return last.to_string();
                }
            }
        }
    }
    "download.bin".to_string()
}

fn send_download_complete_page(stream: &mut TcpStream, filename: &str, path: &str, _success: bool, size_bytes: usize) {
    let size_kb = (size_bytes as f64) / 1024.0;
    let size_str = if size_kb > 1024.0 {
        format!("{:.1} MB", size_kb / 1024.0)
    } else {
        format!("{:.1} KB", size_kb)
    };

    let is_userscript = filename.ends_with(".user.js");
    let script_badge = if is_userscript {
        "<span style=\"background:#d4a373;color:#18181b;padding:2px 6px;font-size:10px;font-weight:bold;margin-left:8px;\">USERSCRIPT INSTALLED</span>"
    } else {
        ""
    };

    let html = format!(
        r#"<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Sonde — Download Completed</title>
  <style>
    body {{
      background: #18181b;
      color: #f5f5f0;
      font-family: 'JetBrains Mono', 'Iosevka Nerd Font', monospace;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      padding: 20px;
      box-sizing: border-box;
      text-align: center;
    }}
    .box {{
      max-width: 620px;
      width: 100%;
      border: 1px solid #3f3f46;
      background: #262624;
      padding: 32px 24px;
      border-radius: 0;
    }}
    h1 {{
      font-size: 15px;
      color: #10b981;
      margin-bottom: 12px;
      letter-spacing: 1px;
      text-transform: uppercase;
    }}
    .file-name {{
      color: #d4a373;
      font-weight: bold;
      font-size: 14px;
      word-break: break-all;
      margin: 12px 0 6px 0;
    }}
    .path {{
      font-size: 11px;
      color: #a1a1aa;
      word-break: break-all;
      margin-bottom: 20px;
    }}
    .btn-row {{
      display: flex;
      gap: 10px;
      justify-content: center;
      margin-top: 20px;
    }}
    .btn {{
      background: #d4a373;
      color: #18181b;
      border: none;
      padding: 8px 16px;
      font-family: inherit;
      font-size: 11px;
      font-weight: bold;
      cursor: pointer;
    }}
    .btn-sec {{
      background: #2d2d2a;
      color: #f5f5f0;
      border: 1px solid #3f3f46;
      padding: 8px 16px;
      font-family: inherit;
      font-size: 11px;
      font-weight: bold;
      cursor: pointer;
    }}
    .btn:hover {{ filter: brightness(1.1); }}
    .btn-sec:hover {{ border-color: #d4a373; color: #d4a373; }}
  </style>
</head>
<body>
  <div class="box">
    <h1>DOWNLOAD COMPLETED {}</h1>
    <div class="file-name">{}</div>
    <div class="path">Saved to: {} ({})</div>
    <div class="btn-row">
      <button class="btn" onclick="openFile()">OPEN FILE</button>
      <button class="btn-sec" onclick="openFolder()">OPEN DOWNLOADS FOLDER</button>
      <button class="btn-sec" onclick="history.back()">GO BACK</button>
    </div>
  </div>
  <script>
    function openFile() {{
      if (window.parent && window.parent !== window) {{
        window.parent.postMessage({{ type: 'crux_cmd', url: 'sonde://action/open-file?path=' + encodeURIComponent({path_json}) }}, '*');
      }}
    }}
    function openFolder() {{
      if (window.parent && window.parent !== window) {{
        window.parent.postMessage({{ type: 'crux_cmd', url: 'sonde://action/open-downloads-folder' }}, '*');
      }}
    }}
    // Notify host about completed download
    if (window.parent && window.parent !== window) {{
      window.parent.postMessage({{
        type: 'sonde_download_complete',
        filename: {filename_json},
        path: {path_json},
        size: {size_bytes}
      }}, '*');
    }}
  </script>
</body>
</html>"#,
        script_badge,
        filename,
        path,
        size_str,
        path_json = serde_json::to_string(path).unwrap_or_else(|_| "\"\"".to_string()),
        filename_json = serde_json::to_string(filename).unwrap_or_else(|_| "\"\"".to_string()),
        size_bytes = size_bytes
    );

    let resp = format!(
        "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: {}\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n{}",
        html.len(),
        html
    );
    let _ = stream.write_all(resp.as_bytes());
}

fn send_error_page(stream: &mut TcpStream, url: &str, err_msg: &str) {
    let html = format!(
        r#"<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Sonde — Navigation Error</title>
  <style>
    body {{
      background: #18181b;
      color: #f5f5f0;
      font-family: 'JetBrains Mono', 'Iosevka Nerd Font', monospace;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      padding: 20px;
      box-sizing: border-box;
      text-align: center;
    }}
    .box {{
      max-width: 600px;
      border: 1px solid #3f3f46;
      background: #262624;
      padding: 30px;
      border-radius: 0;
    }}
    h1 {{
      font-size: 15px;
      color: #ef4444;
      margin-bottom: 12px;
      text-transform: uppercase;
      letter-spacing: 1px;
    }}
    p {{
      font-size: 12px;
      color: #a1a1aa;
      line-height: 1.6;
      margin: 8px 0;
      word-break: break-all;
    }}
    .url {{
      color: #d4a373;
      font-weight: bold;
    }}
    .btn {{
      margin-top: 18px;
      background: #d4a373;
      color: #18181b;
      border: none;
      padding: 8px 16px;
      font-family: inherit;
      font-size: 11px;
      font-weight: bold;
      cursor: pointer;
    }}
    .btn:hover {{
      filter: brightness(1.1);
    }}
  </style>
</head>
<body>
  <div class="box">
    <h1>Unable to Load Web Page</h1>
    <p>Target: <span class="url">{}</span></p>
    <p>Error: {}</p>
    <button class="btn" onclick="location.reload()">TRY AGAIN</button>
  </div>
</body>
</html>"#,
        url, err_msg
    );

    let resp = format!(
        "HTTP/1.1 502 Bad Gateway\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: {}\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n{}",
        html.len(),
        html
    );
    let _ = stream.write_all(resp.as_bytes());
}
