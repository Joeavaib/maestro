from __future__ import annotations

import re
from .types import LiteError, LiteRecord, LiteStep


class LiteParser:
    """
    Parst TMP-S Lite Records.
    Toleriert Leerzeichen, fehlende Felder, falsch Reihenfolge.
    """
    
    def parse(self, raw: str) -> LiteRecord:
        rec = LiteRecord(raw=raw)
        
        for line in raw.strip().splitlines():
            line = line.strip()
            if not line or len(line) < 3:
                continue
            
            tag = line[0].upper()
            rest = line[2:].strip() if len(line) > 2 else ""
            parts = [p.strip() for p in rest.split("|")]
            
            if tag == "A":
                self._parse_a(parts, rec)
            elif tag == "E":
                self._parse_e(parts, rec)
            elif tag == "B":
                self._parse_b(parts, rec)
            elif tag == "C":
                self._parse_c(parts, rec)
        
        self._apply_defaults(rec)
        return rec
    
    def _parse_a(self, parts: list[str], rec: LiteRecord):
        if len(parts) >= 1:
            rec.ok = int(parts[0]) if parts[0] in ("0", "1") else 1
        if len(parts) >= 2:
            rec.score = int(parts[1]) if parts[1].isdigit() else 5
        if len(parts) >= 3:
            rec.rationale = parts[2][:200]
    
    def _parse_e(self, parts: list[str], rec: LiteRecord):
        if len(rec.errors) >= 3:
            return
        location = parts[0][:50] if len(parts) >= 1 else "unknown"
        fix = parts[1][:100] if len(parts) >= 2 else "Fehler beheben"
        rec.errors.append(LiteError(location=location, fix=fix))
    
    def _parse_b(self, parts: list[str], rec: LiteRecord):
        if len(rec.briefing) >= 3:
            return
        agent = parts[0][:10].lower() if len(parts) >= 1 else "orch"
        agent = re.sub(r'[^a-z0-9]', '', agent)[:10] or "orch"
        action = parts[1][:200] if len(parts) >= 2 else "Nächsten Schritt ausführen"
        rec.briefing.append(LiteStep(agent=agent, action=action))
    
    def _parse_c(self, parts: list[str], rec: LiteRecord):
        rec._c_parsed = True
        if len(parts) >= 1:
            d = parts[0].upper()
            rec.decision = d if d in ("A", "R", "E") else "R"
        if len(parts) >= 2:
            rec.focus = parts[1][:50] if parts[1] else "*"
    
    def _apply_defaults(self, rec: LiteRecord):
        if not rec.briefing:
            rec.briefing = [LiteStep(agent="orch", action="Nächsten Schritt bestimmen")]
        if not rec.rationale:
            rec.rationale = "Keine Begründung"
        if not hasattr(rec, '_c_parsed'):
            if rec.score >= 7 and rec.ok == 1:
                rec.decision = "A"
            elif rec.score < 4 or rec.ok == 0:
                rec.decision = "R"
            else:
                rec.decision = "R"


def parse_lite(raw: str) -> LiteRecord:
    return LiteParser().parse(raw)
