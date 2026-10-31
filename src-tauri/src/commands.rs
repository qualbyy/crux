use crate::tab_manager::{Tab, TabManagerState};
use tauri::State;

#[tauri::command]
pub fn get_tabs(state: State<TabManagerState>) -> Vec<Tab> {
    let tm = state.lock().unwrap();
    tm.tabs.clone()
}

#[tauri::command]
pub fn create_tab(url: String, container: String, state: State<TabManagerState>) -> Tab {
    let mut tm = state.lock().unwrap();
    tm.create_tab(url, container)
}

#[tauri::command]
pub fn close_tab(id: u32, state: State<TabManagerState>) -> Option<u32> {
    let mut tm = state.lock().unwrap();
    tm.close_tab(id)
}

#[tauri::command]
pub fn activate_tab(id: u32, state: State<TabManagerState>) {
    let mut tm = state.lock().unwrap();
    tm.activate_tab(id);
}

#[tauri::command]
pub fn toggle_pin_tab(id: u32, state: State<TabManagerState>) {
    let mut tm = state.lock().unwrap();
    tm.toggle_pin(id);
}

#[tauri::command]
pub async fn choose_download_directory() -> Option<String> {
    let folder = rfd::AsyncFileDialog::new()
        .set_title("Choose Download Directory")
        .pick_folder()
        .await;
    folder.map(|f| f.path().to_string_lossy().to_string())
}
