from __future__ import annotations

from .types import LiteRecord, LiteError, LiteStep


class RuleEngine:
    """
    Alle deterministischen Ableitungen für TMP-S Lite.
    Kein ML, kein LLM, pure Logik.
    """
    
    @staticmethod
    def validate_semantics(lite: LiteRecord, budget: int):
        """Native Lite semantic validation."""
        # 1. Budget sync
        if lite.decision == "R" and budget <= 0:
            raise ValueError(f"Decision 'R' requested but budget is 0")
        
        # 2. Score/OK consistency
        if lite.ok == 0 and lite.score > 4:
            # Fatal error but high score? Correct to low score.
            lite.score = min(lite.score, 3)
            
    # ── Verdict ──
    @staticmethod
    def derive_verdict(ok: int, score: int) -> str:
        if ok == 0:
            return "H"
        if score >= 7:
            return "P"
        if score >= 4:
            return "W"
        return "F"
    
    # ── Decision Normalisierung ──
    @staticmethod
    def normalize_decision(
        verdict: str, 
        decision: str, 
        budget: int
    ) -> str:
        # Pass/Warn → Accept if decision wasn't explicit rejection
        if verdict == "P" and decision != "A" and decision != "R":
             decision = "A"
        
        # Fail/Hard bei Accept → korrigieren
        if verdict in ("F", "H") and decision == "A":
            decision = "R" if budget > 0 else "E"
        
        # Kein Budget → Escalate
        if decision == "R" and budget <= 0:
            decision = "E"
        
        return decision
    
    # ── Strategy ──
    @staticmethod
    def derive_strategy(
        score: int, 
        turn: int, 
        n_errors: int, 
        budget: int
    ) -> int:
        if score >= 7:
            return 0
        if n_errors <= 1 and turn < 2:
            return 1
        if turn == 0:
            return 2
        if n_errors >= 3:
            return 3
        if budget <= 1:
            return 5
        return 4
    
    # ── Severity ──
    @staticmethod
    def derive_severity(ok: int, score: int, error_index: int) -> str:
        if ok == 0 and error_index == 0:
            return "C"
        if score <= 3:
            return "H"
        if score <= 6:
            return "M"
        return "L"
