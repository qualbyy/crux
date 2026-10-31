use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
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
        .user_agent("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Crux/2.0")
        .timeout(Duration::from_secs(12))
        .redirect(reqwest::redirect::Policy::limited(10))
        .build()
    {
        Ok(c) => Arc::new(c),
        Err(e) => {
            eprintln!("[Crux Proxy] Failed to build HTTP client: {}", e);
            return;
        }
    };

    std::thread::spawn(move || {
        let addr = format!("127.0.0.1:{}", port);
        let listener = match TcpListener::bind(&addr) {
            Ok(l) => l,
            Err(e) => {
                eprintln!("[Crux Proxy] Failed to bind to {}: {}", addr, e);
                return;
            }
        };
        println!("[Crux Proxy] WebKit CSP/Frame-Bypass proxy listening on http://{}", addr);

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
    let _ = stream.set_read_timeout(Some(Duration::from_secs(10)));
    let _ = stream.set_write_timeout(Some(Duration::from_secs(15)));

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
    let mut content_length: usize = 0;
    for line in lines {
        let lower = line.to_lowercase();
        if lower.starts_with("referer:") {
            referer = Some(line[8..].trim().to_string());
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
            let body = "Crux Proxy: No target URL specified.";
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
        println!("[Crux Proxy] AdBlock blocked: {}", target);
        let resp = "HTTP/1.1 204 No Content\r\nConnection: close\r\n\r\n";
        let _ = stream.write_all(resp.as_bytes());
        return;
    }

    // Execute request via shared reqwest client
    let resp = if method == "POST" && content_length > 0 {
        // Read POST body if present
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
        client.post(&target).body(post_body).send()
    } else {
        client.get(&target).send()
    };

    let resp = match resp {
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

    let is_html = content_type.to_lowercase().contains("text/html");

    if is_html {
        let final_url = resp.url().to_string();
        let body = match resp.text() {
            Ok(t) => t,
            Err(_) => String::new(),
        };

        // Injected script for link interception, key forwarding & frame communication
        let injection = format!(
            r#"<base href="{final_url}">
<script>
(function() {{
  try {{
    window.top.postMessage({{ type: 'crux_navigated', url: {final_url_json} }}, '*');
  }} catch(e) {{}}

  // Forward keyboard events to Crux host
  window.addEventListener('keydown', function(e) {{
    try {{
      window.top.postMessage({{
        type: 'crux_key',
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
      window.top.postMessage({{ type: 'crux_click' }}, '*');
    }} catch(e) {{}}
  }}, true);

  // Intercept anchor clicks to route through proxy
  document.addEventListener('click', function(e) {{
    var a = e.target.closest('a');
    if (a && a.href && !a.href.startsWith('javascript:') && !a.href.startsWith('#')) {{
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

        let mut modified_body = body;
        if let Some(idx) = modified_body.to_lowercase().find("<head>") {
            modified_body.insert_str(idx + 6, &injection);
        } else if let Some(idx) = modified_body.to_lowercase().find("<html>") {
            modified_body.insert_str(idx + 6, &format!("<head>{}</head>", injection));
        } else {
            modified_body.insert_str(0, &injection);
        }

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

fn send_error_page(stream: &mut TcpStream, url: &str, err_msg: &str) {
    let html = format!(
        r#"<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Crux — Navigation Error</title>
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
    }}
    h1 {{
      font-size: 16px;
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
      color: #38bdf8;
      font-weight: bold;
    }}
    .btn {{
      margin-top: 18px;
      background: #a855f7;
      color: #ffffff;
      border: none;
      padding: 8px 16px;
      font-family: inherit;
      font-size: 11px;
      font-weight: bold;
      cursor: pointer;
    }}
    .btn:hover {{
      filter: brightness(1.15);
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
