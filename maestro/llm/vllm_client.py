from __future__ import annotations

import json
import requests
import sys

class VLLMClient:
    def __init__(self, host: str = "http://127.0.0.1:8000", timeout_s: int = 120):
        self.host = host.rstrip("/")
        self.timeout_s = timeout_s

    def generate(self, model: str, prompt: str, options: dict | None = None, system: str | None = None, keep_alive: str | int | None = 0, skip_strip_thinking: bool = False, guided_regex: str | None = None) -> str:
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
            
        payload = {
            "model": model, 
            "messages": messages, 
            "stream": True
        }
        
        if options:
            if "temperature" in options: payload["temperature"] = options["temperature"]
            if "top_p" in options: payload["top_p"] = options["top_p"]
            if "min_p" in options:
                # min_p is often passed in 'extra_body' or as a direct param depending on vLLM version
                payload["min_p"] = options["min_p"]
            if "repeat_penalty" in options: 
                payload["frequency_penalty"] = 0.1 # Soft prevention
                payload["presence_penalty"] = 0.1
            if "stop" in options: payload["stop"] = options["stop"]
        
        if guided_regex:
            # vLLM/Outlines integration
            payload["guided_regex"] = guided_regex
            
        print(f"[*] vLLM: model={model} host={self.host}")
        
        response_text = ""
        current_line = ""
        last_lines = []
        loop_detected = False
        
        try:
            with requests.post(
                f"{self.host}/v1/chat/completions",
                json=payload,
                timeout=self.timeout_s,
                stream=True
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if loop_detected:
                        break
                        
                    line = line.decode('utf-8').strip()
                    if not line or line == "data: [DONE]":
                        continue
                        
                    if line.startswith("data: "):
                        line = line[6:]
                        
                    try:
                        chunk = json.loads(line)
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            token = delta.get("content", "")
                            
                            if token:
                                response_text += token
                                sys.stdout.write(token)
                                sys.stdout.flush()
                                
                                # Loop detection
                                if "\n" in token:
                                    parts = token.split("\n")
                                    current_line += parts[0]
                                    
                                    if len(response_text) > 200:
                                        recent_window = response_text[-150:]
                                        words = recent_window.split()
                                        if len(words) > 15:
                                            pattern = " ".join(words[-10:])
                                            search_area = response_text[-500:]
                                            if search_area.count(pattern) >= 2:
                                                sys.stdout.write(f"\n[!] PARAGRAPH LOOP DETECTED! Aborting stream.\n")
                                                sys.stdout.flush()
                                                loop_detected = True
                                                break
                                                
                                    current_line = parts[-1]
                                else:
                                    current_line += token
                    except json.JSONDecodeError:
                        continue
                            
        except Exception as e:
            print(f"\n[!] vLLM error: {e}")
            return f"ERROR: {e}"
        
        print("\n")
        
        return response_text.strip()