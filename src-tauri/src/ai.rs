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
        .timeout(std::time::Duration::from_secs(30))
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

    if req.provider == "ollama" {
        // Query local Ollama daemon
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
        // Standard OpenAI-compatible format (OpenAI, DeepSeek, Groq)
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
                {"role": "system", "content": "You are Crux AI, an intelligent engineer-focused browser assistant."},
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
