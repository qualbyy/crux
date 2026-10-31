use serde::{Deserialize, Serialize};
use std::sync::Mutex;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tab {
    pub id: u32,
    pub title: String,
    pub url: String,
    pub container: String,
    pub is_pinned: bool,
    pub is_muted: bool,
    pub is_active: bool,
}

pub struct TabManager {
    next_id: u32,
    pub tabs: Vec<Tab>,
    pub active_id: Option<u32>,
}

impl TabManager {
    pub fn new() -> Self {
        let mut tm = Self {
            next_id: 1,
            tabs: Vec::new(),
            active_id: None,
        };
        // Initial tab
        tm.create_tab("crux://startpage".to_string(), "default".to_string());
        tm
    }

    pub fn create_tab(&mut self, url: String, container: String) -> Tab {
        let id = self.next_id;
        self.next_id += 1;

        let tab = Tab {
            id,
            title: "New Tab".to_string(),
            url,
            container,
            is_pinned: false,
            is_muted: false,
            is_active: true,
        };

        // Mark previous tabs as inactive
        for t in &mut self.tabs {
            t.is_active = false;
        }

        self.active_id = Some(id);
        self.tabs.push(tab.clone());
        tab
    }

    pub fn close_tab(&mut self, id: u32) -> Option<u32> {
        if let Some(pos) = self.tabs.iter().position(|t| t.id == id) {
            self.tabs.remove(pos);
            if self.active_id == Some(id) {
                if !self.tabs.is_empty() {
                    let next_pos = if pos < self.tabs.len() { pos } else { self.tabs.len() - 1 };
                    self.tabs[next_pos].is_active = true;
                    self.active_id = Some(self.tabs[next_pos].id);
                } else {
                    self.active_id = None;
                }
            }
        }
        self.active_id
    }

    pub fn activate_tab(&mut self, id: u32) {
        for t in &mut self.tabs {
            t.is_active = t.id == id;
        }
        self.active_id = Some(id);
    }

    pub fn toggle_pin(&mut self, id: u32) {
        if let Some(tab) = self.tabs.iter_mut().find(|t| t.id == id) {
            tab.is_pinned = !tab.is_pinned;
        }
    }
}

pub type TabManagerState = Mutex<TabManager>;
