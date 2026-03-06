"""
Test: Validator TMP-S Verständnis nach Epoche 1
================================================

Dieser Test überprüft, ob der Validator nach dem ersten Training
 die grundlegenden TMP-S Konzepte verstanden hat.

Verwendung:
    ./venv/bin/python3.12 -m pytest tests/test_validator_understanding.py -v

Oder direkt:
    ./venv/bin/python3.12 tests/test_validator_understanding.py
"""

import json
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from maestro.llm.prompts import VALIDATOR_SYSTEM_PROMPT


class MockValidator:
    """Mock-Validator für Test ohne echtes Modell."""
    
    def __init__(self, adapter_path: str | None = None):
        self.adapter_path = adapter_path
        self.calls: list[dict] = []
    
    def generate(self, prompt: str, system: str | None = None) -> str:
        """Simuliere Validator-Output."""
        self.calls.append({"prompt": prompt, "system": system})
        
        # In echter Implementierung würde hier das Modell inference machen
        # Für den Test returnen wir einen Platzhalter
        return "V 2.4|test|run|0\nA 1111|8888|P|Test\nB 1:imp|Action\nC A|1|0|*"


def create_test_scenario(name: str, checks: dict, patch: dict, budget: int, expected_verdict: str, expected_decision: str) -> dict:
    """Erstelle ein Test-Szenario."""
    return {
        "name": name,
        "input": {
            "sid": "test-001",
            "runid": "run-001", 
            "turn": 0,
            "budget": budget,
            "request": f"Test: {name}",
            "checks": checks,
            "patch": patch,
        },
        "expected": {
            "verdict": expected_verdict,
            "decision": expected_decision,
        }
    }


# Test-Szenarien definieren
TEST_SCENARIOS = [
    # Format-Tests (sollte nach Epoche 1 funktionieren)
    create_test_scenario(
        name="All Checks Pass",
        checks={"summary": "ok", "patch_applied": True, "tests_ok": True},
        patch={"ok": True},
        budget=3,
        expected_verdict="P",
        expected_decision="A",
    ),
    create_test_scenario(
        name="Patch Fails",
        checks={"summary": "not_started", "patch_applied": False},
        patch={"ok": False, "error": "patch failed"},
        budget=3,
        expected_verdict="F",
        expected_decision="R",
    ),
    create_test_scenario(
        name="Checks Fail With Budget",
        checks={"summary": "failed", "patch_applied": True, "lint_ok": False},
        patch={"ok": True},
        budget=2,
        expected_verdict="F",
        expected_decision="R",
    ),
    create_test_scenario(
        name="Checks Fail No Budget",
        checks={"summary": "failed", "patch_applied": True},
        patch={"ok": True},
        budget=0,
        expected_verdict="F",
        expected_decision="E",
    ),
    # Logik-Tests (sollte nach Epoche 1 beginnen zu funktionieren)
    create_test_scenario(
        name="Security Critical",
        checks={"summary": "failed", "security_scan": {"critical": True}, "patch_applied": True},
        patch={"ok": True},
        budget=3,
        expected_verdict="H",
        expected_decision="X",
    ),
    create_test_scenario(
        name="Warning State",
        checks={"summary": "ok", "warnings": ["coverage_low"], "patch_applied": True},
        patch={"ok": True},
        budget=3,
        expected_verdict="W",
        expected_decision="A",
    ),
]


def build_validator_input(scenario: dict) -> str:
    """Baue Validator Input aus Szenario."""
    inp = scenario["input"]
    return (
        f"[SID] {inp['sid']}\n"
        f"[RUNID] {inp['runid']}\n"
        f"[TURN] {inp['turn']}\n"
        f"[BUDGET_AFTER_TURN] {inp['budget']}\n"
        f"[MODE] NORMAL\n"
        f"[REQUEST] {inp['request']}\n"
        f"[ARTIFACT_KIND] diff\n"
        f"[ARTIFACT] <test>\n"
        f"[PATCH_APPLY] {json.dumps(inp['patch'])}\n"
        f"[CHECKS] {json.dumps(inp['checks'])}\n"
        f"[LAST_TMPS] NONE\n"
    )


def parse_tmps_simple(tmps_text: str) -> dict:
    """Einfacher TMP-S Parser für Tests."""
    lines = tmps_text.strip().split('\n')
    result = {"verdict": None, "decision": None}
    
    for line in lines:
        if line.startswith('A '):
            parts = line[2:].split('|')
            if len(parts) >= 3:
                result["verdict"] = parts[2]
        elif line.startswith('C '):
            parts = line[2:].split('|')
            if len(parts) >= 1:
                result["decision"] = parts[0]
    
    return result


def test_validator_understanding(adapter_path: str | None = None, verbose: bool = True):
    """
    Teste Validator Verständnis.
    
    Args:
        adapter_path: Pfad zum Adapter nach Epoche 1, oder None für Base Model
        verbose: Ausführliche Ausgabe
    
    Returns:
        dict mit Test-Ergebnissen
    """
    validator = MockValidator(adapter_path)
    
    results = {
        "total": len(TEST_SCENARIOS),
        "passed": 0,
        "failed": 0,
        "details": []
    }
    
    if verbose:
        print("=" * 60)
        print("VALIDATOR TMP-S VERSTÄNDNIS-TEST")
        print("=" * 60)
        print(f"Adapter: {adapter_path or 'Base Model (kein Training)'}\n")
    
    for scenario in TEST_SCENARIOS:
        # Input bauen
        val_input = build_validator_input(scenario)
        
        # Validator aufrufen
        try:
            response = validator.generate(
                prompt=val_input,
                system=VALIDATOR_SYSTEM_PROMPT
            )
            
            # Response parsen
            parsed = parse_tmps_simple(response)
            
            # Prüfen
            expected = scenario["expected"]
            verdict_ok = parsed["verdict"] == expected["verdict"]
            decision_ok = parsed["decision"] == expected["decision"]
            passed = verdict_ok and decision_ok
            
            result = {
                "name": scenario["name"],
                "passed": passed,
                "expected": expected,
                "got": parsed,
                "response": response
            }
            
            if passed:
                results["passed"] += 1
                status = "✅ PASS"
            else:
                results["failed"] += 1
                status = "❌ FAIL"
            
            results["details"].append(result)
            
            if verbose:
                print(f"\n{status} | {scenario['name']}")
                print(f"  Input: {scenario['input']['checks']['summary']}, budget={scenario['input']['budget']}")
                print(f"  Expected: verdict={expected['verdict']}, decision={expected['decision']}")
                print(f"  Got:      verdict={parsed['verdict']}, decision={parsed['decision']}")
                if not passed:
                    print(f"  Raw Response:\n{response[:200]}...")
        
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "name": scenario["name"],
                "passed": False,
                "error": str(e)
            })
            if verbose:
                print(f"\n💥 ERROR | {scenario['name']}: {e}")
    
    # Zusammenfassung
    if verbose:
        print("\n" + "=" * 60)
        print("ZUSAMMENFASSUNG")
        print("=" * 60)
        print(f"Gesamt:  {results['total']}")
        print(f"✅ Pass:  {results['passed']}")
        print(f"❌ Fail:  {results['failed']}")
        print(f"Erfolgsrate: {results['passed']/results['total']*100:.1f}%")
        
        if results["passed"] == results["total"]:
            print("\n🎉 Alle Tests bestanden! Validator versteht TMP-S!")
        elif results["passed"] >= results["total"] * 0.8:
            print("\n⚠️  Gut, aber noch Raum für Verbesserung.")
        else:
            print("\n🔧 Mehr Training nötig.")
    
    return results


def test_with_real_model(adapter_path: str = "finetune/output/stufe1_format_booster/final"):
    """
    Test mit echtem Modell (benötigt GPU und trainierten Adapter).
    
    Diese Funktion lädt das tatsächliche Modell und führt Inference durch.
    """
    try:
        from peft import PeftModel, PeftConfig
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        
        print("Lade Modell... (kann 1-2 Minuten dauern)")
        
        # Base Model laden
        base_model = "Qwen/Qwen2.5-3B-Instruct"
        model = AutoModelForCausalLM.from_pretrained(
            base_model,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        tokenizer = AutoTokenizer.from_pretrained(base_model)
        
        # Adapter laden wenn vorhanden
        adapter_path = Path(adapter_path)
        if adapter_path.exists():
            print(f"Lade Adapter von {adapter_path}")
            model = PeftModel.from_pretrained(model, str(adapter_path))
        else:
            print("⚠️  Kein Adapter gefunden, teste Base Model")
        
        model.eval()
        
        # Validator Wrapper
        class RealValidator:
            def __init__(self, model, tokenizer):
                self.model = model
                self.tokenizer = tokenizer
            
            def generate(self, prompt: str, system: str | None = None) -> str:
                # Format für Qwen
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})
                
                text = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
                
                inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)
                
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=256,
                        temperature=0.0,
                        do_sample=False,
                        pad_token_id=self.tokenizer.eos_token_id
                    )
                
                response = self.tokenizer.decode(
                    outputs[0][inputs['input_ids'].shape[1]:],
                    skip_special_tokens=True
                )
                return response
        
        validator = RealValidator(model, tokenizer)
        
        # Tests durchführen
        results = {
            "total": len(TEST_SCENARIOS),
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        print("\n" + "=" * 60)
        print("ECHTER VALIDATOR TEST")
        print("=" * 60)
        
        for scenario in TEST_SCENARIOS:
            val_input = build_validator_input(scenario)
            
            print(f"\n📝 Teste: {scenario['name']}")
            response = validator.generate(val_input, VALIDATOR_SYSTEM_PROMPT)
            parsed = parse_tmps_simple(response)
            
            expected = scenario["expected"]
            verdict_ok = parsed["verdict"] == expected["verdict"]
            decision_ok = parsed["decision"] == expected["decision"]
            passed = verdict_ok and decision_ok
            
            if passed:
                results["passed"] += 1
                print(f"   ✅ PASS")
            else:
                results["failed"] += 1
                print(f"   ❌ FAIL")
            
            print(f"   Expected: {expected}")
            print(f"   Got:      {parsed}")
            print(f"   Raw:\n{response[:150]}")
        
        print(f"\nErfolgsrate: {results['passed']/results['total']*100:.1f}%")
        return results
        
    except ImportError as e:
        print(f"Fehlende Dependencies: {e}")
        print("Installiere: pip install peft transformers torch")
        return None
    except Exception as e:
        print(f"Fehler beim Laden des Modells: {e}")
        return None


# PyTest Interface
import pytest

@pytest.mark.parametrize("scenario", TEST_SCENARIOS)
def test_scenario(scenario):
    """PyTest Wrapper für einzelne Szenarien."""
    validator = MockValidator()
    val_input = build_validator_input(scenario)
    
    response = validator.generate(val_input, VALIDATOR_SYSTEM_PROMPT)
    parsed = parse_tmps_simple(response)
    expected = scenario["expected"]
    
    assert parsed["verdict"] == expected["verdict"], \
        f"Verdict mismatch in {scenario['name']}: expected {expected['verdict']}, got {parsed['verdict']}"
    assert parsed["decision"] == expected["decision"], \
        f"Decision mismatch in {scenario['name']}: expected {expected['decision']}, got {parsed['decision']}"


if __name__ == "__main__":
    # Direkter Aufruf
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Validator TMP-S Verständnis")
    parser.add_argument("--adapter", type=str, default=None, 
                        help="Pfad zum Adapter (optional)")
    parser.add_argument("--real", action="store_true",
                        help="Echtes Modell laden (benötigt GPU)")
    
    args = parser.parse_args()
    
    if args.real:
        test_with_real_model(args.adapter or "finetune/output/stufe1_format_booster/final")
    else:
        test_validator_understanding(args.adapter)
