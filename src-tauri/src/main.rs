use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use tao::{
    dpi::LogicalSize,
    event::{Event, StartCause, WindowEvent},
    event_loop::{ControlFlow, EventLoopBuilder},
    window::WindowBuilder,
};
use wry::WebViewBuilder;
use serde_json::Value;

mod adblock;
mod ai;
mod proxy;
mod storage;
mod tab_manager;

use adblock::AdBlocker;
use storage::Database;
use tab_manager::TabManager;

#[derive(Debug)]
enum UserEvent {
    AiResponse(String),
    DownloadDirSelected(PathBuf),
    BookmarksLoaded(String),
    HistoryLoaded(String),
    DownloadsLoaded(String),
    SettingsLoaded(String),
    ReaderContentLoaded(String),
    AdBlockStateChanged(bool),
    VaultUnlocked(String),
    VaultAuthFailed,
    AutofillData(String),
    ExtensionsLoaded(String),
    MigrationCompleted(String),
    OpenDevTools,
    ToggleFullscreen,
    CloseWindow,
    MinimizeWindow,
    MaximizeWindow,
    DragWindow,
    NavigateUrl(String),
    CreateTab { id: u32, url: String },
    CloseTab { id: u32, new_active: Option<u32> },
    ActivateTab(u32),
    GoBack,
    GoForward,
    Reload,
    SetUiHeight(i32),
    SetZoom(f64),
    PageUrlChanged { id: u32, url: String },
    PageTitleChanged { id: u32, title: String },
    PageLoadingState { id: u32, is_loading: bool, progress: f64 },
    InternalSettingCommand(String),
    NativeKeyPress { ctrl: bool, alt: bool, shift: bool, key: String, code: String },
}

#[derive(Clone)]
struct InternalPages {
    startpage: String,
    settings: String,
    history: String,
    downloads: String,
}

fn load_tab_content(wv: &webkit2gtk::WebView, url: &str, pages: &InternalPages) {
    use webkit2gtk::WebViewExt;
    if url == "sonde://startpage" || url == "crux://startpage" || url == "about:blank" || url.is_empty() {
        wv.load_html(&pages.startpage, None);
    } else if url.starts_with("sonde://settings") || url.starts_with("crux://settings") {
        wv.load_html(&pages.settings, None);
    } else if url.starts_with("sonde://history") || url.starts_with("crux://history") {
        wv.load_html(&pages.history, None);
    } else if url.starts_with("sonde://downloads") || url.starts_with("crux://downloads") {
        wv.load_html(&pages.downloads, None);
    } else {
        let full = if url.starts_with("http://") || url.starts_with("https://") {
            url.to_string()
        } else {
            format!("https://{}", url)
        };
        wv.load_uri(&full);
    }
}

fn parse_reader_mode(url: &str, html: &str) -> serde_json::Value {
    let mut title = "Article".to_string();
    if let Some(t_start) = html.find("<title>") {
        if let Some(t_end) = html[t_start..].find("</title>") {
            title = html[t_start + 7..t_start + t_end].trim().to_string();
        }
    }

    let mut paragraphs = Vec::new();
    let mut current_pos = 0;
    while let Some(p_start) = html[current_pos..].find("<p") {
        let abs_start = current_pos + p_start;
        if let Some(tag_close) = html[abs_start..].find('>') {
            let content_start = abs_start + tag_close + 1;
            if let Some(p_end) = html[content_start..].find("</p>") {
                let p_raw = &html[content_start..content_start + p_end];
                let mut clean = String::new();
                let mut in_tag = false;
                for ch in p_raw.chars() {
                    if ch == '<' {
                        in_tag = true;
                    } else if ch == '>' {
                        in_tag = false;
                    } else if !in_tag {
                        clean.push(ch);
                    }
                }
                let clean_trimmed = clean.trim();
                if clean_trimmed.len() > 30 {
                    paragraphs.push(clean_trimmed.to_string());
                }
                current_pos = content_start + p_end + 4;
            } else {
                break;
            }
        } else {
            break;
        }
    }

    serde_json::json!({
        "url": url,
        "title": title,
        "paragraphs": paragraphs,
    })
}

fn percent_decode(input: &str) -> String {
    let mut bytes = Vec::new();
    let mut chars = input.bytes();
    while let Some(b) = chars.next() {
        if b == b'%' {
            let h1 = chars.next();
            let h2 = chars.next();
            if let (Some(c1), Some(c2)) = (h1, h2) {
                if let Ok(num) = u8::from_str_radix(&format!("{}{}", c1 as char, c2 as char), 16) {
                    bytes.push(num);
                    continue;
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

fn main() -> wry::Result<()> {
    // WebKitGTK Wayland rendering fix to prevent blank/gray screen on Linux Wayland/Hyprland
    std::env::set_var("WEBKIT_DISABLE_DMABUF_RENDERER", "1");

    // 1. Initialize SQLite Database in user config dir (~/.config/sonde)
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    let config_dir = PathBuf::from(&home).join(".config").join("sonde");
    let legacy_config = PathBuf::from(&home).join(".config").join("crux").join("crux_v2.db");
    let db_path = config_dir.join("sonde.db");

    // Data migration from legacy Crux db if present
    if !db_path.exists() && legacy_config.exists() {
        std::fs::create_dir_all(&config_dir).ok();
        std::fs::copy(&legacy_config, &db_path).ok();
        println!("[Sonde Core] Migrated database from legacy crux_v2.db to sonde.db");
    }

    let db = Arc::new(Database::init(db_path).expect("Failed to initialize SQLite database"));

    let initial_url = std::env::args().nth(1).unwrap_or_else(|| "sonde://startpage".to_string());
    let mut init_tm = TabManager::new();
    if initial_url != "sonde://startpage" {
        init_tm.set_url(1, initial_url.clone());
    }
    let tab_manager = Arc::new(Mutex::new(init_tm));
    let adblocker = Arc::new(AdBlocker::new());

    // Restore saved adblock state
    if let Some(ab_saved) = db.get_setting("adblock_enabled") {
        if ab_saved == "false" {
            adblocker.set_enabled(false);
        }
    }

    // Restore saved user agent if customized
    if let Some(ua_saved) = db.get_setting("user_agent") {
        if !ua_saved.trim().is_empty() {
            proxy::set_custom_user_agent(&ua_saved);
        }
    }

    // Start local embedded proxy on 127.0.0.1:39281 to bypass WebKit CSP & frame-ancestors
    proxy::start_proxy(Arc::clone(&adblocker), Arc::clone(&db), 39281);

    // Auto-migration on first run (passwords & cookies from Chrome/Edge/Firefox)
    let db_mig = Arc::clone(&db);
    std::thread::spawn(move || {
        if db_mig.get_setting("auto_migrated_v1").is_none() {
            println!("[Sonde Core] Initiating first-time browser passwords and cookies auto-migration...");
            let home_dir = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
            let script_path = PathBuf::from(&home_dir).join(".gemini/antigravity/scratch/zinc-browser/resources/migrate_browser_data.py");
            if script_path.exists() {
                let output = std::process::Command::new("python3")
                    .arg(&script_path)
                    .output();
                if let Ok(out) = output {
                    println!("[Sonde Core] Auto-migration result: {}", String::from_utf8_lossy(&out.stdout));
                }
            } else {
                let _ = std::process::Command::new("python3")
                    .arg("-c")
                    .arg(include_str!("../../resources/migrate_browser_data.py"))
                    .output();
            }
        }
    });

    // 3. Initialize Tao Event Loop with UserEvent support
    let event_loop = EventLoopBuilder::<UserEvent>::with_user_event().build();
    let proxy = event_loop.create_proxy();

    let window = WindowBuilder::new()
        .with_title("Sonde")
        .with_inner_size(LogicalSize::new(1280.0, 800.0))
        .with_min_inner_size(LogicalSize::new(320.0, 200.0))
        .with_decorations(false) // Frameless Minimal Dark / Sand Aesthetic
        .build(&event_loop)
        .unwrap();

    // 4. Embed UI HTML/CSS/JS Assets and Sonde Pages
    let html_content = include_str!("../../ui/index.html");
    let css_content = include_str!("../../ui/style.css");
    let js_content = include_str!("../../ui/main.js");
    let startpage_content = include_str!("../../ui/startpage.html");
    let settings_content = include_str!("../../resources/settings.html");
    let history_content = include_str!("../../resources/history.html");
    let downloads_content = include_str!("../../resources/downloads.html");

    // Escape '<' as '\\u003c' to prevent premature </script> closing by HTML tokenizer
    let startpage_escaped = serde_json::to_string(&startpage_content).unwrap_or_default().replace('<', "\\u003c");
    let settings_escaped = serde_json::to_string(&settings_content).unwrap_or_default().replace('<', "\\u003c");
    let history_escaped = serde_json::to_string(&history_content).unwrap_or_default().replace('<', "\\u003c");
    let downloads_escaped = serde_json::to_string(&downloads_content).unwrap_or_default().replace('<', "\\u003c");

    let embedded_page = html_content
        .replace(r#"<link rel="stylesheet" href="style.css">"#, &format!("<style>{}</style>", css_content))
        .replace(
            r#"<script src="main.js"></script>"#,
            &format!(
                "<script>\nwindow.SONDE_INITIAL_URL = {};\nwindow.SONDE_APP_VERSION = \"v2.0.0 // BETA\";\nwindow.SONDE_STARTPAGE_HTML = {};\nwindow.CRUX_STARTPAGE_HTML = {};\nwindow.SONDE_SETTINGS_HTML = {};\nwindow.CRUX_SETTINGS_HTML = {};\nwindow.SONDE_HISTORY_HTML = {};\nwindow.CRUX_HISTORY_HTML = {};\nwindow.SONDE_DOWNLOADS_HTML = {};\nwindow.CRUX_DOWNLOADS_HTML = {};\n{}\n</script>",
                serde_json::to_string(&initial_url).unwrap_or_default(),
                startpage_escaped, startpage_escaped, settings_escaped, settings_escaped, history_escaped, history_escaped, downloads_escaped, downloads_escaped, js_content
            ),
        );

    let tm_clone = Arc::clone(&tab_manager);
    let db_clone = Arc::clone(&db);
    let adb_clone = Arc::clone(&adblocker);
    let proxy_clone = proxy.clone();

    let mut builder = WebViewBuilder::new();
    builder = builder
        .with_html(embedded_page)
        .with_devtools(true)
        .with_ipc_handler(move |req| {
            let body = req.body();
            if let Ok(v) = serde_json::from_str::<Value>(body) {
                let cmd = v["cmd"].as_str().unwrap_or("");
                match cmd {
                    "navigate" => {
                        if let Some(url) = v["url"].as_str() {
                            if adb_clone.should_block(url) {
                                println!("[Rust AdBlock] Blocked URL: {}", url);
                                return;
                            }
                            let mut tm = tm_clone.lock().unwrap();
                            if let Some(act_id) = tm.active_id {
                                tm.set_url(act_id, url.to_string());
                            }
                            db_clone.add_history(url, "Web Page").ok();
                            println!("[Sonde Core] Navigating to: {}", url);
                            let _ = proxy_clone.send_event(UserEvent::NavigateUrl(url.to_string()));
                        }
                    }
                    "create_tab" => {
                        let id_opt = v["id"].as_u64().map(|x| x as u32);
                        let url = v["url"].as_str().unwrap_or("sonde://startpage");
                        let container = v["container"].as_str().unwrap_or("default");
                        let mut tm = tm_clone.lock().unwrap();
                        let tab = if let Some(req_id) = id_opt {
                            tm.create_tab_with_id(req_id, url.to_string(), container.to_string())
                        } else {
                            tm.create_tab(url.to_string(), container.to_string())
                        };
                        println!("[Sonde Core] Created Tab: #{} - {}", tab.id, tab.url);
                        let _ = proxy_clone.send_event(UserEvent::CreateTab { id: tab.id, url: tab.url });
                    }
                    "close_tab" => {
                        if let Some(id) = v["id"].as_u64() {
                            let mut tm = tm_clone.lock().unwrap();
                            let new_active = tm.close_tab(id as u32);
                            println!("[Sonde Core] Closed Tab: #{}", id);
                            let _ = proxy_clone.send_event(UserEvent::CloseTab { id: id as u32, new_active });
                        }
                    }
                    "activate_tab" => {
                        if let Some(id) = v["id"].as_u64() {
                            let mut tm = tm_clone.lock().unwrap();
                            tm.activate_tab(id as u32);
                            println!("[Sonde Core] Activated Tab: #{}", id);
                            let _ = proxy_clone.send_event(UserEvent::ActivateTab(id as u32));
                        }
                    }
                    "go_back" => {
                        let _ = proxy_clone.send_event(UserEvent::GoBack);
                    }
                    "go_forward" => {
                        let _ = proxy_clone.send_event(UserEvent::GoForward);
                    }
                    "reload" => {
                        let _ = proxy_clone.send_event(UserEvent::Reload);
                    }
                    "set_ui_height" => {
                        if let Some(h) = v["height"].as_i64() {
                            let _ = proxy_clone.send_event(UserEvent::SetUiHeight(h as i32));
                        }
                    }
                    "set_zoom" => {
                        if let Some(z) = v["zoom"].as_f64() {
                            let _ = proxy_clone.send_event(UserEvent::SetZoom(z));
                        }
                    }
                    "toggle_pin" => {
                        if let Some(id) = v["id"].as_u64() {
                            let mut tm = tm_clone.lock().unwrap();
                            tm.toggle_pin(id as u32);
                            println!("[Sonde Core] Toggled Pin Tab: #{}", id);
                        }
                    }
                    "toggle_mute" => {
                        if let Some(id) = v["id"].as_u64() {
                            let mut tm = tm_clone.lock().unwrap();
                            tm.toggle_mute(id as u32);
                            println!("[Sonde Core] Toggled Mute Tab: #{}", id);
                        }
                    }
                    "save_setting" => {
                        if let (Some(key), Some(value)) = (v["key"].as_str(), v["value"].as_str()) {
                            db_clone.save_setting(key, value).ok();
                            if key == "user_agent" {
                                proxy::set_custom_user_agent(value);
                            }
                            if key == "network_proxy" {
                                proxy::set_network_proxy(value);
                            }
                            println!("[Sonde Core] Saved setting: {} = {}", key, value);
                        }
                    }
                    "get_settings" => {
                        let settings = db_clone.get_all_settings();
                        if let Ok(json) = serde_json::to_string(&settings) {
                            let _ = proxy_clone.send_event(UserEvent::SettingsLoaded(json));
                        }
                    }
                    "unlock_vault" => {
                        let pwd = v["password"].as_str().unwrap_or("").to_string();
                        let p_clone = proxy_clone.clone();
                        let db_c = Arc::clone(&db_clone);
                        std::thread::spawn(move || {
                            let is_authenticated = if pwd.trim().is_empty() {
                                false
                            } else {
                                // Validate via sudo -S -v on Linux
                                let child = std::process::Command::new("sudo")
                                    .arg("-S")
                                    .arg("-v")
                                    .stdin(std::process::Stdio::piped())
                                    .stdout(std::process::Stdio::null())
                                    .stderr(std::process::Stdio::null())
                                    .spawn();
                                match child {
                                    Ok(mut c) => {
                                        if let Some(mut stdin) = c.stdin.take() {
                                            use std::io::Write;
                                            let _ = writeln!(stdin, "{}", pwd);
                                        }
                                        match c.wait() {
                                            Ok(status) => status.success(),
                                            Err(_) => true,
                                        }
                                    }
                                    Err(_) => true,
                                }
                            };

                            if is_authenticated {
                                let passwords = db_c.get_passwords().unwrap_or_default();
                                let json = serde_json::to_string(&passwords).unwrap_or_else(|_| "[]".to_string());
                                let _ = p_clone.send_event(UserEvent::VaultUnlocked(json));
                            } else {
                                let _ = p_clone.send_event(UserEvent::VaultAuthFailed);
                            }
                        });
                    }
                    "add_password" => {
                        if let (Some(u), Some(user), Some(pwd)) = (v["url"].as_str(), v["username"].as_str(), v["password"].as_str()) {
                            db_clone.add_password(u, user, pwd).ok();
                            let passwords = db_clone.get_passwords().unwrap_or_default();
                            if let Ok(json) = serde_json::to_string(&passwords) {
                                let _ = proxy_clone.send_event(UserEvent::VaultUnlocked(json));
                            }
                        }
                    }
                    "delete_password" => {
                        if let Some(id) = v["id"].as_i64() {
                            db_clone.delete_password(id).ok();
                            let passwords = db_clone.get_passwords().unwrap_or_default();
                            if let Ok(json) = serde_json::to_string(&passwords) {
                                let _ = proxy_clone.send_event(UserEvent::VaultUnlocked(json));
                            }
                        }
                    }
                    "import_passwords" => {
                        if let Some(list) = v["passwords"].as_array() {
                            let mut count = 0;
                            for item in list {
                                let u = item["url"].as_str().unwrap_or("").trim();
                                let user = item["username"].as_str().unwrap_or("").trim();
                                let pwd = item["password"].as_str().unwrap_or("").trim();
                                if !u.is_empty() && (!user.is_empty() || !pwd.is_empty()) {
                                    db_clone.add_password(u, user, pwd).ok();
                                    count += 1;
                                }
                            }
                            println!("[Sonde Core] Imported {} credentials into vault", count);
                            let passwords = db_clone.get_passwords().unwrap_or_default();
                            if let Ok(json) = serde_json::to_string(&passwords) {
                                let _ = proxy_clone.send_event(UserEvent::VaultUnlocked(json));
                            }
                        }
                    }
                    "auto_migrate_browsers" => {
                        let p_clone = proxy_clone.clone();
                        let db_m = Arc::clone(&db_clone);
                        std::thread::spawn(move || {
                            let home_dir = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
                            let script_path = PathBuf::from(&home_dir).join(".gemini/antigravity/scratch/zinc-browser/resources/migrate_browser_data.py");
                            let output = if script_path.exists() {
                                std::process::Command::new("python3").arg(&script_path).output()
                            } else {
                                std::process::Command::new("python3").arg("-c").arg(include_str!("../../resources/migrate_browser_data.py")).output()
                            };

                            let res_json = match output {
                                Ok(out) => String::from_utf8_lossy(&out.stdout).to_string(),
                                Err(e) => format!("{{\"status\":\"error\",\"message\":\"{}\"}}", e),
                            };
                            println!("[Sonde Core] Manual auto-migration result: {}", res_json);
                            let _ = p_clone.send_event(UserEvent::MigrationCompleted(res_json));

                            let passwords = db_m.get_passwords().unwrap_or_default();
                            if let Ok(json) = serde_json::to_string(&passwords) {
                                let _ = p_clone.send_event(UserEvent::VaultUnlocked(json));
                            }
                        });
                    }
                    "get_autofill" => {
                        if let Some(target_url) = v["url"].as_str() {
                            let domain = if let Ok(u) = reqwest::Url::parse(target_url) {
                                u.host_str().unwrap_or("").replace("www.", "")
                            } else {
                                target_url.replace("https://", "").replace("http://", "")
                            };
                            if !domain.is_empty() {
                                let passwords = db_clone.get_passwords().unwrap_or_default();
                                for entry in passwords {
                                    if !entry.url.is_empty() && (entry.url.to_lowercase().contains(&domain.to_lowercase()) || domain.to_lowercase().contains(&entry.url.to_lowercase())) {
                                        let json = serde_json::json!({
                                            "username": entry.username,
                                            "password": entry.password
                                        }).to_string();
                                        let _ = proxy_clone.send_event(UserEvent::AutofillData(json));
                                        break;
                                    }
                                }
                            }
                        }
                    }
                    "add_bookmark" => {
                        let url = v["url"].as_str().unwrap_or("");
                        let title = v["title"].as_str().unwrap_or("Bookmark");
                        db_clone.add_bookmark(url, title).ok();
                        println!("[Sonde Core] Added bookmark: {}", url);
                    }
                    "delete_bookmark" => {
                        if let Some(url) = v["url"].as_str() {
                            db_clone.delete_bookmark(url).ok();
                            println!("[Sonde Core] Deleted bookmark: {}", url);
                        }
                    }
                    "get_bookmarks" => {
                        if let Ok(list) = db_clone.get_bookmarks() {
                            if let Ok(json) = serde_json::to_string(&list) {
                                let _ = proxy_clone.send_event(UserEvent::BookmarksLoaded(json));
                            }
                        }
                    }
                    "get_history" => {
                        if let Ok(list) = db_clone.get_history(200) {
                            if let Ok(json) = serde_json::to_string(&list) {
                                let _ = proxy_clone.send_event(UserEvent::HistoryLoaded(json));
                            }
                        }
                    }
                    "delete_history" => {
                        if let Some(url) = v["url"].as_str() {
                            db_clone.delete_history(url).ok();
                            println!("[Sonde Core] Deleted history item: {}", url);
                        }
                    }
                    "clear_history" => {
                        db_clone.clear_history().ok();
                        println!("[Sonde Core] History cleared");
                    }
                    "get_downloads" => {
                        if let Ok(list) = db_clone.get_downloads(50) {
                            if let Ok(json) = serde_json::to_string(&list) {
                                let _ = proxy_clone.send_event(UserEvent::DownloadsLoaded(json));
                            }
                        }
                    }
                    "add_download" => {
                        if let (Some(filename), Some(url), Some(path), Some(size)) = (
                            v["filename"].as_str(),
                            v["url"].as_str(),
                            v["path"].as_str(),
                            v["size"].as_i64(),
                        ) {
                            db_clone.add_download(filename, url, path, size, "completed").ok();
                        }
                    }
                    "clear_downloads" => {
                        db_clone.clear_downloads().ok();
                        println!("[Sonde Core] Downloads cleared");
                    }
                    "open_scripts_folder" => {
                        let home_env = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
                        let scripts_dir = PathBuf::from(&home_env).join(".config").join("sonde").join("scripts");
                        std::fs::create_dir_all(&scripts_dir).ok();
                        std::process::Command::new("xdg-open").arg(&scripts_dir).spawn().ok();
                        println!("[Sonde Core] Opened scripts directory: {:?}", scripts_dir);
                    }
                    "get_extensions" => {
                        let home_env = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
                        let scripts_dir = PathBuf::from(&home_env).join(".config").join("sonde").join("scripts");
                        std::fs::create_dir_all(&scripts_dir).ok();

                        let mut userscripts = Vec::new();
                        let mut userstyles = Vec::new();

                        if let Ok(entries) = std::fs::read_dir(&scripts_dir) {
                            for entry in entries.flatten() {
                                let p = entry.path();
                                if let Some(fname) = p.file_name().and_then(|n| n.to_str()) {
                                    if fname.ends_with(".user.js") {
                                        userscripts.push(serde_json::json!({
                                            "name": fname.replace(".user.js", ""),
                                            "filename": fname,
                                            "enabled": true
                                        }));
                                    } else if fname.ends_with(".user.css") {
                                        userstyles.push(serde_json::json!({
                                            "name": fname.replace(".user.css", ""),
                                            "filename": fname,
                                            "enabled": true
                                        }));
                                    }
                                }
                            }
                        }

                        let ext_json = serde_json::json!({
                            "userscripts": userscripts,
                            "userstyles": userstyles
                        }).to_string();

                        let _ = proxy_clone.send_event(UserEvent::ExtensionsLoaded(ext_json));
                    }
                    "open_file" => {
                        if let Some(path) = v["path"].as_str() {
                            std::process::Command::new("xdg-open").arg(path).spawn().ok();
                            println!("[Sonde Core] Opened file: {}", path);
                        }
                    }
                    "open_downloads_folder" => {
                        let home_env = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
                        let dl_dir = db_clone.get_setting("download_dir").unwrap_or_else(|| format!("{}/Downloads", home_env));
                        std::process::Command::new("xdg-open").arg(dl_dir).spawn().ok();
                        println!("[Sonde Core] Opened downloads directory via xdg-open");
                    }
                    "choose_download_dir" => {
                        let p_clone = proxy_clone.clone();
                        std::thread::spawn(move || {
                            let folder = rfd::FileDialog::new()
                                .set_title("Choose Default Download Directory")
                                .pick_folder();
                            if let Some(p) = folder {
                                println!("[Sonde Core] Selected download folder: {:?}", p);
                                let _ = p_clone.send_event(UserEvent::DownloadDirSelected(p));
                            }
                        });
                    }
                    "ask_ai" => {
                        let prompt = v["prompt"].as_str().unwrap_or("").to_string();
                        let provider = v["provider"].as_str().unwrap_or("gemini").to_string();
                        let model = v["model"].as_str().unwrap_or("gemini-2.5-flash").to_string();
                        let api_key = v["api_key"].as_str().map(|s| s.to_string());
                        let p_clone = proxy_clone.clone();

                        std::thread::spawn(move || {
                            let req = ai::AiRequest {
                                provider,
                                model,
                                prompt,
                                api_key,
                            };
                            let resp = ai::query_ai(req);
                            println!("[Sonde AI] Response received: success={}", resp.success);
                            let text = if resp.success {
                                resp.reply
                            } else {
                                resp.error.unwrap_or_else(|| "No response".to_string())
                            };
                            let _ = p_clone.send_event(UserEvent::AiResponse(text));
                        });
                    }
                    "open_devtools" => {
                        let _ = proxy_clone.send_event(UserEvent::OpenDevTools);
                    }
                    "fetch_reader_content" => {
                        if let Some(url) = v["url"].as_str() {
                            let u_str = url.to_string();
                            let p_clone = proxy_clone.clone();
                            std::thread::spawn(move || {
                                let client = reqwest::blocking::Client::builder()
                                    .user_agent("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
                                    .timeout(std::time::Duration::from_secs(8))
                                    .build();
                                if let Ok(c) = client {
                                    if let Ok(resp) = c.get(&u_str).send() {
                                        if let Ok(html) = resp.text() {
                                            let parsed = parse_reader_mode(&u_str, &html);
                                            if let Ok(json) = serde_json::to_string(&parsed) {
                                                let _ = p_clone.send_event(UserEvent::ReaderContentLoaded(json));
                                            }
                                        }
                                    }
                                }
                            });
                        }
                    }
                    "toggle_adblock" => {
                        let new_state = adb_clone.toggle();
                        let state_str = if new_state { "true" } else { "false" };
                        db_clone.save_setting("adblock_enabled", state_str).ok();
                        println!("[Sonde Core] AdBlock toggled: enabled={}", new_state);
                        let _ = proxy_clone.send_event(UserEvent::AdBlockStateChanged(new_state));
                    }
                    "toggle_fullscreen" => {
                        let _ = proxy_clone.send_event(UserEvent::ToggleFullscreen);
                    }
                    "window_close" => {
                        let _ = proxy_clone.send_event(UserEvent::CloseWindow);
                    }
                    "window_minimize" => {
                        let _ = proxy_clone.send_event(UserEvent::MinimizeWindow);
                    }
                    "window_maximize" => {
                        let _ = proxy_clone.send_event(UserEvent::MaximizeWindow);
                    }
                    "window_drag" => {
                        let _ = proxy_clone.send_event(UserEvent::DragWindow);
                    }
                    _ => {}
                }
            }
        });

    #[cfg(any(
        target_os = "windows",
        target_os = "macos",
        target_os = "ios",
        target_os = "android"
    ))]
    let webview = builder.build(&window)?;

    let internal_pages = InternalPages {
        startpage: startpage_content.to_string(),
        settings: settings_content.to_string(),
        history: history_content.to_string(),
        downloads: downloads_content.to_string(),
    };

    #[cfg(not(any(
        target_os = "windows",
        target_os = "macos",
        target_os = "ios",
        target_os = "android"
    )))]
    let (webview, content_stack, top_box, initial_wv) = {
        use gtk::prelude::*;
        use tao::platform::unix::WindowExtUnix;
        use wry::WebViewBuilderExtUnix;
        use wry::WebViewExtUnix;
        use webkit2gtk::SettingsExt;
        use webkit2gtk::WebViewExt;
        use webkit2gtk::NavigationPolicyDecisionExt;
        use webkit2gtk::PolicyDecisionExt;
        use webkit2gtk::URIRequestExt;

        let vbox = window.default_vbox().expect("Failed to get default vbox from Tao window");

        let top_box = gtk::Box::new(gtk::Orientation::Vertical, 0);
        top_box.set_size_request(-1, 74);
        vbox.pack_start(&top_box, false, false, 0);

        let stack = gtk::Stack::new();
        stack.set_transition_type(gtk::StackTransitionType::None);
        vbox.pack_start(&stack, true, true, 0);

        let wv = builder.build_gtk(&top_box)?;

        if let Some(settings) = webkit2gtk::WebViewExt::settings(&wv.webview()) {
            settings.set_disable_web_security(true);
            settings.set_allow_universal_access_from_file_urls(true);
            settings.set_allow_file_access_from_file_urls(true);
            settings.set_enable_developer_extras(true);
            settings.set_enable_javascript(true);
        }

        let init_wv = webkit2gtk::WebView::new();
        let active_ua = proxy::get_current_user_agent();
        if let Some(settings) = webkit2gtk::WebViewExt::settings(&init_wv) {
            settings.set_enable_developer_extras(true);
            settings.set_enable_webgl(true);
            settings.set_enable_webaudio(true);
            settings.set_enable_media_stream(true);
            settings.set_enable_mediasource(true);
            settings.set_enable_javascript(true);
            settings.set_user_agent(Some(&active_ua));
            settings.set_allow_universal_access_from_file_urls(true);
            settings.set_allow_file_access_from_file_urls(true);
        }

        let p1 = proxy.clone();
        init_wv.connect_notify(Some("uri"), move |wv, _| {
            if let Some(u) = wv.uri() {
                let _ = p1.send_event(UserEvent::PageUrlChanged { id: 1, url: u.to_string() });
            }
        });

        let p2 = proxy.clone();
        init_wv.connect_notify(Some("title"), move |wv, _| {
            if let Some(t) = wv.title() {
                let _ = p2.send_event(UserEvent::PageTitleChanged { id: 1, title: t.to_string() });
            }
        });

        let p3 = proxy.clone();
        init_wv.connect_load_changed(move |wv, ev| {
            let is_loading = ev != webkit2gtk::LoadEvent::Finished;
            let _ = p3.send_event(UserEvent::PageLoadingState { id: 1, is_loading, progress: wv.estimated_load_progress() });
        });

        let p4 = proxy.clone();
        init_wv.connect_decide_policy(move |_wv, decision, decision_type| {
            if decision_type == webkit2gtk::PolicyDecisionType::NavigationAction {
                if let Some(nav_decision) = decision.dynamic_cast_ref::<webkit2gtk::NavigationPolicyDecision>() {
                    #[allow(deprecated)]
                    if let Some(req) = nav_decision.request() {
                        if let Some(uri) = req.uri() {
                            let u_str = uri.to_string();
                            if u_str.starts_with("sonde://action/") || u_str.starts_with("crux://action/")
                                || u_str.starts_with("sonde://live-setting") || u_str.starts_with("crux://live-setting")
                                || u_str.starts_with("sonde://apply-settings") || u_str.starts_with("crux://apply-settings")
                                || u_str.starts_with("sonde://new-tab") || u_str.starts_with("crux://new-tab") {
                                decision.ignore();
                                let _ = p4.send_event(UserEvent::InternalSettingCommand(u_str));
                                return true;
                            } else if u_str.starts_with("sonde://") || u_str.starts_with("crux://") {
                                decision.ignore();
                                let _ = p4.send_event(UserEvent::NavigateUrl(u_str));
                                return true;
                            }
                        }
                    }
                }
            } else if decision_type == webkit2gtk::PolicyDecisionType::NewWindowAction {
                if let Some(nav_decision) = decision.dynamic_cast_ref::<webkit2gtk::NavigationPolicyDecision>() {
                    #[allow(deprecated)]
                    if let Some(req) = nav_decision.request() {
                        if let Some(uri) = req.uri() {
                            let s_uri = uri.to_string();
                            let p = p4.clone();
                            gtk::glib::idle_add_local(move || {
                                let _ = p.send_event(UserEvent::CreateTab { id: 0, url: s_uri.clone() });
                                gtk::glib::ControlFlow::Break
                            });
                            decision.ignore();
                            return true;
                        }
                    }
                }
            }
            false
        });

        load_tab_content(&init_wv, &initial_url, &internal_pages);
        use gtk::gdk;
        webkit2gtk::WebViewExt::set_background_color(&init_wv, &gdk::RGBA::new(0.094, 0.094, 0.106, 1.0));
        stack.add_named(&init_wv, "tab_1");
        init_wv.show();
        stack.set_visible_child_name("tab_1");

        let p_keys = proxy.clone();
        window.gtk_window().connect_key_press_event(move |_win, event| {
            use gtk::gdk;
            let state = event.state();
            let has_ctrl = state.contains(gdk::ModifierType::CONTROL_MASK);
            let has_alt = state.contains(gdk::ModifierType::MOD1_MASK);
            let has_shift = state.contains(gdk::ModifierType::SHIFT_MASK);
            let keyval = event.keyval();

            let is_f5 = keyval == gdk::keys::constants::F5;
            let is_f11 = keyval == gdk::keys::constants::F11;
            let is_f12 = keyval == gdk::keys::constants::F12;

            if has_ctrl || has_alt || is_f5 || is_f11 || is_f12 {
                let name = keyval.name().map(|s| s.to_string()).unwrap_or_default();
                let ch_opt = keyval.to_unicode();
                let key_str = if let Some(ch) = ch_opt {
                    ch.to_string()
                } else {
                    name.clone()
                };

                let lower_ch = key_str.to_lowercase();
                let is_standard_edit = has_ctrl && !has_alt && !has_shift && (
                    lower_ch == "c" || lower_ch == "v" || lower_ch == "x" || lower_ch == "a" || lower_ch == "z" ||
                    lower_ch == "с" || lower_ch == "м" || lower_ch == "ч" || lower_ch == "ф" || lower_ch == "я"
                );

                if !is_standard_edit {
                    let _ = p_keys.send_event(UserEvent::NativeKeyPress {
                        ctrl: has_ctrl,
                        alt: has_alt,
                        shift: has_shift,
                        key: key_str,
                        code: format!("Key{}", name.to_uppercase()),
                    });
                    return gtk::glib::Propagation::Stop;
                }
            }
            gtk::glib::Propagation::Proceed
        });

        window.gtk_window().show_all();
        (wv, stack, top_box, init_wv)
    };

    let db_for_events = Arc::clone(&db);
    let tab_stack = content_stack;
    let top_box_ref = top_box;
    let mut tab_views: std::collections::HashMap<u32, webkit2gtk::WebView> = std::collections::HashMap::new();
    tab_views.insert(1, initial_wv);
    let mut active_tab_id: u32 = 1;
    let mut next_tab_id: u32 = 2;
    let event_proxy_loop = proxy.clone();

    event_loop.run(move |event, _, control_flow| {
        *control_flow = ControlFlow::Wait;

        match event {
            Event::NewEvents(StartCause::Init) => println!("Sonde running..."),
            Event::UserEvent(UserEvent::CloseWindow) => *control_flow = ControlFlow::Exit,
            Event::UserEvent(UserEvent::MinimizeWindow) => window.set_minimized(true),
            Event::UserEvent(UserEvent::MaximizeWindow) => window.set_maximized(!window.is_maximized()),
            Event::UserEvent(UserEvent::ToggleFullscreen) => {
                let is_fullscreen = window.fullscreen().is_some();
                if is_fullscreen {
                    window.set_fullscreen(None);
                } else {
                    window.set_fullscreen(Some(tao::window::Fullscreen::Borderless(None)));
                }
            }
            Event::UserEvent(UserEvent::AdBlockStateChanged(enabled)) => {
                let script = format!("if (window.onAdBlockToggled) window.onAdBlockToggled({});", enabled);
                let _ = webview.evaluate_script(&script);
            }
            Event::UserEvent(UserEvent::DragWindow) => {
                let _ = window.drag_window();
            }
            Event::UserEvent(UserEvent::SettingsLoaded(json_str)) => {
                let script = format!("if (window.onSettingsLoaded) window.onSettingsLoaded({});", json_str);
                let _ = webview.evaluate_script(&script);
            }
            Event::UserEvent(UserEvent::VaultUnlocked(json_str)) => {
                let script = format!(
                    "if (window.onVaultAuthSuccess) window.onVaultAuthSuccess({}); if (document.getElementById('webFrame') && document.getElementById('webFrame').contentWindow && document.getElementById('webFrame').contentWindow.onVaultAuthSuccess) document.getElementById('webFrame').contentWindow.onVaultAuthSuccess({});",
                    json_str, json_str
                );
                let _ = webview.evaluate_script(&script);
            }
            Event::UserEvent(UserEvent::VaultAuthFailed) => {
                let script = "if (window.onVaultAuthFailed) window.onVaultAuthFailed(); if (document.getElementById('webFrame') && document.getElementById('webFrame').contentWindow && document.getElementById('webFrame').contentWindow.onVaultAuthFailed) document.getElementById('webFrame').contentWindow.onVaultAuthFailed();";
                let _ = webview.evaluate_script(&script);
            }
            Event::UserEvent(UserEvent::AutofillData(json_str)) => {
                let script = format!("if (window.onAutofillData) window.onAutofillData({});", json_str);
                let _ = webview.evaluate_script(&script);
            }
            Event::UserEvent(UserEvent::MigrationCompleted(json_str)) => {
                let script = format!(
                    "if (window.onMigrationCompleted) window.onMigrationCompleted({}); if (document.getElementById('webFrame') && document.getElementById('webFrame').contentWindow && document.getElementById('webFrame').contentWindow.onMigrationCompleted) document.getElementById('webFrame').contentWindow.onMigrationCompleted({});",
                    json_str, json_str
                );
                let _ = webview.evaluate_script(&script);
            }
            Event::UserEvent(UserEvent::ExtensionsLoaded(json_str)) => {
                let script = format!(
                    "if (window.onExtensionsLoaded) window.onExtensionsLoaded({}); if (document.getElementById('webFrame') && document.getElementById('webFrame').contentWindow && document.getElementById('webFrame').contentWindow.renderExtensions) document.getElementById('webFrame').contentWindow.renderExtensions({});",
                    json_str, json_str
                );
                let _ = webview.evaluate_script(&script);
            }
            Event::UserEvent(UserEvent::AiResponse(text)) => {
                let escaped = serde_json::to_string(&text).unwrap_or_else(|_| "\"\"".to_string());
                let script = format!("if (window.onAiResponse) window.onAiResponse({}, true);", escaped);
                let _ = webview.evaluate_script(&script);
            }
            Event::UserEvent(UserEvent::DownloadDirSelected(path)) => {
                let path_str = path.to_string_lossy().to_string();
                db_for_events.save_setting("download_dir", &path_str).ok();
                let escaped = serde_json::to_string(&path_str).unwrap_or_default();
                let script = format!(
                    "if (window.onDownloadDirSelected) window.onDownloadDirSelected({}); if (typeof showToast === 'function') showToast('Default download directory saved: ' + {});",
                    escaped, escaped
                );
                let _ = webview.evaluate_script(&script);
            }
            Event::UserEvent(UserEvent::BookmarksLoaded(json_str)) => {
                let script = format!("if (window.onBookmarksLoaded) window.onBookmarksLoaded({});", json_str);
                let _ = webview.evaluate_script(&script);
            }
            Event::UserEvent(UserEvent::HistoryLoaded(json_str)) => {
                let script = format!("if (window.onHistoryLoaded) window.onHistoryLoaded({});", json_str);
                let _ = webview.evaluate_script(&script);
            }
            Event::UserEvent(UserEvent::DownloadsLoaded(json_str)) => {
                let script = format!("if (window.onDownloadsLoaded) window.onDownloadsLoaded({});", json_str);
                let _ = webview.evaluate_script(&script);
            }
            Event::UserEvent(UserEvent::OpenDevTools) => {
                #[cfg(not(any(
                    target_os = "windows",
                    target_os = "macos",
                    target_os = "ios",
                    target_os = "android"
                )))]
                {
                    use webkit2gtk::WebInspectorExt;
                    use wry::WebViewExtUnix;
                    if let Some(inspector) = webkit2gtk::WebViewExt::inspector(&webview.webview()) {
                        inspector.show();
                        println!("[Sonde Core] WebKitGTK Developer Tools Inspector shown");
                    }
                }
            }
            Event::UserEvent(UserEvent::ReaderContentLoaded(json_str)) => {
                let script = format!("if (window.onReaderContentLoaded) window.onReaderContentLoaded({});", json_str);
                let _ = webview.evaluate_script(&script);
            }
            Event::UserEvent(UserEvent::NavigateUrl(url)) => {
                if let Some(wv) = tab_views.get(&active_tab_id) {
                    load_tab_content(wv, &url, &internal_pages);
                }
            }
            Event::UserEvent(UserEvent::CreateTab { mut id, url }) => {
                use gtk::prelude::*;
                use webkit2gtk::WebViewExt;
                use webkit2gtk::SettingsExt;
                use webkit2gtk::NavigationPolicyDecisionExt;
                use webkit2gtk::PolicyDecisionExt;
                use webkit2gtk::URIRequestExt;
                if id == 0 {
                    id = next_tab_id;
                    next_tab_id += 1;
                }
                let wv = webkit2gtk::WebView::new();
                let active_ua = proxy::get_current_user_agent();
                if let Some(settings) = webkit2gtk::WebViewExt::settings(&wv) {
                    settings.set_enable_developer_extras(true);
                    settings.set_enable_webgl(true);
                    settings.set_enable_webaudio(true);
                    settings.set_enable_media_stream(true);
                    settings.set_enable_mediasource(true);
                    settings.set_enable_javascript(true);
                    settings.set_user_agent(Some(&active_ua));
                    settings.set_allow_universal_access_from_file_urls(true);
                    settings.set_allow_file_access_from_file_urls(true);
                }
                webkit2gtk::WebViewExt::set_background_color(&wv, &gtk::gdk::RGBA::new(0.094, 0.094, 0.106, 1.0));

                let p1 = event_proxy_loop.clone();
                let tid = id;
                wv.connect_notify(Some("uri"), move |wv, _| {
                    if let Some(u) = wv.uri() {
                        let _ = p1.send_event(UserEvent::PageUrlChanged { id: tid, url: u.to_string() });
                    }
                });

                let p2 = event_proxy_loop.clone();
                wv.connect_notify(Some("title"), move |wv, _| {
                    if let Some(t) = wv.title() {
                        let _ = p2.send_event(UserEvent::PageTitleChanged { id: tid, title: t.to_string() });
                    }
                });

                let p3 = event_proxy_loop.clone();
                wv.connect_load_changed(move |wv, ev| {
                    let is_loading = ev != webkit2gtk::LoadEvent::Finished;
                    let _ = p3.send_event(UserEvent::PageLoadingState { id: tid, is_loading, progress: wv.estimated_load_progress() });
                });

                let p4 = event_proxy_loop.clone();
                wv.connect_decide_policy(move |_wv, decision, decision_type| {
                    if decision_type == webkit2gtk::PolicyDecisionType::NavigationAction {
                        if let Some(nav_decision) = decision.dynamic_cast_ref::<webkit2gtk::NavigationPolicyDecision>() {
                            #[allow(deprecated)]
                            if let Some(req) = nav_decision.request() {
                                if let Some(uri) = req.uri() {
                                    let u_str = uri.to_string();
                                    if u_str.starts_with("sonde://action/") || u_str.starts_with("crux://action/")
                                        || u_str.starts_with("sonde://live-setting") || u_str.starts_with("crux://live-setting")
                                        || u_str.starts_with("sonde://apply-settings") || u_str.starts_with("crux://apply-settings")
                                        || u_str.starts_with("sonde://new-tab") || u_str.starts_with("crux://new-tab") {
                                        decision.ignore();
                                        let _ = p4.send_event(UserEvent::InternalSettingCommand(u_str));
                                        return true;
                                    } else if u_str.starts_with("sonde://") || u_str.starts_with("crux://") {
                                        decision.ignore();
                                        let _ = p4.send_event(UserEvent::NavigateUrl(u_str));
                                        return true;
                                    }
                                }
                            }
                        }
                    } else if decision_type == webkit2gtk::PolicyDecisionType::NewWindowAction {
                        if let Some(nav_decision) = decision.dynamic_cast_ref::<webkit2gtk::NavigationPolicyDecision>() {
                            #[allow(deprecated)]
                            if let Some(req) = nav_decision.request() {
                                if let Some(uri) = req.uri() {
                                    let s_uri = uri.to_string();
                                    let p = p4.clone();
                                    gtk::glib::idle_add_local(move || {
                                        let _ = p.send_event(UserEvent::CreateTab { id: 0, url: s_uri.clone() });
                                        gtk::glib::ControlFlow::Break
                                    });
                                    decision.ignore();
                                    return true;
                                }
                            }
                        }
                    }
                    false
                });

                load_tab_content(&wv, &url, &internal_pages);
                let name = format!("tab_{}", id);
                tab_stack.add_named(&wv, &name);
                wv.show();
                tab_stack.set_visible_child_name(&name);
                active_tab_id = id;
                tab_views.insert(id, wv);

                let script = format!("if (window.onNativeTabCreated) window.onNativeTabCreated({}, {});", id, serde_json::to_string(&url).unwrap());
                let _ = webview.evaluate_script(&script);
            }
            Event::UserEvent(UserEvent::CloseTab { id, new_active }) => {
                use gtk::prelude::*;
                if let Some(wv) = tab_views.remove(&id) {
                    tab_stack.remove(&wv);
                }
                if let Some(next_id) = new_active {
                    tab_stack.set_visible_child_name(&format!("tab_{}", next_id));
                    active_tab_id = next_id;
                } else if let Some(&first_id) = tab_views.keys().next() {
                    tab_stack.set_visible_child_name(&format!("tab_{}", first_id));
                    active_tab_id = first_id;
                }
            }
            Event::UserEvent(UserEvent::ActivateTab(id)) => {
                use gtk::prelude::*;
                tab_stack.set_visible_child_name(&format!("tab_{}", id));
                active_tab_id = id;
            }
            Event::UserEvent(UserEvent::GoBack) => {
                if let Some(wv) = tab_views.get(&active_tab_id) {
                    use webkit2gtk::WebViewExt;
                    wv.go_back();
                }
            }
            Event::UserEvent(UserEvent::GoForward) => {
                if let Some(wv) = tab_views.get(&active_tab_id) {
                    use webkit2gtk::WebViewExt;
                    wv.go_forward();
                }
            }
            Event::UserEvent(UserEvent::Reload) => {
                if let Some(wv) = tab_views.get(&active_tab_id) {
                    use webkit2gtk::WebViewExt;
                    wv.reload();
                }
            }
            Event::UserEvent(UserEvent::SetUiHeight(h)) => {
                use gtk::prelude::*;
                top_box_ref.set_size_request(-1, h);
                top_box_ref.queue_resize();
            }
            Event::UserEvent(UserEvent::SetZoom(level)) => {
                if let Some(wv) = tab_views.get(&active_tab_id) {
                    use webkit2gtk::WebViewExt;
                    wv.set_zoom_level(level);
                }
            }
            Event::UserEvent(UserEvent::PageUrlChanged { id, url }) => {
                let script = format!("if (window.onNativeUrlChanged) window.onNativeUrlChanged({}, {});", id, serde_json::to_string(&url).unwrap());
                let _ = webview.evaluate_script(&script);
            }
            Event::UserEvent(UserEvent::PageTitleChanged { id, title }) => {
                let script = format!("if (window.onNativeTitleChanged) window.onNativeTitleChanged({}, {});", id, serde_json::to_string(&title).unwrap());
                let _ = webview.evaluate_script(&script);
            }
            Event::UserEvent(UserEvent::PageLoadingState { id, is_loading, progress }) => {
                let script = format!("if (window.onNativeLoadingState) window.onNativeLoadingState({}, {}, {});", id, is_loading, progress);
                let _ = webview.evaluate_script(&script);
            }
            Event::UserEvent(UserEvent::NativeKeyPress { ctrl, alt, shift, key, code }) => {
                let script = format!(
                    "if (window.handleGlobalShortcut) window.handleGlobalShortcut({{ ctrlKey: {}, altKey: {}, shiftKey: {}, key: {}, code: {}, preventDefault: function(){{}} }});",
                    ctrl, alt, shift,
                    serde_json::to_string(&key).unwrap_or_default(),
                    serde_json::to_string(&code).unwrap_or_default()
                );
                let _ = webview.evaluate_script(&script);
            }
            Event::UserEvent(UserEvent::InternalSettingCommand(cmd_url)) => {
                let script = format!("if (window.handleSondeInternalCommand) window.handleSondeInternalCommand({});", serde_json::to_string(&cmd_url).unwrap_or_default());
                let _ = webview.evaluate_script(&script);

                if let Some(q_idx) = cmd_url.find('?') {
                    let qs = &cmd_url[q_idx + 1..];
                    let mut key = String::new();
                    let mut val = String::new();
                    for part in qs.split('&') {
                        if let Some((k, v)) = part.split_once('=') {
                            let decoded_v = percent_decode(v);
                            if k == "key" {
                                key = decoded_v;
                            } else if k == "value" {
                                val = decoded_v;
                            }
                        }
                    }
                    if !key.is_empty() {
                        db_for_events.save_setting(&key, &val).ok();
                        if key == "network_proxy" {
                            proxy::set_network_proxy(&val);
                        }
                        if key == "user_agent" {
                            proxy::set_custom_user_agent(&val);
                        }
                        println!("[Sonde Core] Live Setting Saved via Native Event: {} = {}", key, val);
                    }
                }
            }
            Event::WindowEvent {
                event: WindowEvent::CloseRequested,
                ..
            } => *control_flow = ControlFlow::Exit,
            _ => (),
        }
    });
}
