from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VLine:
    ver: str
    sid: str
    runid: str
    turn: int


@dataclass
class ALine:
    hard4: str
    soft4: str
    verdict: str
    rationale: str


@dataclass
class ELine:
    dotpath: str
    severity: str
    fix_hint: str
    turn_ref: str | None = None


@dataclass
class BLine:
    pri: int
    agent: str
    action: str


@dataclass
class CLine:
    decision: str
    strategy: int
    max_retries: int
    focus: str


@dataclass
class LiteError:
    location: str
    fix: str
    severity: str = ""
    turn_ref: int = -1

    @property
    def fix_hint(self) -> str:
        return f"{self.location}: {self.fix}"


@dataclass
class LiteStep:
    agent: str
    action: str
    priority: int = 0


@dataclass
class LiteRecord:
    ok: int = 1
    score: int = 5
    rationale: str = ""
    errors: list[LiteError] = field(default_factory=list)
    briefing: list[LiteStep] = field(default_factory=list)
    decision: str = "R"
    focus: str = "*"
    raw: str = ""


@dataclass
class TMPSRecord:
    v: VLine
    a: ALine
    e: list[ELine]
    b: list[BLine]
    c: CLine
