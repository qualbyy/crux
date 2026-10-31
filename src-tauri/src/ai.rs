use serde::{Deserialize, Serialize};
use serde_json::json;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AiRequest {
    pub provider: String,
    pub model: String,
    pub prompt: String,
    pub api_key: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AiResponse {
    pub success: bool,
    pub reply: String,
    pub error: Option<String>,
}

pub fn query_ai(req: AiRequest) -> AiResponse {
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(45))
        .build();

    let client = match client {
        Ok(c) => c,
        Err(e) => {
            return AiResponse {
                success: false,
                reply: String::new(),
                error: Some(format!("Failed to build HTTP client: {}", e)),
            }
        }
    };

    if req.provider == "gemini" || req.model.starts_with("gemini-") {
        // Google Gemini API
        let key = req.api_key.clone().unwrap_or_default();
        if key.trim().is_empty() {
            return AiResponse {
                success: false,
                reply: String::new(),
                error: Some("Gemini API key is required. Please set it in Sonde Settings -> AI Assistant.".to_string()),
            };
        }
        let model = if req.model.is_empty() || req.model == "default" {
            "gemini-2.5-flash"
        } else {
            &req.model
        };
        let url = format!(
            "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent?key={}",
            model, key.trim()
        );

        let payload = json!({
            "contents": [{
                "role": "user",
                "parts": [{"text": req.prompt}]
            }],
            "systemInstruction": {
                "parts": [{"text": "You are Sonde AI, an intelligent, ultra-fast, engineer-grade browser assistant."}]
            }
        });

        match client.post(&url).json(&payload).send() {
            Ok(resp) => {
                if let Ok(v) = resp.json::<serde_json::Value>() {
                    if let Some(err) = v.get("error") {
                        let msg = err["message"].as_str().unwrap_or("Gemini API error");
                        AiResponse {
                            success: false,
                            reply: String::new(),
                            error: Some(format!("Gemini Error: {}", msg)),
                        }
                    } else if let Some(reply) = v["candidates"][0]["content"]["parts"][0]["text"].as_str() {
                        AiResponse {
                            success: true,
                            reply: reply.to_string(),
                            error: None,
                        }
                    } else {
                        AiResponse {
                            success: false,
                            reply: String::new(),
                            error: Some("No text returned by Gemini".to_string()),
                        }
                    }
                } else {
                    AiResponse {
                        success: false,
                        reply: String::new(),
                        error: Some("Invalid response from Gemini endpoint".to_string()),
                    }
                }
            }
            Err(e) => AiResponse {
                success: false,
                reply: String::new(),
                error: Some(format!("Gemini request failed: {}", e)),
            },
        }
    } else if req.provider == "ollama" {
        // Local Ollama daemon
        let payload = json!({
            "model": if req.model.is_empty() { "llama3" } else { &req.model },
            "prompt": req.prompt,
            "stream": false
        });

        match client
            .post("http://127.0.0.1:11434/api/generate")
            .json(&payload)
            .send()
        {
            Ok(resp) => {
                if let Ok(v) = resp.json::<serde_json::Value>() {
                    let reply = v["response"].as_str().unwrap_or("").to_string();
                    AiResponse {
                        success: true,
                        reply,
                        error: None,
                    }
                } else {
                    AiResponse {
                        success: false,
                        reply: String::new(),
                        error: Some("Invalid JSON from Ollama".to_string()),
                    }
                }
            }
            Err(e) => AiResponse {
                success: false,
                reply: String::new(),
                error: Some(format!("Ollama connection error (is ollama running?): {}", e)),
            },
        }
    } else {
        // OpenAI / DeepSeek / Custom OpenAI-compatible endpoint
        let endpoint = if req.provider == "deepseek" {
            "https://api.deepseek.com/v1/chat/completions"
        } else if req.provider == "groq" {
            "https://api.groq.com/openai/v1/chat/completions"
        } else {
            "https://api.openai.com/v1/chat/completions"
        };

        let key = req.api_key.unwrap_or_default();
        let payload = json!({
            "model": req.model,
            "messages": [
                {"role": "system", "content": "You are Sonde AI, an intelligent engineer-focused browser assistant."},
                {"role": "user", "content": req.prompt}
            ],
            "temperature": 0.7
        });

        match client
            .post(endpoint)
            .header("Authorization", format!("Bearer {}", key))
            .json(&payload)
            .send()
        {
            Ok(resp) => {
                if let Ok(v) = resp.json::<serde_json::Value>() {
                    let reply = v["choices"][0]["message"]["content"]
                        .as_str()
                        .unwrap_or("")
                        .to_string();
                    AiResponse {
                        success: true,
                        reply,
                        error: None,
                    }
                } else {
                    AiResponse {
                        success: false,
                        reply: String::new(),
                        error: Some("Failed to parse API response".to_string()),
                    }
                }
            }
            Err(e) => AiResponse {
                success: false,
                reply: String::new(),
                error: Some(format!("AI Request error: {}", e)),
            },
        }
    }
}
