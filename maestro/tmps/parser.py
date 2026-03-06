from __future__ import annotations

import re
from .types import ALine, BLine, CLine, ELine, TMPSRecord, VLine, LiteError, LiteRecord, LiteStep


class ParseError(ValueError):
    pass


_DOTPATH_PATTERN = re.compile(r"^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_\-*]+)*$")
_FOCUS_PATTERN = re.compile(r"^(\*|[A-Za-z0-9_]+(?:\.[A-Za-z0-9_\-*]+)*(?:,[A-Za-z0-9_]+(?:\.[A-Za-z0-9_\-*]+)*){0,2})$")


def split_with_escape(text: str) -> list[str]:
    out, current = [], []
    esc = False
    for ch in text:
        if esc:
            if ch == "|":
                current.append("|")
            else:
                current.extend(["\\", ch])
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == "|":
            out.append("".join(current))
            current = []
            continue
        current.append(ch)
    if esc:
        current.append("\\")
    out.append("".join(current))
    return out


def parse_tmps(raw: str, *, strict: bool = False) -> TMPSRecord:
    if strict:
        lines = raw.splitlines()
        if not lines:
            raise ParseError("empty")
        for line in lines:
            if line == "":
                raise ParseError("blank line")
            if line != line.strip():
                raise ParseError("leading/trailing spaces")
    else:
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]

    i = 0
    if not lines:
        raise ParseError("empty")

    if not lines[0].startswith("V "):
        raise ParseError("missing V")

    vparts = split_with_escape(lines[0][2:])
    if len(vparts) != 4:
        raise ParseError("invalid V")
    try:
        vturn = int(vparts[3])
    except ValueError:
        raise ParseError("invalid V turn") from None
    v = VLine(vparts[0], vparts[1], vparts[2], vturn)
    i = 1

    if i >= len(lines) or not lines[i].startswith("A "):
        raise ParseError("missing A")
    aparts = split_with_escape(lines[i][2:])
    if len(aparts) != 4:
        raise ParseError("invalid A")
    a = ALine(*aparts)
    if not re.fullmatch(r"[01]{4}", a.hard4):
        raise ParseError("hard4")
    if not re.fullmatch(r"\d{4}", a.soft4):
        raise ParseError("soft4")
    if a.verdict not in {"P", "W", "F", "H"}:
        raise ParseError("verdict")
    if len(a.rationale.split()) > 12:
        raise ParseError("rationale wordcount")
    i += 1

    es: list[ELine] = []
    while i < len(lines) and lines[i].startswith("E "):
        eparts = split_with_escape(lines[i][2:])
        if len(eparts) not in {3, 4}:
            raise ParseError("invalid E")
        if eparts[1] not in {"C", "H", "M", "L"}:
            raise ParseError("E severity")
        if not _DOTPATH_PATTERN.fullmatch(eparts[0]):
            raise ParseError("E dotpath")
        es.append(ELine(eparts[0], eparts[1], eparts[2], eparts[3] if len(eparts) == 4 else None))
        i += 1

    bs: list[BLine] = []
    while i < len(lines) and lines[i].startswith("B "):
        payload = lines[i][2:]
        if "|" not in payload:
            raise ParseError("invalid B")
        left, right = payload.split("|", 1)
        if ":" not in left:
            raise ParseError("invalid B")
        pri_s, agent = left.split(":", 1)
        try:
            pri = int(pri_s)
        except ValueError:
            raise ParseError("B pri") from None

        if pri < 1 or pri > 7:
            raise ParseError("B pri range")
        if not re.fullmatch(r"[a-z]{2,4}", agent):
            raise ParseError("B agent")

        action_parts = split_with_escape(right)
        if len(action_parts) != 1:
            raise ParseError("B action (unescaped pipe)")

        bs.append(BLine(pri, agent, action_parts[0]))
        i += 1

    if not 3 <= len(bs) <= 7:
        raise ParseError("B count")
    pris = [b.pri for b in bs]
    if pris != sorted(pris) or len(set(pris)) != len(pris):
        raise ParseError("B order")

    if i >= len(lines) or not lines[i].startswith("C "):
        raise ParseError("missing C")
    cparts = split_with_escape(lines[i][2:])
    if len(cparts) != 4:
        raise ParseError("invalid C")

    try:
        strategy = int(cparts[1])
        max_retries = int(cparts[2])
    except ValueError:
        raise ParseError("invalid C int") from None

    c = CLine(cparts[0], strategy, max_retries, cparts[3])
    if c.decision not in {"A", "R", "X", "E"}:
        raise ParseError("decision")
    if c.strategy not in {0, 1, 2, 3, 4, 5}:
        raise ParseError("strategy")
    if c.max_retries < 0 or c.max_retries > 9:
        raise ParseError("max_retries")
    if not _FOCUS_PATTERN.fullmatch(c.focus):
        raise ParseError("focus")

    if i != len(lines) - 1:
        raise ParseError("trailing lines")

    return TMPSRecord(v=v, a=a, e=es, b=bs, c=c)


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
