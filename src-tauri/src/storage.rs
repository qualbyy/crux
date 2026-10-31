use rusqlite::{params, Connection, Result};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::Mutex;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistoryEntry {
    pub id: i64,
    pub url: String,
    pub title: String,
    pub visited_at: String,
    pub timestamp: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BookmarkEntry {
    pub id: i64,
    pub url: String,
    pub title: String,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DownloadItem {
    pub id: i64,
    pub filename: String,
    pub url: String,
    pub path: String,
    pub size: i64,
    pub state: String,
    pub timestamp: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PasswordEntry {
    pub id: i64,
    pub url: String,
    pub username: String,
    pub password: String,
    pub created_at: String,
}

pub struct Database {
    pub conn: Mutex<Connection>,
}

impl Database {
    pub fn init(db_path: PathBuf) -> Result<Self> {
        if let Some(parent) = db_path.parent() {
            std::fs::create_dir_all(parent).ok();
        }
        let conn = Connection::open(db_path)?;

        conn.execute(
            "CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                title TEXT,
                visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )?;

        conn.execute(
            "CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )?;

        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )",
            [],
        )?;

        conn.execute(
            "CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                url TEXT,
                path TEXT,
                size INTEGER DEFAULT 0,
                state TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )?;

        conn.execute(
            "CREATE TABLE IF NOT EXISTS passwords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )?;

        conn.execute(
            "CREATE TABLE IF NOT EXISTS cookies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host TEXT NOT NULL,
                name TEXT NOT NULL,
                value TEXT NOT NULL,
                path TEXT DEFAULT '/',
                is_secure INTEGER DEFAULT 0,
                expires INTEGER DEFAULT 0,
                UNIQUE(host, name, path)
            )",
            [],
        )?;

        conn.execute(
            "CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT,
                container TEXT,
                is_pinned INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 0
            )",
            [],
        )?;

        Ok(Self {
            conn: Mutex::new(conn),
        })
    }

    pub fn add_history(&self, url: &str, title: &str) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO history (url, title) VALUES (?1, ?2)",
            params![url, title],
        )?;
        Ok(())
    }

    pub fn get_history(&self, limit: u32) -> Result<Vec<HistoryEntry>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(
            "SELECT id, url, COALESCE(title, ''), visited_at, COALESCE(strftime('%s', visited_at), 0) FROM history ORDER BY id DESC LIMIT ?1"
        )?;
        let rows = stmt.query_map(params![limit], |row| {
            let ts_str: rusqlite::types::Value = row.get(4)?;
            let ts = match ts_str {
                rusqlite::types::Value::Integer(i) => i,
                rusqlite::types::Value::Text(s) => s.parse::<i64>().unwrap_or(0),
                _ => 0,
            };
            Ok(HistoryEntry {
                id: row.get(0)?,
                url: row.get(1)?,
                title: row.get(2)?,
                visited_at: row.get(3)?,
                timestamp: ts,
            })
        })?;

        let mut res = Vec::new();
        for r in rows {
            if let Ok(item) = r {
                res.push(item);
            }
        }
        Ok(res)
    }

    pub fn add_download(&self, filename: &str, url: &str, path: &str, size: i64, state: &str) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO downloads (filename, url, path, size, state) VALUES (?1, ?2, ?3, ?4, ?5)",
            params![filename, url, path, size, state],
        )?;
        Ok(())
    }

    pub fn get_downloads(&self, limit: u32) -> Result<Vec<DownloadItem>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(
            "SELECT id, filename, COALESCE(url, ''), COALESCE(path, ''), size, state, COALESCE(strftime('%s', created_at), 0) FROM downloads ORDER BY id DESC LIMIT ?1"
        )?;
        let rows = stmt.query_map(params![limit], |row| {
            let ts_str: rusqlite::types::Value = row.get(6)?;
            let ts = match ts_str {
                rusqlite::types::Value::Integer(i) => i,
                rusqlite::types::Value::Text(s) => s.parse::<i64>().unwrap_or(0),
                _ => 0,
            };
            Ok(DownloadItem {
                id: row.get(0)?,
                filename: row.get(1)?,
                url: row.get(2)?,
                path: row.get(3)?,
                size: row.get(4)?,
                state: row.get(5)?,
                timestamp: ts,
            })
        })?;

        let mut res = Vec::new();
        for r in rows {
            if let Ok(item) = r {
                res.push(item);
            }
        }
        Ok(res)
    }

    pub fn clear_downloads(&self) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute("DELETE FROM downloads", [])?;
        Ok(())
    }

    pub fn clear_history(&self) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute("DELETE FROM history", [])?;
        Ok(())
    }

    pub fn delete_history(&self, url: &str) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute("DELETE FROM history WHERE url = ?1", params![url])?;
        Ok(())
    }

    pub fn delete_bookmark(&self, url: &str) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute("DELETE FROM bookmarks WHERE url = ?1", params![url])?;
        Ok(())
    }

    pub fn add_bookmark(&self, url: &str, title: &str) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT OR REPLACE INTO bookmarks (url, title) VALUES (?1, ?2)",
            params![url, title],
        )?;
        Ok(())
    }

    pub fn get_bookmarks(&self) -> Result<Vec<BookmarkEntry>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, url, COALESCE(title, ''), created_at FROM bookmarks ORDER BY id DESC")?;
        let rows = stmt.query_map([], |row| {
            Ok(BookmarkEntry {
                id: row.get(0)?,
                url: row.get(1)?,
                title: row.get(2)?,
                created_at: row.get(3)?,
            })
        })?;

        let mut res = Vec::new();
        for r in rows {
            if let Ok(item) = r {
                res.push(item);
            }
        }
        Ok(res)
    }

    pub fn save_setting(&self, key: &str, val: &str) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?1, ?2)",
            params![key, val],
        )?;
        Ok(())
    }

    pub fn get_setting(&self, key: &str) -> Option<String> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT value FROM settings WHERE key = ?1").ok()?;
        stmt.query_row(params![key], |r| r.get(0)).ok()
    }

    pub fn get_all_settings(&self) -> std::collections::HashMap<String, String> {
        let conn = self.conn.lock().unwrap();
        let mut map = std::collections::HashMap::new();
        if let Ok(mut stmt) = conn.prepare("SELECT key, value FROM settings") {
            if let Ok(rows) = stmt.query_map([], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
            }) {
                for r in rows.flatten() {
                    map.insert(r.0, r.1);
                }
            }
        }
        map
    }

    // --- CREDENTIALS VAULT (PASSWORDS) ---
    pub fn get_passwords(&self) -> Result<Vec<PasswordEntry>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, url, username, password, created_at FROM passwords ORDER BY id DESC")?;
        let rows = stmt.query_map([], |row| {
            Ok(PasswordEntry {
                id: row.get(0)?,
                url: row.get(1)?,
                username: row.get(2)?,
                password: row.get(3)?,
                created_at: row.get(4)?,
            })
        })?;

        let mut res = Vec::new();
        for r in rows.flatten() {
            res.push(r);
        }
        Ok(res)
    }

    pub fn add_password(&self, url: &str, username: &str, password: &str) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO passwords (url, username, password) VALUES (?1, ?2, ?3)",
            params![url, username, password],
        )?;
        Ok(())
    }

    pub fn delete_password(&self, id: i64) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute("DELETE FROM passwords WHERE id = ?1", params![id])?;
        Ok(())
    }

    pub fn clear_passwords(&self) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute("DELETE FROM passwords", [])?;
        Ok(())
    }

    pub fn get_cookies_for_host(&self, host: &str) -> Vec<(String, String)> {
        let conn = self.conn.lock().unwrap();
        let mut list = Vec::new();
        let domain_wildcard = format!("%{}", host);
        if let Ok(mut stmt) = conn.prepare("SELECT name, value FROM cookies WHERE ?1 LIKE ('%' || host) OR host LIKE ?2") {
            if let Ok(rows) = stmt.query_map(params![host, domain_wildcard], |r| {
                Ok((r.get::<_, String>(0)?, r.get::<_, String>(1)?))
            }) {
                for r in rows.flatten() {
                    list.push(r);
                }
            }
        }
        list
    }

    pub fn get_cookies_count(&self) -> i64 {
        let conn = self.conn.lock().unwrap();
        conn.query_row("SELECT count(*) FROM cookies", [], |r| r.get(0)).unwrap_or(0)
    }

    pub fn get_passwords_count(&self) -> i64 {
        let conn = self.conn.lock().unwrap();
        conn.query_row("SELECT count(*) FROM passwords", [], |r| r.get(0)).unwrap_or(0)
    }
}
