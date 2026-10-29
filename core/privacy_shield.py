"""
Advanced Privacy Shield for Crux Browser
Provides AudioContext and anti-fingerprinting protection,
Anti-Adblock script trap neutralizers, and URL tracking parameter stripping.
Preserves compatibility with Cloudflare Turnstile, GitHub, and modern SPAs.
"""
from PyQt6.QtWebEngineCore import QWebEngineScript, QWebEngineProfile

STEALTH_SCRIPT_SOURCE = """
(function() {
    try {
        const host = (window.location.hostname || "").toLowerCase();
        // Whitelist critical SPA platforms, deployment dashboards, auth providers, and local tools
        const EXEMPT_DOMAINS = [
            "cloudflare.com", "pages.dev", "workers.dev", "github.com",
            "google.com", "accounts.google.com", "microsoft.com", "apple.com",
            "figma.com", "localhost", "127.0.0.1", "huggingface.co", "gitlab.com",
            "stripe.com", "paypal.com"
        ];
        if (EXEMPT_DOMAINS.some(d => host === d || host.endsWith("." + d))) {
            return;
        }

        // 1. AudioContext Fingerprint Spoofing
        if (window.AudioBuffer) {
            const origGetChannelData = AudioBuffer.prototype.getChannelData;
            AudioBuffer.prototype.getChannelData = function(channel) {
                const data = origGetChannelData.call(this, channel);
                for (let i = 0; i < Math.min(data.length, 8); i++) {
                    data[i] += 0.0000001 * (Math.random() - 0.5);
                }
                return data;
            };
        }

        // 2. Anti-Adblock Trap Evasion (neutralizes checks for fake ad scripts)
        window.canRunAds = true;
        window.isAdBlockActive = false;
        window.isAdblockerActive = false;
    } catch(err) {}
})();
"""

def install_privacy_shield(profile: QWebEngineProfile) -> None:
    """Injects stealth anti-fingerprinting script at DocumentCreation on the profile."""
    try:
        # Remove any existing script with same name before re-inserting
        scripts = profile.scripts()
        for s in scripts.toList():
            if s.name() == "crux_stealth_privacy":
                scripts.remove(s)

        script = QWebEngineScript()
        script.setName("crux_stealth_privacy")
        script.setSourceCode(STEALTH_SCRIPT_SOURCE)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.ApplicationWorld)
        script.setRunsOnSubFrames(True)
        scripts.insert(script)
    except Exception as e:
        print(f"Error installing privacy shield: {e}")

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "mc_eid", "igshid", "yclid", "_openstat", "msclkid"
}

def strip_tracking_params(url_str: str) -> str:
    """Removes common tracking and telemetry query parameters from URLs."""
    try:
        import urllib.parse
        parsed = urllib.parse.urlsplit(url_str)
        if not parsed.query:
            return url_str
        query_dict = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        filtered = [(k, v) for k, v in query_dict if k.lower() not in TRACKING_PARAMS]
        new_query = urllib.parse.urlencode(filtered)
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, new_query, parsed.fragment))
    except Exception:
        return url_str
