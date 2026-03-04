#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import json
import random
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from maestro.llm.prompts import VALIDATOR_SYSTEM_PROMPT


@dataclass
class SynthCase:
    request: str
    artifact_kind: str
    patch_ok: bool
    checks_ok: bool
    budget: int


def _mk_validator_input(case: SynthCase) -> str:
    patch_apply = {"ok": case.patch_ok}
    if not case.patch_ok:
        patch_apply["error"] = "invalid artifact"
    checks_summary = "all_passed" if case.checks_ok else "failed:lint"
    return (
        f"[MODE] NORMAL\n"
        f"[REQUEST]\n{case.request}\n"
        f"[ARTIFACT_KIND] {case.artifact_kind}\n"
        f"[ARTIFACT]\n<synthetic>\n"
        f"[PATCH_APPLY] {json.dumps(patch_apply, ensure_ascii=False)}\n"
        f"[CHECKS] {{\"summary\": \"{checks_summary}\"}}\n"
        f"[LAST_TMPS] NONE\n"
        f"[BUDGET] {case.budget}\n"
    )


def _mk_tmps(case: SynthCase) -> str:
    ok = 1 if case.patch_ok and case.checks_ok else 0
    score = 9 if ok else 3
    decision = "A" if ok else ("R" if case.budget > 0 else "E")
    rationale = "synthetic success" if ok else "synthetic failure"

    lines = [f"A {ok}|{score}|{rationale}"]
    if not ok:
        lines.append("E repo|fix issue")
    lines.append("B imp|fix based on checks")
    lines.append(f"C {decision}|*")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate synthetic validator SFT data")
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    random.seed(args.seed)
    reqs = [
        "Create hello.txt with greeting",
        "Refactor parser and keep tests green",
        "Fix failing check and update docs",
        "Add new config field and tests",
    ]

    rows = []
    for _ in range(args.n):
        case = SynthCase(
            request=random.choice(reqs),
            artifact_kind=random.choice(["diff", "file_blocks", "invalid"]),
            patch_ok=random.random() > 0.25,
            checks_ok=random.random() > 0.35,
            budget=random.randint(0, 3),
        )
        row = {
            "source": "synthetic",
            "messages": [
                {"role": "system", "content": VALIDATOR_SYSTEM_PROMPT},
                {"role": "user", "content": _mk_validator_input(case)},
                {"role": "assistant", "content": _mk_tmps(case)},
            ],
        }
        rows.append(row)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} synthetic examples to {args.out}")


if __name__ == "__main__":
    main()
