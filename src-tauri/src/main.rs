use tao::{
    dpi::LogicalSize,
    event::{Event, StartCause, WindowEvent},
    event_loop::{ControlFlow, EventLoop},
    window::WindowBuilder,
};
use wry::WebViewBuilder;

mod storage;
mod tab_manager;

fn main() -> wry::Result<()> {
    let event_loop = EventLoop::new();
    let window = WindowBuilder::new()
        .with_title("Crux 2.0 (Rust Alpha)")
        .with_inner_size(LogicalSize::new(1280.0, 800.0))
        .with_min_inner_size(LogicalSize::new(800.0, 500.0))
        .build(&event_loop)
        .unwrap();

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

    let mut builder = WebViewBuilder::new();
    builder = builder.with_html(embedded_page);

    #[cfg(not(any(target_os = "windows", target_os = "macos")))]
    let _webview = builder.build_gtk(window.gtk_window())?;

    #[cfg(target_os = "windows")]
    let _webview = builder.build(&window)?;

    #[cfg(target_os = "macos")]
    let _webview = builder.build(&window)?;

    event_loop.run(move |event, _, control_flow| {
        *control_flow = ControlFlow::Wait;

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
