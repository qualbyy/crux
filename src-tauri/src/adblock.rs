pub struct AdBlocker {
    pub blocked_domains: Vec<&'static str>,
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
        }
    }

    pub fn should_block(&self, url: &str) -> bool {
        let u_lower = url.to_lowercase();
        for domain in &self.blocked_domains {
            if u_lower.contains(domain) {
                return true;
            }
        }
        false
    }
}
