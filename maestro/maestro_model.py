from __future__ import annotations

import logging
from typing import Optional

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

LOGGER = logging.getLogger(__name__)

SYSTEM_ROLE = (
    "You are TMP-S v2.4 Validator.\n"
    "Output must be a single valid TMP-S record.\n"
    "No explanations.\n"
    "No markdown.\n"
    "No extra text.\n"
    "Strict order:\n"
    "V\n"
    "A\n"
    "E*\n"
    "B (3-7 lines)\n"
    "C"
)


class TMPSValidatorModel:
    def __init__(self, base_model: str, adapter_path: str):
        self.tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
        base = AutoModelForCausalLM.from_pretrained(
            base_model,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
        self.model = PeftModel.from_pretrained(base, adapter_path)
        self.model.eval()
        torch.manual_seed(42)

    def generate_tmps(self, user_input: str, repair_instruction: Optional[str] = None) -> str:
        messages = [{"role": "system", "content": SYSTEM_ROLE}]
        if repair_instruction:
            messages.append({"role": "system", "content": repair_instruction})
        messages.append({"role": "user", "content": user_input})

        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        with torch.inference_mode():
            output_ids = self.model.generate(
                **inputs,
                temperature=0.0,
                do_sample=False,
                top_p=1.0,
                repetition_penalty=1.0,
                max_new_tokens=512,
            )

        generated = output_ids[0][inputs["input_ids"].shape[1] :]
        text = self.tokenizer.decode(generated, skip_special_tokens=True).strip()
        LOGGER.info("Raw LLM output: %s", text)
        return text
