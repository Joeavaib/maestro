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

    def generate(self, model: str, prompt: str, options: dict | None = None, system: str | None = None, keep_alive: str | int | None = 0, skip_strip_thinking: bool = False) -> str:
        import sys
        
        # Prepend system prompt to the main prompt to ensure compatibility
        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"
            
        # Define stop sequences to force end of generation
        stop_seqs = ["</rationale>\n\n<rationale>", "[/FILE]", "###", "Previous Attempt"]
            
        payload = {
            "model": model, 
            "prompt": full_prompt, 
            "stream": True,
            "options": options or {}
        }
        
        # Add stop sequences to options
        payload["options"]["stop"] = stop_seqs
        
        if keep_alive is not None:
            payload["keep_alive"] = keep_alive
            
        print(f"[*] Ollama: model={model} keep_alive={keep_alive}")
        
        response_text = ""
        loop_detected = False
        
        try:
            # First try Ollama endpoint (/api/generate)
            url = f"{self.host}/api/generate"
            with requests.post(
                url,
                json=payload,
                timeout=self.timeout_s,
                stream=True
            ) as resp:
                if resp.status_code == 404:
                    # Fallback for native llama-server or OpenAI-style backends
                    print(f"[*] /api/generate not found. Falling back to OpenAI completions...")
                    # Transform payload for OpenAI
                    openai_payload = {
                        "model": model,
                        "prompt": full_prompt,
                        "stream": True,
                        "stop": stop_seqs,
                        "max_tokens": 4096,
                        "temperature": 0.2
                    }
                    resp = requests.post(
                        f"{self.host}/v1/completions",
                        json=openai_payload,
                        timeout=self.timeout_s,
                        stream=True
                    )
                    
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if loop_detected:
                        break
                        
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith("data: "):
                            # Handle OpenAI Server-Sent Events (SSE)
                            chunk_data = line_str[6:].strip()
                            if chunk_data == "[DONE]": break
                            chunk = json.loads(chunk_data)
                            token = chunk.get("choices", [{}])[0].get("text", "")
                        else:
                            # Standard Ollama JSON lines
                            chunk = json.loads(line)
                            token = chunk.get("response", "")
                            
                        response_text += token
                        
                        # Native CLI streaming
                        sys.stdout.write(token)
                        sys.stdout.flush()
                        
                        # --- ADVANCED LOOP DETECTION (Token Window) ---
                        # Check if the last N characters are just repeating
                        if len(response_text) > 200:
                            # Look at the last 150 chars
                            recent_window = response_text[-150:]
                            # Split into words to avoid partial word matches
                            words = recent_window.split()
                            if len(words) > 15:
                                # Grab the last 10 words as a pattern
                                pattern = " ".join(words[-10:])
                                # Count how many times this exact 10-word phrase appears in the last 500 chars
                                search_area = response_text[-500:]
                                if search_area.count(pattern) >= 2: # Reduced from 3 to 2
                                    sys.stdout.write(f"\n[!] PARAGRAPH LOOP DETECTED! Aborting stream.\n")
                                    sys.stdout.flush()
                                    loop_detected = True
                                    break
                        # ----------------------------------------------
                            
        except Exception as e:
            print(f"\n[!] Ollama error: {e}")
            return f"ERROR: {e}"
        
        print("\n") # Newline after streaming finishes
        
        # Strip thinking and prose unless skipped
        if not skip_strip_thinking:
            response_text = _strip_thinking(response_text)
        
        # If we injected <rationale> at the end of the prompt (Force-Start), prepend it back to the response
        if prompt.endswith("<rationale>\n") and not response_text.startswith("<rationale>"):
            response_text = "<rationale>\n" + response_text
            
        return response_text
