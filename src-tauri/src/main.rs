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
    OpenDevTools,
    ToggleFullscreen,
    CloseWindow,
    MinimizeWindow,
    MaximizeWindow,
    DragWindow,
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

    // 2. Initialize Core State: TabManager & AdBlocker
    let tab_manager = Arc::new(Mutex::new(TabManager::new()));
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
    proxy::start_proxy(Arc::clone(&adblocker), 39281);

    // 3. Initialize Tao Event Loop with UserEvent support
    let event_loop = EventLoopBuilder::<UserEvent>::with_user_event().build();
    let proxy = event_loop.create_proxy();

    let window = WindowBuilder::new()
        .with_title("Sonde 2.0")
        .with_inner_size(LogicalSize::new(1280.0, 800.0))
        .with_min_inner_size(LogicalSize::new(800.0, 500.0))
        .with_decorations(false) // Frameless Anthropic Minimal Dark / Sand Aesthetic
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
                "<script>\nwindow.SONDE_STARTPAGE_HTML = {};\nwindow.CRUX_STARTPAGE_HTML = {};\nwindow.SONDE_SETTINGS_HTML = {};\nwindow.CRUX_SETTINGS_HTML = {};\nwindow.SONDE_HISTORY_HTML = {};\nwindow.CRUX_HISTORY_HTML = {};\nwindow.SONDE_DOWNLOADS_HTML = {};\nwindow.CRUX_DOWNLOADS_HTML = {};\n{}\n</script>",
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
                        }
                    }
                    "create_tab" => {
                        let url = v["url"].as_str().unwrap_or("sonde://startpage");
                        let container = v["container"].as_str().unwrap_or("default");
                        let mut tm = tm_clone.lock().unwrap();
                        let tab = tm.create_tab(url.to_string(), container.to_string());
                        println!("[Sonde Core] Created Tab: #{} - {}", tab.id, tab.url);
                    }
                    "close_tab" => {
                        if let Some(id) = v["id"].as_u64() {
                            let mut tm = tm_clone.lock().unwrap();
                            tm.close_tab(id as u32);
                            println!("[Sonde Core] Closed Tab: #{}", id);
                        }
                    }
                    "activate_tab" => {
                        if let Some(id) = v["id"].as_u64() {
                            let mut tm = tm_clone.lock().unwrap();
                            tm.activate_tab(id as u32);
                            println!("[Sonde Core] Activated Tab: #{}", id);
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

    #[cfg(not(any(
        target_os = "windows",
        target_os = "macos",
        target_os = "ios",
        target_os = "android"
    )))]
    let webview = {
        use gtk::prelude::*;
        use tao::platform::unix::WindowExtUnix;
        use wry::WebViewBuilderExtUnix;
        use wry::WebViewExtUnix;
        use webkit2gtk::SettingsExt;

        let vbox = window.default_vbox().expect("Failed to get default vbox from Tao window");
        let wv = builder.build_gtk(vbox)?;

        if let Some(settings) = webkit2gtk::WebViewExt::settings(&wv.webview()) {
            settings.set_disable_web_security(true);
            settings.set_allow_universal_access_from_file_urls(true);
            settings.set_allow_file_access_from_file_urls(true);
            settings.set_enable_developer_extras(true);
            settings.set_enable_webgl(true);
            settings.set_enable_webaudio(true);
            settings.set_enable_media_stream(true);
            settings.set_enable_mediasource(true);
            settings.set_enable_javascript(true);
            let active_ua = proxy::get_current_user_agent();
            settings.set_user_agent(Some(&active_ua));
        }

        window.gtk_window().show_all();
        wv
    };

    let db_for_events = Arc::clone(&db);

    event_loop.run(move |event, _, control_flow| {
        *control_flow = ControlFlow::Wait;

        match event {
            Event::NewEvents(StartCause::Init) => println!("Sonde 2.0 running..."),
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
            Event::WindowEvent {
                event: WindowEvent::CloseRequested,
                ..
            } => *control_flow = ControlFlow::Exit,
            _ => (),
        }
    });
}
