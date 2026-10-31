use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use tao::{
    dpi::LogicalSize,
    event::{Event, StartCause, WindowEvent},
    event_loop::{ControlFlow, EventLoop},
    window::WindowBuilder,
};
use wry::WebViewBuilder;
use serde_json::Value;

mod storage;
mod tab_manager;

use storage::Database;
use tab_manager::TabManager;

fn main() -> wry::Result<()> {
    // 1. Initialize SQLite Database in user config dir
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    let config_dir = PathBuf::from(home).join(".config").join("crux");
    let db_path = config_dir.join("crux_v2.db");
    let db = Arc::new(Database::init(db_path).expect("Failed to initialize SQLite database"));

    // 2. Initialize TabManager
    let tab_manager = Arc::new(Mutex::new(TabManager::new()));

    // 3. Initialize Tao Event Loop & Window
    let event_loop = EventLoop::new();
    let window = WindowBuilder::new()
        .with_title("Crux 2.0 (Rust Alpha)")
        .with_inner_size(LogicalSize::new(1280.0, 800.0))
        .with_min_inner_size(LogicalSize::new(800.0, 500.0))
        .build(&event_loop)
        .unwrap();

    // 4. Embed UI HTML/CSS/JS Assets
    let html_content = include_str!("../../ui/index.html");
    let css_content = include_str!("../../ui/style.css");
    let js_content = include_str!("../../ui/main.js");

    let embedded_page = html_content
        .replace(r#"<link rel="stylesheet" href="style.css">"#, &format!("<style>{}</style>", css_content))
        .replace(r#"<script src="main.js"></script>"#, &format!("<script>{}</script>", js_content));

    #[cfg(not(any(target_os = "windows", target_os = "macos")))]
    use tao::platform::unix::WindowExtUnix;
    #[cfg(not(any(target_os = "windows", target_os = "macos")))]
    use wry::WebViewBuilderExtUnix;

    let tm_clone = Arc::clone(&tab_manager);
    let db_clone = Arc::clone(&db);

    let mut builder = WebViewBuilder::new();
    builder = builder
        .with_html(embedded_page)
        .with_ipc_handler(move |req| {
            let body = req.body();
            if let Ok(v) = serde_json::from_str::<Value>(body) {
                let cmd = v["cmd"].as_str().unwrap_or("");
                match cmd {
                    "navigate" => {
                        if let Some(url) = v["url"].as_str() {
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
                    "choose_download_dir" => {
                        std::thread::spawn(|| {
                            let folder = rfd::FileDialog::new()
                                .set_title("Choose Default Download Directory")
                                .pick_folder();
                            if let Some(p) = folder {
                                println!("[Rust Core] Selected download folder: {:?}", p);
                            }
                        });
                    }
                    _ => {}
                }
            }
        });

    #[cfg(not(any(target_os = "windows", target_os = "macos")))]
    let _webview = {
        let wv = builder.build_gtk(window.gtk_window())?;
        use gtk::prelude::WidgetExt;
        window.gtk_window().show_all();
        wv
    };

    #[cfg(target_os = "windows")]
    let _webview = builder.build(&window)?;

    #[cfg(target_os = "macos")]
    let _webview = builder.build(&window)?;

    event_loop.run(move |event, _, control_flow| {
        *control_flow = ControlFlow::Wait;
        let _ = &_webview; // Prevent drop of webview during runtime

        match event {
            Event::NewEvents(StartCause::Init) => println!("Crux 2.0 Rust Alpha running..."),
            Event::WindowEvent {
                event: WindowEvent::CloseRequested,
                ..
            } => *control_flow = ControlFlow::Exit,
            _ => (),
        }
    });
}
