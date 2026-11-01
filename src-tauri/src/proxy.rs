use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::sync::{Arc, Mutex, OnceLock};
use std::time::Duration;
use crate::adblock::AdBlocker;
use crate::storage::Database;

static CURRENT_USER_AGENT: OnceLock<Mutex<String>> = OnceLock::new();
static LAST_PROXY_BASE: OnceLock<Mutex<String>> = OnceLock::new();

fn update_last_proxy_base(target: &str) {
    if let Ok(u) = reqwest::Url::parse(target) {
        if let Some(host) = u.host_str() {
            let base = format!("{}://{}/", u.scheme(), host);
            let lock = LAST_PROXY_BASE.get_or_init(|| Mutex::new(String::new()));
            if let Ok(mut g) = lock.lock() {
                *g = base;
            }
        }
    }
}

fn get_last_proxy_base() -> Option<String> {
    if let Some(lock) = LAST_PROXY_BASE.get() {
        if let Ok(g) = lock.lock() {
            if !g.is_empty() {
                return Some(g.clone());
            }
        }
    }
    None
}

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

pub fn parse_query_param(path: &str, param_name: &str) -> Option<String> {
    let key = format!("{}=", param_name);
    let mut search_from = 0;
    while let Some(pos) = path[search_from..].find(&key) {
        let abs_pos = search_from + pos;
        if abs_pos == 0 || path.as_bytes()[abs_pos - 1] == b'?' || path.as_bytes()[abs_pos - 1] == b'&' {
            let val_start = abs_pos + key.len();
            let val_end = path[val_start..].find('&').map(|p| val_start + p).unwrap_or(path.len());
            let raw = &path[val_start..val_end];
            let decoded = percent_decode(raw);
            let trimmed = decoded.trim().to_string();
            if !trimmed.is_empty() {
                return Some(trimmed);
            }
        }
        search_from = abs_pos + key.len();
    }
    None
}

fn parse_query_url(path: &str) -> Option<String> {
    if let Some(mut raw_url) = parse_query_param(path, "url") {
        while let Some(inner_pos) = raw_url.find("url=") {
            let inner_raw = &raw_url[inner_pos + 4..];
            let inner_dec = percent_decode(inner_raw);
            if inner_dec.starts_with("http://") || inner_dec.starts_with("https://") {
                raw_url = inner_dec;
            } else {
                break;
            }
        }
        let trimmed = raw_url.trim().to_string();
        if !trimmed.is_empty() {
            return Some(trimmed);
        }
    }
    None
}

pub fn parse_container_param(path: &str) -> String {
    parse_query_param(path, "container").unwrap_or_else(|| "default".to_string())
}

static CONTAINER_CLIENTS: OnceLock<Mutex<std::collections::HashMap<String, (Arc<reqwest::blocking::Client>, Arc<reqwest::cookie::Jar>)>>> = OnceLock::new();
static UPSTREAM_PROXY: OnceLock<Mutex<Option<String>>> = OnceLock::new();
static DOH_CACHE: OnceLock<Mutex<std::collections::HashMap<String, (std::net::IpAddr, std::time::Instant)>>> = OnceLock::new();
static DOH_ENABLED: OnceLock<std::sync::atomic::AtomicBool> = OnceLock::new();
static DOH_CLIENT: OnceLock<reqwest::blocking::Client> = OnceLock::new();

pub fn set_doh_enabled(enabled: bool) {
    let flag = DOH_ENABLED.get_or_init(|| std::sync::atomic::AtomicBool::new(false));
    flag.store(enabled, std::sync::atomic::Ordering::Relaxed);
    println!("[Sonde DoH] DNS-over-HTTPS status updated: enabled = {}", enabled);
}

pub fn is_doh_enabled() -> bool {
    let flag = DOH_ENABLED.get_or_init(|| std::sync::atomic::AtomicBool::new(false));
    flag.load(std::sync::atomic::Ordering::Relaxed)
}

fn get_doh_client() -> &'static reqwest::blocking::Client {
    DOH_CLIENT.get_or_init(|| {
        reqwest::blocking::Client::builder()
            .timeout(Duration::from_millis(2000))
            .build()
            .unwrap_or_default()
    })
}

pub fn doh_lookup(domain: &str) -> Option<std::net::IpAddr> {
    if !is_doh_enabled() {
        return None;
    }

    if domain == "localhost" || domain == "127.0.0.1" || domain.parse::<std::net::IpAddr>().is_ok() {
        return None;
    }

    let cache_lock = DOH_CACHE.get_or_init(|| Mutex::new(std::collections::HashMap::new()));
    if let Ok(cache) = cache_lock.lock() {
        if let Some((ip, timestamp)) = cache.get(domain) {
            if timestamp.elapsed() < Duration::from_secs(300) {
                return Some(*ip);
            }
        }
    }

    let client = get_doh_client();

    // Primary: Cloudflare DNS-over-HTTPS (1.1.1.1)
    let cf_url = format!("https://1.1.1.1/dns-query?name={}&type=A", domain);
    if let Ok(resp) = client.get(&cf_url).header("Accept", "application/dns-json").send() {
        if resp.status().is_success() {
            if let Ok(v) = resp.json::<serde_json::Value>() {
                if let Some(answers) = v.get("Answer").and_then(|a| a.as_array()) {
                    for ans in answers {
                        if let Some(data) = ans.get("data").and_then(|d| d.as_str()) {
                            if let Ok(ip) = data.parse::<std::net::IpAddr>() {
                                if let Ok(mut cache) = cache_lock.lock() {
                                    cache.insert(domain.to_string(), (ip, std::time::Instant::now()));
                                }
                                println!("[Sonde DoH] Cloudflare resolved {} -> {}", domain, ip);
                                return Some(ip);
                            }
                        }
                    }
                }
            }
        }
    }

    // Fallback: Google DNS-over-HTTPS (8.8.8.8)
    let google_url = format!("https://8.8.8.8/resolve?name={}&type=A", domain);
    if let Ok(resp) = client.get(&google_url).header("Accept", "application/dns-json").send() {
        if resp.status().is_success() {
            if let Ok(v) = resp.json::<serde_json::Value>() {
                if let Some(answers) = v.get("Answer").and_then(|a| a.as_array()) {
                    for ans in answers {
                        if let Some(data) = ans.get("data").and_then(|d| d.as_str()) {
                            if let Ok(ip) = data.parse::<std::net::IpAddr>() {
                                if let Ok(mut cache) = cache_lock.lock() {
                                    cache.insert(domain.to_string(), (ip, std::time::Instant::now()));
                                }
                                println!("[Sonde DoH] Google resolved {} -> {}", domain, ip);
                                return Some(ip);
                            }
                        }
                    }
                }
            }
        }
    }

    None
}

struct DohResolver;

impl reqwest::dns::Resolve for DohResolver {
    fn resolve(&self, name: reqwest::dns::Name) -> reqwest::dns::Resolving {
        let domain = name.as_str().to_string();
        Box::pin(async move {
            if let Some(ip) = doh_lookup(&domain) {
                let addr = std::net::SocketAddr::new(ip, 0);
                let addrs: reqwest::dns::Addrs = Box::new(std::iter::once(addr));
                Ok(addrs)
            } else {
                use std::net::ToSocketAddrs;
                let fallback = format!("{}:0", domain);
                if let Ok(iter) = fallback.to_socket_addrs() {
                    let mut addrs_vec: Vec<std::net::SocketAddr> = iter.filter(|a| a.is_ipv4()).collect();
                    if addrs_vec.is_empty() {
                        if let Ok(iter_retry) = fallback.to_socket_addrs() {
                            addrs_vec = iter_retry.collect();
                        }
                    }
                    let addrs: reqwest::dns::Addrs = Box::new(addrs_vec.into_iter());
                    Ok(addrs)
                } else {
                    Err(From::from(format!("Failed to resolve host {}", domain)))
                }
            }
        })
    }
}

fn create_http_client(proxy_url: Option<&str>) -> (Arc<reqwest::blocking::Client>, Arc<reqwest::cookie::Jar>) {
    let jar = Arc::new(reqwest::cookie::Jar::default());
    if let Ok(yt_u) = "https://www.youtube.com".parse::<reqwest::Url>() {
        jar.add_cookie_str("SOCS=CAESEwgDEgk1NDk4NjQ1MTMaAnJ1IAEaBgiA_L20Bg; Domain=.youtube.com; Path=/", &yt_u);
        jar.add_cookie_str("PREF=f4=4000000&f6=400&hl=ru&gl=RU; Domain=.youtube.com; Path=/", &yt_u);
    }
    if let Ok(yt_u2) = "https://youtube.com".parse::<reqwest::Url>() {
        jar.add_cookie_str("SOCS=CAESEwgDEgk1NDk4NjQ1MTMaAnJ1IAEaBgiA_L20Bg; Domain=.youtube.com; Path=/", &yt_u2);
        jar.add_cookie_str("PREF=f4=4000000&f6=400&hl=ru&gl=RU; Domain=.youtube.com; Path=/", &yt_u2);
    }

    let active_ua = get_current_user_agent();
    let mut builder = reqwest::blocking::Client::builder()
        .user_agent(active_ua)
        .connect_timeout(Duration::from_secs(15))
        .timeout(Duration::from_secs(35))
        .redirect(reqwest::redirect::Policy::limited(10))
        .cookie_provider(Arc::clone(&jar))
        .gzip(true)
        .brotli(true)
        .deflate(true)
        .dns_resolver(Arc::new(DohResolver));

    if let Some(p_url) = proxy_url {
        let trimmed = p_url.trim();
        if !trimmed.is_empty() {
            if let Ok(proxy) = reqwest::Proxy::all(trimmed) {
                println!("[Sonde Proxy] Configured upstream proxy: {}", trimmed);
                builder = builder.proxy(proxy);
            }
        }
    }

    let client = match builder.build() {
        Ok(c) => Arc::new(c),
        Err(e) => {
            eprintln!("[Sonde Proxy] Failed to build HTTP client with proxy, building fallback: {}", e);
            Arc::new(
                reqwest::blocking::Client::builder()
                    .connect_timeout(Duration::from_secs(15))
                    .timeout(Duration::from_secs(35))
                    .redirect(reqwest::redirect::Policy::limited(10))
                    .cookie_provider(Arc::clone(&jar))
                    .gzip(true)
                    .brotli(true)
                    .deflate(true)
                    .dns_resolver(Arc::new(DohResolver))
                    .build()
                    .unwrap(),
            )
        }
    };
    (client, jar)
}

pub fn set_network_proxy(proxy_url: &str) {
    let p_lock = UPSTREAM_PROXY.get_or_init(|| Mutex::new(None));
    if let Ok(mut g) = p_lock.lock() {
        *g = Some(proxy_url.to_string());
    }
    if let Some(map_lock) = CONTAINER_CLIENTS.get() {
        if let Ok(mut map) = map_lock.lock() {
            map.clear();
        }
    }
}

pub fn get_client_for_container(container: &str) -> (Arc<reqwest::blocking::Client>, Arc<reqwest::cookie::Jar>) {
    let map_lock = CONTAINER_CLIENTS.get_or_init(|| Mutex::new(std::collections::HashMap::new()));
    let mut map = map_lock.lock().unwrap();
    if let Some((client, jar)) = map.get(container) {
        return (Arc::clone(client), Arc::clone(jar));
    }
    let upstream = UPSTREAM_PROXY.get().and_then(|l| l.lock().ok()).and_then(|g| g.clone());
    let (client, jar) = create_http_client(upstream.as_deref());
    map.insert(container.to_string(), (Arc::clone(&client), Arc::clone(&jar)));
    (client, jar)
}

pub fn start_proxy(adblocker: Arc<AdBlocker>, db: Arc<Database>, port: u16) {
    let initial_doh = db.get_setting("doh_enabled").map(|v| v != "false").unwrap_or(false);
    set_doh_enabled(initial_doh);

    if let Some(initial_proxy) = db.get_setting("network_proxy") {
        set_network_proxy(&initial_proxy);
    }

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
                let d = Arc::clone(&db);
                std::thread::spawn(move || {
                    handle_client(stream, adb, d);
                });
            }
        }
    });
}

fn sanitize_cookie_for_local_proxy(sc: &str) -> String {
    let mut parts = Vec::new();
    let mut first = true;
    for piece in sc.split(';') {
        let trimmed = piece.trim();
        if first {
            parts.push(trimmed.to_string());
            first = false;
            continue;
        }
        let lower = trimmed.to_lowercase();
        if lower.starts_with("domain=") || lower == "secure" {
            continue;
        }
        if lower.starts_with("samesite=none") {
            parts.push("SameSite=Lax".to_string());
            continue;
        }
        parts.push(trimmed.to_string());
    }
    parts.join("; ")
}

fn handle_client(mut stream: TcpStream, adblocker: Arc<AdBlocker>, _db: Arc<Database>) {
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

    let mut forwarded_headers: Vec<(String, String)> = Vec::new();
    let mut referer: Option<String> = None;
    let mut req_origin: Option<String> = None;
    let mut content_length: usize = 0;
    let mut sec_fetch_dest: Option<String> = None;

    for line in lines {
        if line.trim().is_empty() {
            break;
        }
        if let Some(colon) = line.find(':') {
            let key = line[..colon].trim();
            let val = line[colon + 1..].trim();
            let key_lower = key.to_lowercase();

            if key_lower == "sec-fetch-dest" {
                sec_fetch_dest = Some(val.to_string());
            }

            if key_lower == "host"
                || key_lower == "connection"
                || key_lower == "accept-encoding"
                || key_lower == "user-agent"
                || key_lower == "origin"
                || key_lower.starts_with("sec-fetch-")
            {
                if key_lower == "origin" {
                    req_origin = Some(val.to_string());
                }
                continue;
            }
            if key_lower == "content-length" {
                if let Ok(cl) = val.parse::<usize>() {
                    content_length = cl;
                }
                continue;
            }
            if key_lower == "cookie" {
                let clean: String = val.chars().filter(|c| c.is_ascii() && *c >= ' ' && *c <= '~').collect();
                if !clean.is_empty() {
                    forwarded_headers.push(("Cookie".to_string(), clean));
                }
                continue;
            }
            if key_lower == "referer" {
                referer = Some(val.to_string());
                let unproxied = parse_query_url(val).unwrap_or_else(|| val.to_string());
                if !unproxied.starts_with("http://127.0.0.1") && !unproxied.starts_with("http://localhost") {
                    forwarded_headers.push(("Referer".to_string(), unproxied));
                }
                continue;
            }
            forwarded_headers.push((key.to_string(), val.to_string()));
        }
    }

    let client_origin = req_origin.as_deref().unwrap_or("http://127.0.0.1:39281");

    if path.starts_with("/__sonde_log") {
        if let Some(q_idx) = path.find("msg=") {
            let encoded = &path[q_idx + 4..];
            let clean = percent_decode(encoded);
            println!("[BROWSER-LOG] {}", clean);
        }
        let resp = "HTTP/1.1 204 No Content\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET, POST, OPTIONS\r\nAccess-Control-Allow-Headers: *\r\nConnection: close\r\n\r\n";
        let _ = stream.write_all(resp.as_bytes());
        return;
    }

    if method == "OPTIONS" {
        let resp = format!(
            "HTTP/1.1 204 No Content\r\nAccess-Control-Allow-Origin: {}\r\nAccess-Control-Allow-Methods: GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD\r\nAccess-Control-Allow-Headers: *\r\nAccess-Control-Allow-Credentials: true\r\nAccess-Control-Max-Age: 86400\r\nConnection: close\r\n\r\n",
            client_origin
        );
        let _ = stream.write_all(resp.as_bytes());
        return;
    }

    let mut target_url: Option<String> = parse_query_url(path);

    // Loop prevention & relative path un-mangling:
    if let Some(ref t) = target_url {
        if t.starts_with("http://127.0.0.1:39281") || t.starts_with("http://localhost:39281") {
            // Unloop request pointing to proxy itself
            if let Some(ref ref_val) = referer {
                let ref_target = parse_query_url(ref_val).unwrap_or_else(|| ref_val.clone());
                if let Ok(parsed_ref) = reqwest::Url::parse(&ref_target) {
                    if let Ok(bad_u) = reqwest::Url::parse(t) {
                        let rel_path = format!("{}{}", bad_u.path(), bad_u.query().map(|q| format!("?{}", q)).unwrap_or_default());
                        if let Ok(joined) = parsed_ref.join(&rel_path) {
                            target_url = Some(joined.to_string());
                        }
                    }
                }
            }
        }
    }

    // Fallback 1: If not /proxy?url=..., check if referer was a proxy request
    if target_url.is_none() {
        if let Some(ref ref_val) = referer {
            let ref_target = parse_query_url(ref_val).unwrap_or_else(|| ref_val.clone());
            if !ref_target.starts_with("http://127.0.0.1") && !ref_target.starts_with("http://localhost") {
                if let Ok(parsed_ref) = reqwest::Url::parse(&ref_target) {
                    if let Ok(joined) = parsed_ref.join(path) {
                        target_url = Some(joined.to_string());
                    }
                }
            }
        }
    }

    // Fallback 2: Check LAST_PROXY_BASE
    if target_url.is_none() {
        if let Some(base) = get_last_proxy_base() {
            if let Ok(parsed_base) = reqwest::Url::parse(&base) {
                if let Ok(joined) = parsed_base.join(path) {
                    target_url = Some(joined.to_string());
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

            update_last_proxy_base(&normalized);
            normalized
        }
        None => {
            println!("[PROXY-NO-TARGET] {} {} (Referer: {:?})", method, path, referer);
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

    let container = parse_container_param(path);
    let (client, jar) = get_client_for_container(&container);
    let mut req_builder = client.request(req_method, &target);

    if (method == "POST" || method == "PUT" || method == "PATCH") && content_length > 0 {
        let header_end = req_str.find("\r\n\r\n").map(|i| i + 4).unwrap_or(n);
        let body_in_buf = if header_end < n { &buf[header_end..n] } else { &[] };
        let mut post_body = body_in_buf.to_vec();
        if post_body.len() < content_length {
            let _ = stream.set_read_timeout(Some(Duration::from_millis(3000)));
            while post_body.len() < content_length {
                let mut chunk = [0u8; 4096];
                match stream.read(&mut chunk) {
                    Ok(read_n) if read_n > 0 => {
                        post_body.extend_from_slice(&chunk[..read_n]);
                    }
                    _ => break,
                }
            }
            let _ = stream.set_read_timeout(Some(Duration::from_secs(12)));
        }
        req_builder = req_builder.body(post_body);
    }

    if let Ok(target_u) = reqwest::Url::parse(&target) {
        let scheme = target_u.scheme();
        let host = target_u.host_str().unwrap_or("");
        let port_str = target_u.port().map(|p| format!(":{}", p)).unwrap_or_default();
        let target_origin = format!("{}://{}{}", scheme, host, port_str);

        let is_yt = host.contains("youtube.com") || host.contains("googlevideo.com") || host.contains("ytimg.com");
        let effective_origin = if is_yt {
            "https://www.youtube.com".to_string()
        } else if let Some(ref ref_val) = referer {
            if let Ok(ru) = reqwest::Url::parse(ref_val) {
                let r_scheme = ru.scheme();
                let r_host = ru.host_str().unwrap_or("");
                let r_port = ru.port().map(|p| format!(":{}", p)).unwrap_or_default();
                format!("{}://{}{}", r_scheme, r_host, r_port)
            } else {
                target_origin.clone()
            }
        } else {
            target_origin.clone()
        };

        if req_origin.is_some() || (method != "GET" && method != "HEAD") {
            req_builder = req_builder.header("Origin", effective_origin.clone());
        }

        if !forwarded_headers.iter().any(|(k, _)| k.eq_ignore_ascii_case("referer")) {
            let eff_ref = if is_yt {
                "https://www.youtube.com/".to_string()
            } else {
                format!("{}/", effective_origin)
            };
            req_builder = req_builder.header("Referer", eff_ref);
        }

        // Add any incoming cookies from WebKit into the container cookie jar
        for (k, v) in &forwarded_headers {
            if k.eq_ignore_ascii_case("cookie") {
                for piece in v.split(';') {
                    let p = piece.trim();
                    if !p.is_empty() {
                        jar.add_cookie_str(p, &target_u);
                    }
                }
            }
        }
    }

    let active_ua = get_current_user_agent();
    req_builder = req_builder.header("User-Agent", active_ua);

    for (k, v) in forwarded_headers {
        if k.eq_ignore_ascii_case("cookie") {
            continue; // Handled automatically by jar
        }
        if let Ok(header_name) = reqwest::header::HeaderName::from_bytes(k.as_bytes()) {
            if let Ok(val) = reqwest::header::HeaderValue::from_str(&v) {
                req_builder = req_builder.header(header_name, val);
            }
        }
    }

    let resp = match req_builder.send() {
        Ok(r) => r,
        Err(e) => {
            eprintln!("[Sonde Proxy Error] target={}, method={}, err={:#?}", target, method, e);
            send_error_page(&mut stream, &target, &format!("Failed to load web page: {}", e));
            return;
        }
    };

    let status = resp.status();
    if target.contains("youtube.com") || target.contains("googlevideo.com") || target.contains("ytimg.com") {
        println!("[YOUTUBE-PROXY] {} {} (Referer: {:?}, Dest: {:?}) -> {}", method, target, referer, sec_fetch_dest, status);
    }
    if target.contains("youtube.com/results") {
        println!("[YOUTUBE-DEBUG-RAW] status={}\n{}\n[END-RAW]", status, req_str);
    }
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
        let filename = extract_filename(&final_url, &content_disp);
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        let downloads_dir = PathBuf::from(&home).join("Downloads");
        std::fs::create_dir_all(&downloads_dir).ok();
        let target_file_path = downloads_dir.join(&filename);

        let mut saved = false;
        let mut total_bytes = 0usize;
        if let Ok(mut f) = std::fs::File::create(&target_file_path) {
            let mut reader = resp;
            let mut buffer = [0u8; 65536]; // 64 KB streaming buffer
            loop {
                match reader.read(&mut buffer) {
                    Ok(0) => {
                        saved = true;
                        break;
                    }
                    Ok(n) => {
                        if f.write_all(&buffer[..n]).is_err() {
                            break;
                        }
                        total_bytes += n;
                    }
                    Err(_) => break,
                }
            }
        }

        // If it's a userscript, also copy to ~/.config/sonde/scripts/
        if filename.ends_with(".user.js") && saved {
            let scripts_dir = PathBuf::from(&home).join(".config").join("sonde").join("scripts");
            std::fs::create_dir_all(&scripts_dir).ok();
            let script_target = scripts_dir.join(&filename);
            let _ = std::fs::copy(&target_file_path, &script_target);
        }

        send_download_complete_page(&mut stream, &filename, target_file_path.to_str().unwrap_or(""), saved, total_bytes);
        return;
    }

    let is_html = content_type.to_lowercase().contains("text/html");

    if !is_html {
        // Stream media / video / binary responses with Range & 206 Partial Content support
        let mut header = format!(
            "HTTP/1.1 {} {}\r\nContent-Type: {}\r\nAccess-Control-Allow-Origin: {}\r\nAccess-Control-Allow-Methods: *\r\nAccess-Control-Allow-Headers: *\r\nAccess-Control-Allow-Credentials: true\r\nAccess-Control-Expose-Headers: *\r\nConnection: close\r\n",
            status.as_u16(),
            status.canonical_reason().unwrap_or("OK"),
            content_type,
            client_origin
        );
        for sc_val in resp_headers.get_all("set-cookie") {
            if let Ok(sc_str) = sc_val.to_str() {
                let sanitized = sanitize_cookie_for_local_proxy(sc_str);
                header.push_str(&format!("Set-Cookie: {}\r\n", sanitized));
            }
        }
        if let Some(cr) = resp_headers.get("content-range").and_then(|v| v.to_str().ok()) {
            header.push_str(&format!("Content-Range: {}\r\n", cr));
        }
        if let Some(ar) = resp_headers.get("accept-ranges").and_then(|v| v.to_str().ok()) {
            header.push_str(&format!("Accept-Ranges: {}\r\n", ar));
        } else {
            header.push_str("Accept-Ranges: bytes\r\n");
        }
        if status.as_u16() == 206 {
            if let Some(cl) = resp_headers.get("content-length").and_then(|v| v.to_str().ok()) {
                header.push_str(&format!("Content-Length: {}\r\n", cl));
            }
        } else if !resp_headers.contains_key("content-encoding") {
            if let Some(cl) = resp_headers.get("content-length").and_then(|v| v.to_str().ok()) {
                header.push_str(&format!("Content-Length: {}\r\n", cl));
            }
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
  function sendLog(prefix, args) {{
    try {{
      var str = Array.prototype.slice.call(args).map(function(a) {{
        if (a instanceof Error) return (a.stack || a.message);
        if (typeof a === 'object') {{
          try {{ return JSON.stringify(a); }} catch(e) {{ return String(a); }}
        }}
        return String(a);
      }}).join(' ');
      var x = new XMLHttpRequest();
      x.open('GET', 'http://127.0.0.1:39281/__sonde_log?msg=' + encodeURIComponent(prefix + ': ' + str), true);
      x.send();
    }} catch(e) {{}}
  }}
  window.addEventListener('error', function(e) {{
    var tgt = e.target;
    if (tgt && tgt.tagName) {{
      sendLog('ELEMENT_ERR', [tgt.tagName, tgt.src || tgt.href || tgt.getAttribute('src')]);
    }} else {{
      sendLog('JS_ERR', [e.message, e.filename, e.lineno, e.colno, e.error ? (e.error.stack || e.error.message) : 'no-err-obj']);
    }}
  }}, true);
  window.addEventListener('unhandledrejection', function(e) {{
    sendLog('UNHANDLED_REJECTION', [e.reason ? (e.reason.stack || e.reason.message || e.reason) : e]);
  }}, true);
  var oLog = console.log;
  var oWarn = console.warn;
  var oErr = console.error;
  console.log = function() {{ oLog.apply(console, arguments); sendLog('LOG', arguments); }};
  console.warn = function() {{ oWarn.apply(console, arguments); sendLog('WARN', arguments); }};
  console.error = function() {{ oErr.apply(console, arguments); sendLog('ERROR', arguments); }};
  sendLog('INIT', ['Sonde proxy injected into', window.location.href]);

  var hostWindow = window.top;
  try {{
    Object.defineProperty(window, 'top', {{ get: function() {{ return window; }}, configurable: true }});
    Object.defineProperty(window, 'parent', {{ get: function() {{ return window; }}, configurable: true }});
  }} catch(e) {{}}
  var targetBase = {final_url_json};
  var targetOrigin = (function() {{
    try {{ return new URL(targetBase).origin; }} catch(e) {{ return ''; }}
  }})();
  var containerName = {container_json};

  function resolveTargetUrl(u) {{
    if (!u) return '';
    var idx = u.indexOf('/proxy?url=');
    if (idx !== -1) {{
      var raw = u.substring(idx + 11);
      var cIdx = raw.indexOf('&container=');
      if (cIdx !== -1) {{
        raw = raw.substring(0, cIdx);
      }}
      try {{ u = decodeURIComponent(raw); }} catch(ex) {{ u = raw; }}
    }}
    if (u.startsWith('http://127.0.0.1:39281') || u.startsWith('http://localhost:39281')) {{
      try {{
        var parsed = new URL(u);
        return new URL(parsed.pathname + parsed.search + parsed.hash, targetOrigin).href;
      }} catch(e) {{
        return u;
      }}
    }}
    try {{
      return new URL(u, targetBase).href;
    }} catch(e) {{
      return u;
    }}
  }}

  function unwrapProxy(u) {{
    return resolveTargetUrl(u);
  }}

  function toProxyUrl(u) {{
    if (!u) return u;
    var str = '';
    if (typeof u === 'string') {{
      str = u;
    }} else if (typeof URL !== 'undefined' && u instanceof URL) {{
      str = u.href;
    }} else if (u && typeof u.url === 'string') {{
      str = u.url;
    }} else {{
      try {{ str = String(u); }} catch(e) {{ return u; }}
    }}

    if (!str || str.startsWith('data:') || str.startsWith('blob:') || str.startsWith('javascript:') || str.indexOf('__sonde_log') !== -1) {{
      return u;
    }}
    if (str.indexOf('/proxy?url=') !== -1) {{
      return u;
    }}

    var full = resolveTargetUrl(str);
    if (full.startsWith('http://') || full.startsWith('https://')) {{
      var pUrl = 'http://127.0.0.1:39281/proxy?url=' + encodeURIComponent(full);
      if (containerName && containerName !== 'default') {{
        pUrl += '&container=' + encodeURIComponent(containerName);
      }}
      return pUrl;
    }}
    return u;
  }}

  // Hook window.fetch
  try {{
    var origFetch = window.fetch;
    if (origFetch) {{
      window.fetch = function(input, init) {{
        var rawIn = typeof input === 'string' ? input : (input && input.url ? input.url : String(input));
        sendLog('FETCH', [rawIn]);
        try {{
          if (typeof input === 'string') {{
            return origFetch.call(this, toProxyUrl(input), init);
          }} else if (typeof URL !== 'undefined' && input instanceof URL) {{
            return origFetch.call(this, toProxyUrl(input.href), init);
          }} else if (input && typeof input === 'object' && typeof input.url === 'string') {{
            var proxied = toProxyUrl(input.url);
            if (proxied !== input.url) {{
              try {{
                var reqClone = new Request(proxied, input);
                return origFetch.call(this, reqClone, init);
              }} catch(err) {{
                var reqInit = {{}};
                try {{
                  if (input.method) reqInit.method = input.method;
                  if (input.headers) reqInit.headers = input.headers;
                  if (input.credentials) reqInit.credentials = input.credentials;
                  if (input.mode && input.mode !== 'navigate') reqInit.mode = input.mode;
                  if (input.cache) reqInit.cache = input.cache;
                  if (input.body) reqInit.body = input.body;
                  if (init) Object.assign(reqInit, init);
                }} catch(e) {{}}
                return origFetch.call(this, proxied, reqInit);
              }}
            }}
          }}
        }} catch(e) {{}}
        return origFetch.apply(this, arguments);
      }};
    }}
  }} catch(e) {{}}

  // Hook XMLHttpRequest
  try {{
    var origXhrOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url, async, user, password) {{
      var rawUrl = typeof url === 'string' ? url : (url && url.href ? url.href : String(url));
      sendLog('XHR', [method, rawUrl]);
      try {{
        var proxiedUrl = url;
        if (typeof url === 'string') {{
          proxiedUrl = toProxyUrl(url);
        }} else if (typeof URL !== 'undefined' && url instanceof URL) {{
          proxiedUrl = toProxyUrl(url.href);
        }}
        return origXhrOpen.call(this, method, proxiedUrl, async !== false, user, password);
      }} catch(e) {{
        return origXhrOpen.apply(this, arguments);
      }}
    }};
  }} catch(e) {{}}

  // Hook sendBeacon
  try {{
    if (navigator.sendBeacon) {{
      var origSendBeacon = navigator.sendBeacon;
      navigator.sendBeacon = function(url, data) {{
        try {{
          return origSendBeacon.call(this, toProxyUrl(url), data);
        }} catch(e) {{
          return false;
        }}
      }};
    }}
  }} catch(e) {{}}

  // Disable ServiceWorker registration in proxy mode to prevent cache hijacking
  try {{
    if ('serviceWorker' in navigator) {{
      navigator.serviceWorker.register = function() {{
        return Promise.reject(new Error('ServiceWorker disabled in Sonde Proxy'));
      }};
    }}
  }} catch(e) {{}}

  try {{
    hostWindow.postMessage({{ type: 'sonde_navigated', url: {final_url_json} }}, '*');
    hostWindow.postMessage({{ type: 'crux_navigated', url: {final_url_json} }}, '*');
    if (document.title) {{
      hostWindow.postMessage({{ type: 'sonde_title', title: document.title }}, '*');
    }}
  }} catch(e) {{}}

  // Observe title changes for real-time tab label updates
  try {{
    var titleEl = document.querySelector('title');
    if (titleEl) {{
      var titleObs = new MutationObserver(function() {{
        if (document.title) hostWindow.postMessage({{ type: 'sonde_title', title: document.title }}, '*');
      }});
      titleObs.observe(titleEl, {{ subtree: true, characterData: true, childList: true }});
    }}
  }} catch(e) {{}}

  // SPA Route Change Tracking (YouTube, GitHub, Twitter)
  try {{
    var origPush = history.pushState;
    history.pushState = function(state, title, url) {{
      var res = origPush.apply(this, arguments);
      if (url) {{
        try {{
          var full = resolveTargetUrl(url);
          targetBase = full;
          try {{ targetOrigin = new URL(targetBase).origin; }} catch(ex) {{}}
          hostWindow.postMessage({{ type: 'sonde_navigated', url: full }}, '*');
        }} catch(e) {{}}
      }}
      return res;
    }};
    var origReplace = history.replaceState;
    history.replaceState = function(state, title, url) {{
      var res = origReplace.apply(this, arguments);
      if (url) {{
        try {{
          var full = resolveTargetUrl(url);
          targetBase = full;
          try {{ targetOrigin = new URL(targetBase).origin; }} catch(ex) {{}}
          hostWindow.postMessage({{ type: 'sonde_navigated', url: full }}, '*');
        }} catch(e) {{}}
      }}
      return res;
    }};
    window.addEventListener('popstate', function() {{
      try {{
        var full = resolveTargetUrl(window.location.href);
        targetBase = full;
        try {{ targetOrigin = new URL(targetBase).origin; }} catch(ex) {{}}
        hostWindow.postMessage({{ type: 'sonde_navigated', url: full }}, '*');
      }} catch(e) {{}}
    }});
  }} catch(e) {{}}

  // Error and diagnostic reporting to host
  window.addEventListener('error', function(e) {{
    try {{
      hostWindow.postMessage({{ type: 'sonde_log', msg: '[PAGE-ERR] ' + e.message + ' at ' + e.filename + ':' + e.lineno }}, '*');
    }} catch(ex) {{}}
  }});
  window.addEventListener('unhandledrejection', function(e) {{
    try {{
      var r = e.reason;
      var str = (r && r.stack) ? r.stack : String(r);
      hostWindow.postMessage({{ type: 'sonde_log', msg: '[PAGE-PROMISE-ERR] ' + str }}, '*');
    }} catch(ex) {{}}
  }});
  setTimeout(function() {{
    try {{
      var ytdApp = document.querySelector('ytd-app');
      var searchResults = document.querySelectorAll('ytd-video-renderer');
      var items = document.querySelectorAll('ytd-two-column-search-results-renderer');
      var skeleton = document.getElementById('home-page-skeleton');
      hostWindow.postMessage({{
        type: 'sonde_log',
        msg: '[DOM-DIAG] title=' + document.title + ', ytdApp=' + (!!ytdApp) + ', searchResults=' + searchResults.length + ', items=' + items.length + ', skeleton=' + (!!skeleton)
      }}, '*');
    }} catch(e) {{
      hostWindow.postMessage({{ type: 'sonde_log', msg: '[DOM-DIAG-ERR] ' + e.message }}, '*');
    }}
  }}, 10000);

  // Forward keyboard events to Sonde host
  window.addEventListener('keydown', function(e) {{
    try {{
      hostWindow.postMessage({{
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
      hostWindow.postMessage({{ type: 'sonde_click' }}, '*');
    }} catch(e) {{}}
  }}, true);

  // Link hover preview for Sonde mini bottom status bar
  document.addEventListener('mouseover', function(e) {{
    var a = e.target.closest('a');
    if (a && a.href) {{
      var targetUrl = unwrapProxy(a.href);
      try {{
        hostWindow.postMessage({{ type: 'sonde_link_hover', url: targetUrl }}, '*');
      }} catch(ex) {{}}
    }}
  }}, true);

  document.addEventListener('mouseout', function(e) {{
    var a = e.target.closest('a');
    if (a) {{
      try {{
        hostWindow.postMessage({{ type: 'sonde_link_hover', url: '' }}, '*');
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
        hostWindow.postMessage({{
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

  function isAlreadyDark() {{
    try {{
      var bg = '';
      if (document.body) {{
        bg = window.getComputedStyle(document.body).backgroundColor;
      }}
      if (!bg || bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent') {{
        if (document.documentElement) {{
          bg = window.getComputedStyle(document.documentElement).backgroundColor;
        }}
      }}
      if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') {{
        var m = bg.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
        if (m) {{
          var lum = 0.299 * parseInt(m[1], 10) + 0.587 * parseInt(m[2], 10) + 0.114 * parseInt(m[3], 10);
          if (lum < 130) return true;
        }}
      }}
      var meta = document.querySelector('meta[name="color-scheme"]');
      if (meta && meta.content && meta.content.indexOf('dark') !== -1) return true;
      var docEl = document.documentElement;
      if (docEl && (docEl.getAttribute('data-theme') === 'dark' || docEl.classList.contains('dark') || docEl.classList.contains('theme-dark'))) return true;
      var host = window.location.hostname.toLowerCase();
      if (host.includes('twitter.com') || host.includes('x.com')) {{
        if (document.body && (document.body.style.backgroundColor === 'rgb(0, 0, 0)' || document.body.style.backgroundColor === 'rgb(21, 32, 43)')) return true;
      }}
    }} catch(e) {{}}
    return false;
  }}

  function toggleDarkMode(enable) {{
    var el = document.getElementById('sonde-dark-injected');
    if (enable) {{
      if (isAlreadyDark()) {{
        if (el) el.remove();
        return;
      }}
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

    if (a.getAttribute('role') === 'button' || a.closest('ytd-compact-video-renderer, ytd-rich-item-renderer, ytd-video-renderer, ytd-guide-entry-renderer, yt-formatted-string, [data-turbo]')) {{
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
        var act = resolveTargetUrl(form.getAttribute('action') || form.action);
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
            final_url_json = serde_json::to_string(&final_url).unwrap_or_else(|_| "\"\"".to_string()),
            container_json = serde_json::to_string(&container).unwrap_or_else(|_| "\"default\"".to_string())
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
                            let mut matches = false;
                            let mut has_rules = false;
                            for line in js.lines() {
                                let trimmed = line.trim();
                                if trimmed.starts_with("// @match") || trimmed.starts_with("// @include") {
                                    has_rules = true;
                                    let pattern = trimmed.split_whitespace().nth(2).unwrap_or("");
                                    if pattern == "*" || pattern == "*://*/*" || pattern == "<all_urls>" {
                                        matches = true;
                                        break;
                                    }
                                    let clean = pattern.replace("*", "");
                                    if !clean.is_empty() && final_url.contains(&clean) {
                                        matches = true;
                                        break;
                                    }
                                }
                            }
                            if !has_rules || matches {
                                extensions_injection.push_str(&format!(
                                    "\n<script data-sonde-extension=\"{}\">\ntry {{\n(function() {{\n{}\n}})();\n}} catch(err) {{ console.error('[Sonde Extension {}]', err); }}\n</script>\n",
                                    ext_name, js, ext_name
                                ));
                            }
                        }
                    }
                }
            }
        }

        let full_injection = format!("{}{}", injection, extensions_injection);

        let lower = mod_body.to_lowercase();
        if let Some(head_start) = lower.find("<head") {
            if let Some(head_end) = lower[head_start..].find('>') {
                let insert_pos = head_start + head_end + 1;
                mod_body.insert_str(insert_pos, &full_injection);
            } else {
                mod_body.insert_str(0, &full_injection);
            }
        } else if let Some(html_start) = lower.find("<html") {
            if let Some(html_end) = lower[html_start..].find('>') {
                let insert_pos = html_start + html_end + 1;
                mod_body.insert_str(insert_pos, &format!("<head>{}</head>", full_injection));
            } else {
                mod_body.insert_str(0, &full_injection);
            }
        } else {
            mod_body.insert_str(0, &full_injection);
        }
        mod_body
    } else {
        body
    };

    let body_bytes = modified_body.as_bytes();
    let mut header = format!(
        "HTTP/1.1 {} {}\r\nContent-Type: {}\r\nContent-Length: {}\r\nAccess-Control-Allow-Origin: {}\r\nAccess-Control-Allow-Methods: *\r\nAccess-Control-Allow-Headers: *\r\nAccess-Control-Allow-Credentials: true\r\nAccess-Control-Expose-Headers: *\r\nConnection: close\r\n",
        status.as_u16(),
        status.canonical_reason().unwrap_or("OK"),
        content_type,
        body_bytes.len(),
        client_origin
    );
    for sc_val in resp_headers.get_all("set-cookie") {
        if let Ok(sc_str) = sc_val.to_str() {
            let sanitized = sanitize_cookie_for_local_proxy(sc_str);
            header.push_str(&format!("Set-Cookie: {}\r\n", sanitized));
        }
    }
    header.push_str("\r\n");

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
    let lower_url = url.to_lowercase();
    let lower_err = err_msg.to_lowercase();
    let is_likely_blocked = lower_url.contains("youtube.com")
        || lower_url.contains("googlevideo.com")
        || lower_url.contains("ytimg.com")
        || lower_url.contains("github.com")
        || lower_url.contains("twitter.com")
        || lower_url.contains("x.com")
        || lower_url.contains("instagram.com")
        || lower_url.contains("facebook.com")
        || lower_err.contains("timeout")
        || lower_err.contains("timedout")
        || lower_err.contains("reset")
        || lower_err.contains("connect")
        || lower_err.contains("error sending request");

    let blocked_notice = if is_likely_blocked {
        r#"<div style="background:#1f1f23; border:1px solid #d4a373; border-radius:4px; padding:14px; margin:18px 0; text-align:left; font-size:12px; line-height:1.6; color:#f5f5f0;">
          <div style="color:#d4a373; font-weight:700; margin-bottom:6px;">[ВОЗМОЖНА БЛОКИРОВКА ИЛИ СЕТЕВОЙ СБОЙ]</div>
          Соединение с сервером было сброшено или заблокировано без VPN (ТСПУ / фильтрация РКН).<br>
          <ul style="margin:8px 0 4px 18px; padding:0;">
            <li>Включите VPN или утилиту обхода замедления (GoodbyeDPI / Zapret / ByeDPI).</li>
            <li>Либо в настройках Sonde (вкладка «Дополнительно») задайте сетевой SOCKS5/HTTP прокси (например, <code>socks5://127.0.0.1:10808</code> или <code>http://127.0.0.1:10809</code>).</li>
          </ul>
        </div>"#
    } else {
        ""
    };

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
    {}
    <p>Error: {}</p>
    <button class="btn" onclick="location.reload()">TRY AGAIN</button>
  </div>
</body>
</html>"#,
        url, blocked_notice, err_msg
    );

    let resp = format!(
        "HTTP/1.1 502 Bad Gateway\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: {}\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n{}",
        html.len(),
        html
    );
    let _ = stream.write_all(resp.as_bytes());
}
