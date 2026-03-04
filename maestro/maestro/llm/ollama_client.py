from __future__ import annotations

import json
import re
import requests


# Regex to remove Qwen3 thinking tags
_THINK_PATTERN = re.compile(r"<think>.*?</think>", re.DOTALL)


def _strip_thinking(text: str) -> str:
    """Remove Qwen3 <think> tags and clean up the output."""
    # Remove thinking blocks (both closed and unclosed)
    cleaned = _THINK_PATTERN.sub("", text)
    if "<think>" in cleaned:
        cleaned = cleaned.split("<think>")[0]
    
    # Also handle "Thinking... ...done thinking." pattern
    if "...done thinking." in cleaned:
        cleaned = cleaned.split("...done thinking.")[-1]
    elif "Thinking..." in cleaned:
        cleaned = cleaned.split("Thinking...")[-1]

    # Remove leading/trailing whitespace and empty lines
    cleaned = cleaned.strip()
    return cleaned


class OllamaClient:
    def __init__(self, host: str, timeout_s: int = 120):
        self.host = host.rstrip("/")
        self.timeout_s = timeout_s

    def generate(self, model: str, prompt: str, options: dict | None = None, system: str | None = None, keep_alive: str | int | None = None) -> str:
        # Prepend system prompt to the main prompt to ensure compatibility
        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"
            
        payload = {"model": model, "prompt": full_prompt, "stream": False}
        if options:
            payload["options"] = options
        
        if keep_alive is not None:
            payload["keep_alive"] = keep_alive
            
        print(f"[*] Ollama: model={model} url={self.host}/api/generate keep_alive={keep_alive}")
        
        try:
            resp = requests.post(
                f"{self.host}/api/generate",
                json=payload,
                timeout=self.timeout_s
            )
            resp.raise_for_status()
            body = resp.json()
        except Exception as e:
            print(f"[!] Ollama error: {e}")
            return f"ERROR: {e}"
        
        response = body.get("response", "")
        print(f"[DEBUG] Raw response: {response}")
        
        # Strip thinking and prose
        response = _strip_thinking(response)
        
        return response
