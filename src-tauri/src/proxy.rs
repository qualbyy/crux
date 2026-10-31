use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::sync::{Arc, Mutex, OnceLock};
use std::time::Duration;
use crate::adblock::AdBlocker;

static CURRENT_USER_AGENT: OnceLock<Mutex<String>> = OnceLock::new();

pub fn set_custom_user_agent(ua: &str) {
    let mutex = CURRENT_USER_AGENT.get_or_init(|| {
        Mutex::new("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36".to_string())
    });
    if let Ok(mut lock) = mutex.lock() {
        *lock = ua.to_string();
    }
}

pub fn get_current_user_agent() -> String {
    let mutex = CURRENT_USER_AGENT.get_or_init(|| {
        Mutex::new("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36".to_string())
    });
    mutex.lock().map(|g| g.clone()).unwrap_or_else(|_| {
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36".to_string()
    })
}


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
        let raw = &path[pos + 4..];
        let mut decoded = percent_decode(raw);
        // Recursively unwrap any nested /proxy?url=
        while let Some(inner_pos) = decoded.find("url=") {
            let inner_raw = &decoded[inner_pos + 4..];
            let inner_dec = percent_decode(inner_raw);
            if inner_dec.starts_with("http://") || inner_dec.starts_with("https://") {
                decoded = inner_dec;
            } else {
                break;
            }
        }
        let trimmed = decoded.trim().to_string();
        if !trimmed.is_empty() {
            return Some(trimmed);
        }
    }
    None
}

pub fn start_proxy(adblocker: Arc<AdBlocker>, port: u16) {
    let client = match reqwest::blocking::Client::builder()
        .user_agent("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        .timeout(Duration::from_secs(60))
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

    if method == "OPTIONS" {
        let resp = "HTTP/1.1 204 No Content\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD\r\nAccess-Control-Allow-Headers: *\r\nAccess-Control-Allow-Credentials: true\r\nAccess-Control-Max-Age: 86400\r\nConnection: close\r\n\r\n";
        let _ = stream.write_all(resp.as_bytes());
        return;
    }

    let mut forwarded_headers: Vec<(String, String)> = Vec::new();
    let mut referer: Option<String> = None;
    let mut content_length: usize = 0;

    for line in lines {
        if let Some(colon) = line.find(':') {
            let key = line[..colon].trim();
            let val = line[colon + 1..].trim();
            let key_lower = key.to_lowercase();

            if key_lower == "host" || key_lower == "connection" || key_lower == "accept-encoding" || key_lower == "user-agent" {
                continue;
            }
            if key_lower == "referer" {
                referer = Some(val.to_string());
                let unproxied = parse_query_url(val).unwrap_or_else(|| val.to_string());
                forwarded_headers.push(("Referer".to_string(), unproxied));
                continue;
            }
            if key_lower == "content-length" {
                if let Ok(cl) = val.parse::<usize>() {
                    content_length = cl;
                }
            }
            forwarded_headers.push((key.to_string(), val.to_string()));
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
            let mut normalized = if trimmed.starts_with("http://") || trimmed.starts_with("https://") {
                trimmed.to_string()
            } else {
                format!("https://{}", trimmed)
            };

            // Fix broken URLs where query parameter starts with & instead of ? (e.g. https://youtube.com&themeRefresh=1)
            if let Some(scheme_pos) = normalized.find("://") {
                let rest = &normalized[scheme_pos + 3..];
                if !rest.contains('?') {
                    if let Some(amp_pos) = rest.find('&') {
                        let slash_pos = rest.find('/');
                        if slash_pos.is_none() || amp_pos < slash_pos.unwrap() {
                            let fixed_idx = scheme_pos + 3 + amp_pos;
                            let mut fixed = normalized.clone();
                            fixed.replace_range(fixed_idx..fixed_idx + 1, "/?");
                            normalized = fixed;
                        }
                    }
                }
            }

            normalized
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

    let req_method = match method {
        "POST" => reqwest::Method::POST,
        "PUT" => reqwest::Method::PUT,
        "DELETE" => reqwest::Method::DELETE,
        "PATCH" => reqwest::Method::PATCH,
        "HEAD" => reqwest::Method::HEAD,
        _ => reqwest::Method::GET,
    };

    let mut req_builder = client.request(req_method, &target);

    if (method == "POST" || method == "PUT" || method == "PATCH") && content_length > 0 {
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
        req_builder = req_builder.body(post_body);
    }

    if let Ok(target_u) = reqwest::Url::parse(&target) {
        if let Some(host) = target_u.host_str() {
            let scheme = target_u.scheme();
            let port_str = target_u.port().map(|p| format!(":{}", p)).unwrap_or_default();
            req_builder = req_builder.header("Origin", format!("{}://{}{}", scheme, host, port_str));
        }
    }

    let active_ua = get_current_user_agent();
    req_builder = req_builder.header("User-Agent", active_ua);

    for (k, v) in forwarded_headers {
        req_builder = req_builder.header(&k, &v);
    }

    let resp = match req_builder.send() {
        Ok(r) => r,
        Err(e) => {
            send_error_page(&mut stream, &target, &format!("Failed to load web page: {}", e));
            return;
        }
    };

    let status = resp.status();
    let resp_headers = resp.headers().clone();

    let content_type = resp_headers
        .get("content-type")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("text/html")
        .to_string();

    let content_disp = resp_headers
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

    if !is_html {
        // Stream media / video / binary responses with Range & 206 Partial Content support
        let mut header = format!(
            "HTTP/1.1 {} {}\r\nContent-Type: {}\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: *\r\nAccess-Control-Allow-Headers: *\r\nAccess-Control-Allow-Credentials: true\r\nAccess-Control-Expose-Headers: *\r\nConnection: close\r\n",
            status.as_u16(),
            status.canonical_reason().unwrap_or("OK"),
            content_type
        );
        if let Some(cr) = resp_headers.get("content-range").and_then(|v| v.to_str().ok()) {
            header.push_str(&format!("Content-Range: {}\r\n", cr));
        }
        if let Some(ar) = resp_headers.get("accept-ranges").and_then(|v| v.to_str().ok()) {
            header.push_str(&format!("Accept-Ranges: {}\r\n", ar));
        } else {
            header.push_str("Accept-Ranges: bytes\r\n");
        }
        if let Some(cl) = resp_headers.get("content-length").and_then(|v| v.to_str().ok()) {
            header.push_str(&format!("Content-Length: {}\r\n", cl));
        }
        header.push_str("\r\n");

        let _ = stream.write_all(header.as_bytes());

        let mut reader = resp;
        let mut chunk = [0u8; 16384];
        while let Ok(read_n) = reader.read(&mut chunk) {
            if read_n == 0 { break; }
            if stream.write_all(&chunk[..read_n]).is_err() { break; }
        }
        return;
    }

    let final_url = resp.url().to_string();
    let body = match resp.text() {
        Ok(t) => t,
        Err(_) => String::new(),
    };

    let body_lower = body.to_lowercase();
    let is_full_document = body_lower.contains("<head") || body_lower.contains("<html");

    let modified_body = if is_full_document {
        // Injected script for link interception, SPA pushState tracking, key forwarding, password autofill
        let injection = format!(
            r#"<base href="{final_url}">
<script>
(function() {{
  function unwrapProxy(u) {{
    if (!u) return '';
    var idx = u.indexOf('/proxy?url=');
    if (idx !== -1) {{
      var raw = u.substring(idx + 11);
      try {{ return decodeURIComponent(raw); }} catch(ex) {{ return raw; }}
    }}
    return u;
  }}

  try {{
    window.top.postMessage({{ type: 'sonde_navigated', url: {final_url_json} }}, '*');
    window.top.postMessage({{ type: 'crux_navigated', url: {final_url_json} }}, '*');
  }} catch(e) {{}}

  // SPA Route Change Tracking (YouTube, GitHub, Twitter)
  try {{
    var origPush = history.pushState;
    history.pushState = function(state, title, url) {{
      var res = origPush.apply(this, arguments);
      if (url) {{
        try {{
          var full = new URL(url, window.location.href).href;
          window.top.postMessage({{ type: 'sonde_navigated', url: full }}, '*');
        }} catch(e) {{}}
      }}
      return res;
    }};
    var origReplace = history.replaceState;
    history.replaceState = function(state, title, url) {{
      var res = origReplace.apply(this, arguments);
      if (url) {{
        try {{
          var full = new URL(url, window.location.href).href;
          window.top.postMessage({{ type: 'sonde_navigated', url: full }}, '*');
        }} catch(e) {{}}
      }}
      return res;
    }};
    window.addEventListener('popstate', function() {{
      try {{
        window.top.postMessage({{ type: 'sonde_navigated', url: window.location.href }}, '*');
      }} catch(e) {{}}
    }});
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
      var targetUrl = unwrapProxy(a.href);
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

  // Password Detection & Save Prompt
  function findCredentials(form) {{
    var pwdInput = form ? form.querySelector('input[type="password"]') : document.querySelector('input[type="password"]');
    if (!pwdInput || !pwdInput.value) return null;
    var userInput = null;
    if (form) {{
      userInput = form.querySelector('input[type="text"], input[type="email"], input[name*="user"], input[name*="login"], input[name*="email"], input[autocomplete="username"]');
    }}
    if (!userInput) {{
      var allInputs = Array.from(document.querySelectorAll('input'));
      var pIdx = allInputs.indexOf(pwdInput);
      if (pIdx > 0) userInput = allInputs[pIdx - 1];
    }}
    return {{
      username: userInput ? userInput.value.trim() : '',
      password: pwdInput.value
    }};
  }}

  document.addEventListener('submit', function(e) {{
    try {{
      var creds = findCredentials(e.target);
      if (creds && creds.password) {{
        window.top.postMessage({{
          type: 'sonde_save_password_prompt',
          url: window.location.href,
          username: creds.username,
          password: creds.password
        }}, '*');
      }}
    }} catch(ex) {{}}
  }}, true);

  // Listen for messages from host (autofill, smooth scroll, dark mode)
  window.addEventListener('message', function(e) {{
    if (!e.data) return;
    if (e.data.type === 'sonde_scroll' && typeof e.data.dy === 'number') {{
      window.scrollBy({{ top: e.data.dy, behavior: 'smooth' }});
    }} else if (e.data.type === 'sonde_autofill_data') {{
      try {{
        var pwd = document.querySelector('input[type="password"]');
        if (pwd && !pwd.value) {{
          pwd.value = e.data.password || '';
          pwd.dispatchEvent(new Event('input', {{ bubbles: true }}));
          pwd.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
        var usr = document.querySelector('input[type="text"], input[type="email"], input[autocomplete="username"]');
        if (usr && !usr.value) {{
          usr.value = e.data.username || '';
          usr.dispatchEvent(new Event('input', {{ bubbles: true }}));
          usr.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
      }} catch(ex) {{}}
    }} else if (e.data.type === 'sonde_toggle_dark') {{
      toggleDarkMode(e.data.enabled);
    }}
  }});

  function toggleDarkMode(enable) {{
    var el = document.getElementById('sonde-dark-injected');
    if (enable) {{
      if (!el) {{
        el = document.createElement('style');
        el.id = 'sonde-dark-injected';
        el.textContent = 'html {{ filter: invert(90%) hue-rotate(180deg) !important; background-color: #121212 !important; }} img, video, iframe, canvas, svg, [style*="background-image"] {{ filter: invert(100%) hue-rotate(180deg) !important; }}';
        (document.head || document.documentElement).appendChild(el);
      }}
    }} else if (el) {{
      el.remove();
    }}
  }}

  // Intercept anchor clicks to route through proxy without breaking SPAs
  document.addEventListener('click', function(e) {{
    var a = e.target.closest('a');
    if (!a) return;
    var rawHref = a.getAttribute('href') || '';
    if (rawHref.startsWith('#') || rawHref.startsWith('javascript:')) return;
    if (a.hash && a.origin === window.location.origin && a.pathname === window.location.pathname && a.search === window.location.search) return;

    if (a.getAttribute('role') === 'button' || a.closest('ytd-compact-video-renderer, ytd-rich-item-renderer, ytd-video-renderer, [data-turbo]')) {{
      return;
    }}

    var dest = unwrapProxy(a.href);
    if (dest && (dest.startsWith('http://') || dest.startsWith('https://'))) {{
      if (!e.defaultPrevented && a.target !== '_blank') {{
        e.preventDefault();
        window.location.href = 'http://127.0.0.1:39281/proxy?url=' + encodeURIComponent(dest);
      }}
    }}
  }}, false);

  // Form submissions
  document.addEventListener('submit', function(e) {{
    var form = e.target;
    if (form && form.action) {{
      var method = (form.method || 'get').toLowerCase();
      if (method === 'get') {{
        if (e.defaultPrevented) return;
        e.preventDefault();
        var act = unwrapProxy(form.action);
        var formData = new FormData(form);
        var params = new URLSearchParams(formData).toString();
        var delim = act.indexOf('?') !== -1 ? '&' : '?';
        var finalTarget = act + (params ? delim + params : '');
        window.location.href = 'http://127.0.0.1:39281/proxy?url=' + encodeURIComponent(finalTarget);
      }}
    }}
  }}, false);
}})();
</script>"#,
            final_url = final_url,
            final_url_json = serde_json::to_string(&final_url).unwrap_or_else(|_| "\"\"".to_string())
        );

        let mut mod_body = body;

        // Auto-inject installed Userscripts (.user.js) and Userstyles (.user.css)
        let home_env = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        let scripts_dir = PathBuf::from(&home_env).join(".config").join("sonde").join("scripts");
        let mut extensions_injection = String::new();

        if let Ok(entries) = std::fs::read_dir(&scripts_dir) {
            for entry in entries.flatten() {
                let p = entry.path();
                if let Some(ext_name) = p.file_name().and_then(|n| n.to_str()) {
                    if ext_name.ends_with(".user.css") {
                        if let Ok(css) = std::fs::read_to_string(&p) {
                            extensions_injection.push_str(&format!(
                                "\n<style data-sonde-extension=\"{}\">\n{}\n</style>\n",
                                ext_name, css
                            ));
                        }
                    } else if ext_name.ends_with(".user.js") {
                        if let Ok(js) = std::fs::read_to_string(&p) {
                            extensions_injection.push_str(&format!(
                                "\n<script data-sonde-extension=\"{}\">\ntry {{\n{}\n}} catch(err) {{ console.error('[Sonde Extension {}]', err); }}\n</script>\n",
                                ext_name, js, ext_name
                            ));
                        }
                    }
                }
            }
        }

        let full_injection = format!("{}{}", injection, extensions_injection);

        if let Some(idx) = mod_body.to_lowercase().find("<head>") {
            mod_body.insert_str(idx + 6, &full_injection);
        } else if let Some(idx) = mod_body.to_lowercase().find("<html>") {
            mod_body.insert_str(idx + 6, &format!("<head>{}</head>", full_injection));
        } else {
            mod_body.insert_str(0, &full_injection);
        }
        mod_body
    } else {
        body
    };

    let body_bytes = modified_body.as_bytes();
    let header = format!(
        "HTTP/1.1 {} {}\r\nContent-Type: {}\r\nContent-Length: {}\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: *\r\nAccess-Control-Allow-Headers: *\r\nAccess-Control-Allow-Credentials: true\r\nAccess-Control-Expose-Headers: *\r\nConnection: close\r\n\r\n",
        status.as_u16(),
        status.canonical_reason().unwrap_or("OK"),
        content_type,
        body_bytes.len()
    );

    let _ = stream.write_all(header.as_bytes());
    let _ = stream.write_all(body_bytes);
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
