use std::sync::atomic::{AtomicBool, Ordering};

pub struct AdBlocker {
    pub blocked_domains: Vec<&'static str>,
    pub enabled: AtomicBool,
}

impl AdBlocker {
    pub fn new() -> Self {
        Self {
            blocked_domains: vec![
                "doubleclick.net",
                "google-analytics.com",
                "googletagmanager.com",
                "adservice.google.com",
                "pagead2.googlesyndication.com",
                "yandex.ru/clck",
                "an.yandex.ru",
                "mc.yandex.ru",
                "facebook.net/tr",
                "connect.facebook.net",
                "analytics.twitter.com",
                "ads-twitter.com",
                "criteo.com",
                "outbrain.com",
                "taboola.com",
                "scorecardresearch.com",
            ],
            enabled: AtomicBool::new(true),
        }
    }

    pub fn is_enabled(&self) -> bool {
        self.enabled.load(Ordering::Relaxed)
    }

    pub fn set_enabled(&self, val: bool) {
        self.enabled.store(val, Ordering::Relaxed);
    }

    pub fn toggle(&self) -> bool {
        let prev = self.enabled.fetch_xor(true, Ordering::Relaxed);
        !prev
    }

    pub fn should_block(&self, url: &str) -> bool {
        if !self.is_enabled() {
            return false;
        }
        let u_lower = url.to_lowercase();
        for domain in &self.blocked_domains {
            if u_lower.contains(domain) {
                return true;
            }
        }
        false
    }
}
