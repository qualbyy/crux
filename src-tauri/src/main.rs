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
    SettingsLoaded(String),
    CloseWindow,
    MinimizeWindow,
    MaximizeWindow,
    DragWindow,
}

fn main() -> wry::Result<()> {
    // WebKitGTK Wayland rendering and compositing fixes to prevent blank/gray screen on Linux Wayland/Hyprland
    std::env::set_var("WEBKIT_DISABLE_DMABUF_RENDERER", "1");
    std::env::set_var("WEBKIT_DISABLE_COMPOSITING_MODE", "1");

    // 1. Initialize SQLite Database in user config dir
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    let config_dir = PathBuf::from(home).join(".config").join("crux");
    let db_path = config_dir.join("crux_v2.db");
    let db = Arc::new(Database::init(db_path).expect("Failed to initialize SQLite database"));

    // 2. Initialize Core State: TabManager & AdBlocker
    let tab_manager = Arc::new(Mutex::new(TabManager::new()));
    let adblocker = Arc::new(AdBlocker::new());

    // 3. Initialize Tao Event Loop with UserEvent support
    let event_loop = EventLoopBuilder::<UserEvent>::with_user_event().build();
    let proxy = event_loop.create_proxy();

    let window = WindowBuilder::new()
        .with_title("Crux 2.0 (Rust Alpha)")
        .with_inner_size(LogicalSize::new(1280.0, 800.0))
        .with_min_inner_size(LogicalSize::new(800.0, 500.0))
        .with_decorations(false) // Removes OS title bar completely (Anthropic Minimal Dark)
        .build(&event_loop)
        .unwrap();

    // 4. Embed UI HTML/CSS/JS Assets
    let html_content = include_str!("../../ui/index.html");
    let css_content = include_str!("../../ui/style.css");
    let js_content = include_str!("../../ui/main.js");
    let startpage_content = include_str!("../../ui/startpage.html");

    // Escape '<' as '\\u003c' to prevent premature </script> closing by HTML tokenizer
    let startpage_escaped = serde_json::to_string(&startpage_content)
        .unwrap_or_default()
        .replace('<', "\\u003c");

    let embedded_page = html_content
        .replace(r#"<link rel="stylesheet" href="style.css">"#, &format!("<style>{}</style>", css_content))
        .replace(r#"<script src="main.js"></script>"#, &format!("<script>window.CRUX_STARTPAGE_HTML = {};\n{}</script>", startpage_escaped, js_content));

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
                            println!("[Rust Core] Navigating to: {}", url);
                        }
                    }
                    "create_tab" => {
                        let url = v["url"].as_str().unwrap_or("https://duckduckgo.com");
                        let container = v["container"].as_str().unwrap_or("default");
                        let mut tm = tm_clone.lock().unwrap();
                        let tab = tm.create_tab(url.to_string(), container.to_string());
                        println!("[Rust Core] Created Tab: #{} - {}", tab.id, tab.url);
                    }
                    "close_tab" => {
                        if let Some(id) = v["id"].as_u64() {
                            let mut tm = tm_clone.lock().unwrap();
                            tm.close_tab(id as u32);
                            println!("[Rust Core] Closed Tab: #{}", id);
                        }
                    }
                    "activate_tab" => {
                        if let Some(id) = v["id"].as_u64() {
                            let mut tm = tm_clone.lock().unwrap();
                            tm.activate_tab(id as u32);
                            println!("[Rust Core] Activated Tab: #{}", id);
                        }
                    }
                    "toggle_pin" => {
                        if let Some(id) = v["id"].as_u64() {
                            let mut tm = tm_clone.lock().unwrap();
                            tm.toggle_pin(id as u32);
                            println!("[Rust Core] Toggled Pin Tab: #{}", id);
                        }
                    }
                    "toggle_mute" => {
                        if let Some(id) = v["id"].as_u64() {
                            let mut tm = tm_clone.lock().unwrap();
                            tm.toggle_mute(id as u32);
                            println!("[Rust Core] Toggled Mute Tab: #{}", id);
                        }
                    }
                    "save_setting" => {
                        if let (Some(key), Some(value)) = (v["key"].as_str(), v["value"].as_str()) {
                            db_clone.save_setting(key, value).ok();
                            println!("[Rust Core] Saved setting: {} = {}", key, value);
                        }
                    }
                    "get_settings" => {
                        let settings = db_clone.get_all_settings();
                        if let Ok(json) = serde_json::to_string(&settings) {
                            let _ = proxy_clone.send_event(UserEvent::SettingsLoaded(json));
                        }
                    }
                    "add_bookmark" => {
                        let url = v["url"].as_str().unwrap_or("");
                        let title = v["title"].as_str().unwrap_or("Bookmark");
                        db_clone.add_bookmark(url, title).ok();
                        println!("[Rust Core] Added bookmark: {}", url);
                    }
                    "get_bookmarks" => {
                        if let Ok(list) = db_clone.get_bookmarks() {
                            if let Ok(json) = serde_json::to_string(&list) {
                                let _ = proxy_clone.send_event(UserEvent::BookmarksLoaded(json));
                            }
                        }
                    }
                    "get_history" => {
                        if let Ok(list) = db_clone.get_history(50) {
                            if let Ok(json) = serde_json::to_string(&list) {
                                let _ = proxy_clone.send_event(UserEvent::HistoryLoaded(json));
                            }
                        }
                    }
                    "clear_history" => {
                        db_clone.clear_history().ok();
                        println!("[Rust Core] History cleared");
                    }
                    "choose_download_dir" => {
                        let p_clone = proxy_clone.clone();
                        std::thread::spawn(move || {
                            let folder = rfd::FileDialog::new()
                                .set_title("Choose Default Download Directory")
                                .pick_folder();
                            if let Some(p) = folder {
                                println!("[Rust Core] Selected download folder: {:?}", p);
                                let _ = p_clone.send_event(UserEvent::DownloadDirSelected(p));
                            }
                        });
                    }
                    "ask_ai" => {
                        let prompt = v["prompt"].as_str().unwrap_or("").to_string();
                        let provider = v["provider"].as_str().unwrap_or("ollama").to_string();
                        let model = v["model"].as_str().unwrap_or("llama3").to_string();
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
                            println!("[Crux AI] Response received: success={}", resp.success);
                            let text = if resp.success {
                                resp.reply
                            } else {
                                resp.error.unwrap_or_else(|| "No response".to_string())
                            };
                            let _ = p_clone.send_event(UserEvent::AiResponse(text));
                        });
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
        }

        window.gtk_window().show_all();
        wv
    };

    let db_for_events = Arc::clone(&db);

    event_loop.run(move |event, _, control_flow| {
        *control_flow = ControlFlow::Wait;

        match event {
            Event::NewEvents(StartCause::Init) => println!("Crux 2.0 Rust Alpha running..."),
            Event::UserEvent(UserEvent::CloseWindow) => *control_flow = ControlFlow::Exit,
            Event::UserEvent(UserEvent::MinimizeWindow) => window.set_minimized(true),
            Event::UserEvent(UserEvent::MaximizeWindow) => window.set_maximized(!window.is_maximized()),
            Event::UserEvent(UserEvent::DragWindow) => {
                let _ = window.drag_window();
            }
            Event::UserEvent(UserEvent::SettingsLoaded(json_str)) => {
                let script = format!("if (window.onSettingsLoaded) window.onSettingsLoaded({});", json_str);
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
                    "if (window.onDownloadDirSelected) window.onDownloadDirSelected({}); if (typeof appendAiMessage === 'function') appendAiMessage('system', 'Default download directory saved: ' + {});",
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
            Event::WindowEvent {
                event: WindowEvent::CloseRequested,
                ..
            } => *control_flow = ControlFlow::Exit,
            _ => (),
        }
    });
}
