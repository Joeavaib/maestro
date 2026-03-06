from __future__ import annotations

from threading import Lock
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


class HFClient:
    """
    HuggingFace and PEFT based client for the LoRA-Validator.
    
    ### DETERMINISTIC DECODING MANDATORY
    For a protocol validator like TMP-S, deterministic decoding (temperature=0.0, do_sample=False)
    is strictly required. Any stochastic variance in the output could lead to:
    1. Invalid protocol syntax that fails strict parsing.
    2. Non-reproducible routing decisions.
    3. Structural 'drift' in long-running orchestrations.
    
    The validator must act as a pure, deterministic function of its input to ensure 
    system integrity and predictable agent orchestration.
    """
    
    _MODEL_CACHE: dict[tuple[str, str | None], tuple[object, object]] = {}
    _CACHE_LOCK = Lock()

    def __init__(self, adapter_path: str | None = None):
        self.adapter_path = adapter_path

    def _load_model(self, model: str) -> tuple[object, object]:
        cache_key = (model, self.adapter_path)
        with self._CACHE_LOCK:
            cached = self._MODEL_CACHE.get(cache_key)
            if cached is not None:
                return cached

            tokenizer = AutoTokenizer.from_pretrained(model, trust_remote_code=True)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            # Use 4-bit quantization for efficiency on AMD/NVIDIA GPUs
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )

            base_model = AutoModelForCausalLM.from_pretrained(
                model,
                quantization_config=quantization_config,
                device_map="auto",
                trust_remote_code=True,
                attn_implementation="eager",
            )
            
            if self.adapter_path:
                loaded_model = PeftModel.from_pretrained(base_model, self.adapter_path)
            else:
                loaded_model = base_model
                
            loaded_model.eval()

            self._MODEL_CACHE[cache_key] = (tokenizer, loaded_model)
            return tokenizer, loaded_model

    @staticmethod
    def _build_prompt(prompt: str, system: str | None = None) -> str:
        if system:
            return f"{system}\n\n{prompt}"
        return prompt

    def generate(self, model: str, prompt: str, options: dict | None = None, system: str | None = None, skip_strip_thinking: bool = False) -> str:
        tokenizer, loaded_model = self._load_model(model)
        opts = dict(options or {})
        
        # Force deterministic parameters for validator stability
        seed = opts.pop("seed", 42)
        max_new_tokens = int(opts.pop("max_new_tokens", opts.pop("num_predict", 512)))
        max_new_tokens = max(1, min(512, max_new_tokens))
        
        # Stricly deterministic decoding
        temperature = 0.0
        top_p = 1.0
        do_sample = False

        import torch
        if seed is not None:
            torch.manual_seed(int(seed))

        # Build messages for chat template
        messages = []
        if system and system.strip():
            messages.append({"role": "system", "content": system})
        
        messages.append({"role": "user", "content": prompt})

        # Apply chat template (special handling for Qwen3-style 'thinking' if needed)
        try:
            # enable_thinking=False is important for Qwen3 to avoid <think> tags in structured output
            inputs = tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                return_tensors="pt",
                enable_thinking=not skip_strip_thinking,
            )
        except TypeError:
            # Fallback for models/tokenizers that don't support enable_thinking
            inputs = tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                return_tensors="pt",
            )

        # Handle BatchEncoding vs Tensor returns
        if hasattr(inputs, "input_ids"):
            input_ids = inputs.input_ids
        else:
            input_ids = inputs

        model_device = getattr(loaded_model, "device", None)
        if model_device is not None:
            input_ids = input_ids.to(model_device)

        with torch.inference_mode():
            outputs = loaded_model.generate(
                input_ids,
                do_sample=do_sample,
                temperature=temperature,
                top_p=top_p,
                max_new_tokens=max_new_tokens,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
            
        generated = outputs[0][input_ids.shape[-1] :]
        return tokenizer.decode(generated, skip_special_tokens=True).strip()
