#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod storage;
mod tab_manager;

use std::sync::Mutex;
use tab_manager::{TabManager, TabManagerState};

fn main() {
    let tab_manager_state: TabManagerState = Mutex::new(TabManager::new());

    tauri::Builder::default()
        .manage(tab_manager_state)
        .invoke_handler(tauri::generate_context!())
        .invoke_handler(tauri::generate_handler![
            commands::get_tabs,
            commands::create_tab,
            commands::close_tab,
            commands::activate_tab,
            commands::toggle_pin_tab,
            commands::choose_download_directory
        ])
        .run(tauri::generate_context!())
        .expect("error while running Crux application");
}
