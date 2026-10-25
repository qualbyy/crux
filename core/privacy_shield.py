"""
Advanced Privacy Shield for Zephyrium Browser
Provides Canvas, AudioContext, and WebGL anti-fingerprinting noise injection,
Anti-Adblock script trap neutralizers, and URL tracking parameter stripping.
"""
from PyQt6.QtWebEngineCore import QWebEngineScript, QWebEngineProfile

STEALTH_SCRIPT_SOURCE = """
(function() {
    try {
        // 1. Canvas Fingerprinting Jitter (randomizes imperceptible 1-bit values to bust canvas hashes)
        const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(...args) {
            try {
                const ctx = this.getContext('2d');
                if (ctx && this.width > 0 && this.height > 0) {
                    const imgData = ctx.getImageData(0, 0, 1, 1);
                    imgData.data[0] = (imgData.data[0] ^ 1);
                    ctx.putImageData(imgData, 0, 0);
                }
            } catch(e) {}
            return origToDataURL.apply(this, args);
        };

        // 2. AudioContext Fingerprint Spoofing
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

        // 3. WebGL Unmasked Vendor & Renderer Spoofing
        const patchWebGL = (proto) => {
            if (!proto) return;
            const origGetParam = proto.getParameter;
            proto.getParameter = function(param) {
                if (param === 0x9245) return 'Intel Inc.'; // UNMASKED_VENDOR_WEBGL
                if (param === 0x9246) return 'Intel Iris Pro Graphics OpenGL Engine'; // UNMASKED_RENDERER_WEBGL
                return origGetParam.call(this, param);
            };
        };
        if (window.WebGLRenderingContext) patchWebGL(WebGLRenderingContext.prototype);
        if (window.WebGL2RenderingContext) patchWebGL(WebGL2RenderingContext.prototype);

        // 4. Anti-Adblock Trap Evasion (neutralizes checks for fake ad scripts)
        window.canRunAds = true;
        window.isAdBlockActive = false;
        window.isAdblockerActive = false;
    } catch(err) {}
})();
"""

def install_privacy_shield(profile: QWebEngineProfile) -> None:
    """Injects stealth anti-fingerprinting script at DocumentCreation on the profile."""
    try:
        script = QWebEngineScript()
        script.setName("zephyrium_stealth_privacy")
        script.setSourceCode(STEALTH_SCRIPT_SOURCE)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.ApplicationWorld)
        script.setRunsOnSubFrames(True)
        profile.scripts().insert(script)
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

