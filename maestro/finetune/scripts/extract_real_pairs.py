import json
import os
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from maestro.llm.prompts import VALIDATOR_SYSTEM_PROMPT


def extract_from_run(run_dir):
    run_dir = Path(run_dir)
    pairs = []
    
    # Durchsuche alle Turn-Verzeichnisse (0, 1, 2...)
    turns_dir = run_dir / "turns"
    if not turns_dir.exists():
        # Manche Runs haben direkt Ordner 0, 1, 2 ohne "turns" Zwischenordner
        turns_dir = run_dir
        
    if not turns_dir.exists():
        return []
        
    for turn_id in sorted([d for d in os.listdir(turns_dir) if d.isdigit()], key=int):
        turn_path = turns_dir / turn_id
        val_input_file = turn_path / "validator_input.txt"
        tmps_raw_file = turn_path / "tmps_raw.txt"
        
        if val_input_file.exists() and tmps_raw_file.exists():
            try:
                with open(val_input_file, 'r', encoding='utf-8') as f:
                    val_input = f.read().strip()
                with open(tmps_raw_file, 'r', encoding='utf-8') as f:
                    tmps_raw = f.read().strip()
                
                # Bereinige val_input (manchmal ist da zu viel Müll drin)
                # Wir wollen nur den Teil ab [SID]
                start_marker = "[SID]"
                if start_marker in val_input:
                    val_input = val_input[val_input.find(start_marker):]
                
                pairs.append({
                    "messages": [
                        {"role": "system", "content": VALIDATOR_SYSTEM_PROMPT},
                        {"role": "user", "content": val_input},
                        {"role": "assistant", "content": tmps_raw}
                    ],
                    "metadata": {
                        "run_root": str(run_dir),
                        "turn": turn_id
                    }
                })
            except Exception as e:
                print(f"Fehler beim Lesen von {turn_path}: {e}")
                
    return pairs

def main():
    parser = argparse.ArgumentParser(description="Extrahiere real-world Trainingstaten aus Maestro Runs")
    parser.add_argument("--runs_dir", type=str, required=True, help="Basis-Verzeichnis der Runs (z.B. multi_file_test/runs)")
    parser.add_argument("--output_file", type=str, default="finetune/data/stufe1_format/real_run_pairs.jsonl", help="Output JSONL Datei")
    args = parser.parse_args()

    all_pairs = []
    base_dir = Path(args.runs_dir)
    
    if not base_dir.exists():
        print(f"❌ Verzeichnis {base_dir} nicht gefunden.")
        return

    # Maestro Struktur: runs/[SID]/[RUNID]/turns/[0,1,2...]
    for sid_dir in base_dir.iterdir():
        if sid_dir.is_dir():
            for rid_dir in sid_dir.iterdir():
                if rid_dir.is_dir():
                    run_pairs = extract_from_run(rid_dir)
                    all_pairs.extend(run_pairs)
                    if run_pairs:
                        print(f"✅ {len(run_pairs)} Turns aus {rid_dir.name} extrahiert")

    with open(args.output_file, "w", encoding='utf-8') as f:
        for p in all_pairs:
            f.write(json.dumps(p) + "\n")
    
    print(f"\n🎉 Insgesamt {len(all_pairs)} reale Trainingspaare in {args.output_file} gespeichert.")

if __name__ == "__main__":
    main()
