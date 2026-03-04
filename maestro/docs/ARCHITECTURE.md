# Maestro - Architektur & Funktionsweise

## Übersicht

Maestro ist ein deterministischer, lokaler Orchestrator für KI-gestützte Code-Generierung. Er koordiniert mehrere Specialist-Agenten über Ollama oder HuggingFace-Modelle und verwendet ein proprietäres Protokoll namens **TMP-S v2.4** zur Validierung und Steuerung des Workflows.

Das Kernkonzept ist eine **Validator-First Architektur**, bei der ein spezialisierter Validator-LLM den gesamten Workflow kontrolliert und entscheidet, wann welcher Specialist-Agent agieren soll.

---

## System-Architektur

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MAESTRO ORCHESTRATOR                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────────────────┐  │
│  │   Validator  │─────▶│   TMP-S      │─────▶│   Routing Decision       │  │
│  │   (LLM)      │      │   Parser     │      │   A/R/E/X                │  │
│  └──────────────┘      └──────────────┘      └──────────────────────────┘  │
│         │                                               │                   │
│         │                                               ▼                   │
│         │                                      ┌──────────────┐            │
│         │                                      │   Builder    │            │
│         │                                      │   Agents     │            │
│         │                                      └──────────────┘            │
│         │                                               │                   │
│         │                                               ▼                   │
│         │                                      ┌──────────────┐            │
│         └─────────────────────────────────────▶│   Apply &    │            │
│                                                │   Check      │            │
│                                                └──────────────┘            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Kernkomponenten

### 1. Entry Point & CLI (`maestro/cli.py`)

Der Einstiegspunkt der Anwendung:
- Verarbeitet Kommandozeilenargumente (`--repo`, `--request`, `--cfg`, `--sandboxed`)
- Lädt die Konfiguration aus einer JSON-Datei
- Erstellt LLM-Clients (Ollama für Specialists, Ollama/HF für Validator)
- Startet den Orchestrator

**Verwendung:**
```bash
maestro run --repo PATH --request FILE_OR_STRING --cfg CFG.json [--sandboxed|--unsafe-local]
```

### 2. Konfiguration (`maestro/config.py`)

Die `RunnerConfig`-Klasse definiert alle Laufzeitparameter:

| Feld | Beschreibung |
|------|-------------|
| `ollama_host` | URL für Ollama API (Standard: `http://127.0.0.1:11434`) |
| `validator_backend` | `ollama` oder `hf` (HuggingFace) |
| `validator_model` | Modellname für den Validator |
| `validator_adapter_path` | Pfad zu LoRA/PEFT Adapter (nur für HF) |
| `strict_mode` | Bei `true`: Ablehnung normalisierter TMP-S Records |
| `max_retries` | Maximale Wiederholungsversuche |
| `abs_max_turns` | Hartes Limit für Orchestrator-Runden |
| `execution_mode` | `sandboxed` oder `unsafe-local` |
| `agents` | Mapping von Agent-Codes zu Modellkonfigurationen |

### 3. Orchestrator (`maestro/orch/orchestrator.py`)

Der Herzstück der Anwendung. Implementiert einen **Validator-First Turn-based Loop**:

```
Turn Loop (max abs_max_turns):
┌─────────────────┐
│ 1. VALIDATOR    │ ◀── Erhält aktuellen Zustand (Patch, Checks, etc.)
│    (Architekt)  │     Gibt TMP-S Record mit Entscheidung aus
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────┐
│ 2. ROUTING      │────▶│ A (Accept)  → Task abgeschlossen
│    Entscheidung │     │ E (Escalate)→ An Mensch eskalieren
└────────┬────────┘     │ X (Cancel)  → Abbrechen
         │ R            └─────────┘
         ▼
┌─────────────────┐
│ 3. BUILDER      │ ◀── Specialist-Agent generiert Code
│    (Ausführer)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. APPLY & TEST │ ◀── Patch anwenden + Checks ausführen
│                 │
└─────────────────┘
         │
         └──────────▶ Nächster Turn
```

**Wichtige Design-Entscheidung: Trennung von Validator und Builder**
- **Validator** kümmert sich um Protokoll, Logik und Constraints (Architektur)
- **Builder** fokussiert auf Syntax und Implementierung (Coding)
- Verhindert "Confirmation Bias" durch adversarischen Dialog

### 4. TMP-S Protokoll (`maestro/tmps/`)

TMP-S (Task Management Protocol - Structured) v2.4 ist ein striktes Textprotokoll zur Steuerung des Workflows.

#### Record-Struktur:

```
V 2.4|SID123|RUN456|0          ← V-Line: Version, Session-ID, Run-ID, Turn
A 1111|0000|F|Initial Plan     ← A-Line: Hard4|Soft4|Verdict|Rationale
E path.to.error|C|fix hint     ← E-Lines: Fehlerdetails (0-n)
B 1:bld|Implement core logic   ← B-Lines: Aufgaben (3-7, sortiert)
B 2:bld|Add unit tests
B 3:bld|Final check
C R|1|2|fib.py                 ← C-Line: Decision|Strategy|Retries|Focus
```

#### Feld-Beschreibungen:

| Line | Feld | Bedeutung |
|------|------|-----------|
| V | Version | TMP-S Version (2.4) |
| V | SID | Session ID |
| V | RunID | Eindeutige Run-ID |
| V | Turn | Aktueller Zyklus (0-n) |
| A | Hard4 | 4 Hardware-Bits (0=fehlgeschlagen, 1=ok) |
| A | Soft4 | 4 Software-Scores (0-9) |
| A | Verdict | P=Pass, W=Warning, F=Fail, H=Hard Fail |
| A | Rationale | Kurze Beschreibung (max 12 Wörter) |
| E | Dotpath | Pfad zum Fehler (z.B. `f.src.main_py`) |
| E | Severity | C=Critical, H=High, M=Medium, L=Low |
| E | Fix Hint | Hinweis zur Behebung |
| B | Priority | 1-7 (niedriger = wichtiger) |
| B | Agent | 2-4 Kleinbuchstaben (z.B. `imp`, `tst`, `doc`) |
| B | Action | Aufgabenbeschreibung |
| C | Decision | A=Accept, R=Retry, E=Escalate, X=Cancel |
| C | Strategy | 0-5 (0=Standard, 5=Minimal Fix) |
| C | Max Retries | Verbleibende Versuche |
| C | Focus | Datei-Pfad oder `*` |

### 5. LLM Clients (`maestro/llm/`)

#### OllamaClient (`ollama_client.py`)
- Kommuniziert mit Ollama HTTP API
- Entfernt `<think>` Tags aus Qwen3-Ausgaben
- Unterstützt System-Prompts

#### HFClient (`hf_client.py`)
- Lädt HuggingFace-Modelle mit 4-Bit-Quantisierung
- Unterstützt PEFT/LoRA Adapter
- Cache für geladene Modelle (Singleton-Pattern)
- **Deterministisches Decoding** (temperature=0.0, do_sample=False)
- Spezielle Behandlung für Qwen3 (enable_thinking=False)

### 6. Patch-System (`maestro/orch/patch.py`)

Unterstützt zwei Arten von Code-Änderungen:

**1. Unified Diff:**
```diff
diff --git a/file.py b/file.py
--- a/file.py
+++ b/file.py
@@ -1,5 +1,5 @@
 def hello():
-    print("old")
+    print("new")
```

**2. FILE Blocks:**
```
FILE: path/to/file.py
```python
def new_function():
    pass
```
FILE: another/file.txt
Content here
```

Sicherheitsprüfungen:
- Keine Binärdateien
- Keine Path Traversal (`..`)
- Optionale Umbenennungen (`allow_renames`)

### 7. Checks (`maestro/orch/checks.py`)

Automatisierte Validierung nach jedem Patch:
- Konfigurierbare Kommandos (z.B. `pytest`, `black --check`)
- Timeout-Unterstützung
- Erforderliche vs. optionale Checks

### 8. Storage & Logging (`maestro/store.py`, `maestro/log.py`)

Jeder Run wird in `.maestro/` persistiert:
```
.maestro/
├── runs/{sid}/{runid}/
│   ├── request.txt           # Ursprüngliche Anfrage
│   ├── cfg.json              # Konfiguration
│   ├── final/
│   │   └── final_patch.diff  # Endergebnis
│   └── turns/
│       └── {n}/
│           ├── validator_input.txt
│           ├── tmps_raw.txt
│           ├── builder_output.txt
│           ├── patch_apply.json
│           └── checks.json
└── work/{sid}/{runid}/repo/   # Arbeitskopie des Repositories
```

---

## Workflow im Detail

### Phase 1: Initialisierung
1. CLI parst Argumente und lädt Config
2. `RunStore` erstellt neue Session (SID + RunID)
3. Repository wird nach `.maestro/work/{sid}/{runid}/repo/` kopiert
4. Logger initialisiert Verzeichnisstruktur

### Phase 2: Validierung (pro Turn)
1. `build_validator_input()` erstellt Kontext aus:
   - Original-Request
   - Aktuellem Artefakt (Diff/File Blocks)
   - Patch-Apply-Ergebnis
   - Check-Ergebnissen
   - Vorherigem TMP-S Record

2. Validator-LLM generiert TMP-S Record
3. `parse_tmps()` validiert Syntax
4. `validate_tmps_semantics()` prüft Logik:
   - Verdict basiert auf Hard/Soft Bits
   - Decision passt zu Verdict und Budget
   - Budget-Synchronisation

5. `normalize_tmps()` korrigiert Inkonsistenzen (falls nicht strict_mode)

### Phase 3: Routing
Basierend auf der C-Line Decision:
- **A (Accept)**: Workflow beenden, finalen Diff generieren
- **E (Escalate)** / **X (Cancel)**: An Mensch übergeben
- **R (Retry)**: Zum Builder routen

### Phase 4: Code-Generierung
1. `build_specialist_context()` erstellt menschenlesbares Feedback
2. Specialist-Agent (z.B. `imp`, `tst`, `doc`) generiert Code
3. `parse_artifact()` extrahiert Diff oder FILE Blocks

### Phase 5: Anwendung & Validierung
1. Patch wird auf Arbeits-Repository angewendet
2. Konfigurierte Checks werden ausgeführt
3. Ergebnisse werden für nächsten Turn gespeichert

---

## Feinabstimmung (Fine-tuning)

Im `finetune/`-Verzeichnis befinden sich Skripte zur Feinabstimmung eines Validators:

- `scripts/generate_synth_dataset.py`: Generiert synthetische Trainingsdaten
- `scripts/filter_and_split.py`: Filtert und splittet Datensätze
- `scripts/extract_real_pairs.py`: Extrahiert echte Paare aus Logs
- `scripts/eval_tmps.py`: Evaluiert TMP-S Genauigkeit

Ein vortrainierter Adapter ist verfügbar unter:
`finetune/adapters/qwen4b-tmps-lora-rocm/`

---

## Tests

Das Projekt verwendet pytest. Tests decken ab:
- TMP-S Parsing & Validierung
- Konfiguration
- Patch-Anwendung
- Artefakt-Parsing
- Orchestrator-Loop (mit Mocks)

Ausführen:
```bash
pytest tests/
```

---

## Design-Prinzipien

1. **Determinismus**: Validator läuft mit temperature=0.0 für reproduzierbare Ergebnisse
2. **Separation of Concerns**: Validator (Architekt) und Builder (Ausführer) sind getrennt
3. **Strikte Protokolle**: TMP-S v2.4 erzwingt strukturierte Kommunikation
4. **Retry-Logik**: Automatische Wiederholung bei Fehlern mit Budget-Verwaltung
5. **Audit-Trail**: Jedes Turn wird vollständig persistiert
6. **Sicherheit**: Sandbox-Modus, Path-Traversal-Schutz, keine Binär-Patches

---

## Agent-Strategie: Validator vs. Specialists

### Grundprinzip: Unterschiedliche Trainings-Ansätze

Maestro verwendet **zwei unterschiedliche Strategien** für Validator und Specialists:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  VALIDATOR                    │  SPECIALISTS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Fine-tuned auf TMP-S       │  • Minimal SFT (nur System-Einführung)     │
│  • Strukturierte Outputs      │  • Primär Prompt-basiert                   │
│  • ROCm-stabil via GGUF       │  • Domain-Personas via Context             │
│  • Qwen3-4B + LoRA            │  • Standard Coding-Modelle (3B-7B)         │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Warum dieser Unterschied?

**Validator:** Muss das TMP-S Protokoll exakt beherrschen → **Fine-tuning notwendig**
- Format: `V 2.4|SID|RUN|Turn` etc. muss zuverlässig sein
- Entscheidungslogik (A/R/E/X) muss trainiert sein
- Läuft als GGUF (Q8_0) via Ollama für ROCm-Stabilität

**Specialists:** Generieren nur Code/Diffs → **Prompt-Personas ausreichend**
- Unified Diff Format ist Standard-Fähigkeit von Code-LLMs
- Kein komplexes Protokoll nötig
- Domain-Spezialisierung via System-Prompts (s.u.)

### Specialist Personas (Prompt-basiert)

Anstatt mehrere Modelle zu trainieren, verwenden wir **Contextual Specialization**:

```python
# maestro/llm/prompts.py - Specialist Personas

SPECIALIST_PERSONAS = {
    "imp": "You are an IMPLEMENTATION specialist. Focus on clean, efficient code.",
    "tst": "You are a TEST specialist. Write comprehensive unit tests.",
    "doc": "You are a DOCUMENTATION specialist. Write clear docs and comments.",
    # Zukünftig erweiterbar:
    # "sec": "You are a SECURITY specialist. Focus on auth, crypto, validation.",
    # "db": "You are a DATABASE specialist. Focus on SQL, ORM, migrations.",
}
```

Der Validator wählt den Agent-Code (z.B. `imp`), und das System injiziert die passende Persona.

### Deployment: Alles via Ollama (GGUF)

Um ROCm 6.2 Probleme zu vermeiden:

```
Training Phase:          Inference Phase:
┌─────────────────┐      ┌─────────────────┐
│ HF + Adapter    │  →   │ GGUF (Q8_0)     │
│ (Fine-tuning)   │      │ via Ollama      │
└─────────────────┘      └─────────────────┘
     ROCm-Probleme           Stabil
```

**Workflow:**
1. Validator trainieren (HF + LoRA)
2. Adapter mergen + zu GGUF exportieren (`export_to_gguf.py`)
3. Ollama Modell erstellen (`ollama create`)
4. Config auf `validator_backend: ollama` umstellen

Siehe `Modelfile` und `export_to_gguf.py` für Details.

### Zukünftige Erweiterungen (nicht priorisiert)

| Ansatz | Nutzen | Aufwand | Priorität |
|--------|--------|---------|-----------|
| **Domain Specialists** (sec, db, ui) | Hohe Qualität in Nischen | Training × 3-4 | Später |
| **Tiered Loading** (on-demand) | Weniger VRAM | Komplex | Optional |
| **Mehrere Specialist-Modelle** | Max. Spezialisierung | Training × 6-8 | Nicht geplant |

---

## Zusammenfassung

Maestro ist ein deterministischer Coding-Orchestrator, der:
- Einen **fine-tuned Validator-LLM** zur Workflow-Steuerung verwendet (TMP-S Protokoll)
- **Prompt-basierte Specialist-Agenten** für die Code-Generierung koordiniert
- **GGUF/Ollama** für ROCm-stabile Inference nutzt
- Das TMP-S v2.4 Protokoll für strukturierte Entscheidungen verwendet
- Vollständige Audit-Trails und Retry-Logik bietet
- Lokal mit Ollama oder HuggingFace-Modellen betrieben werden kann
