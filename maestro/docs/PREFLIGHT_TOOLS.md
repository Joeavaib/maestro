# Pre-Flight Assistant: Tool-Spezifikation

> Dokumentation aller geplanten Tools für den Pre-Flight Project Manager (1-2B Parameter, CPU-only)

## Design-Prinzip

Der Assistant kompensiert seine kleine Modellgröße durch **deterministische Tools** mit exakten Daten statt Generierung aus Trainingswissen.

---

## 1. Projekt-Kontext Tools

### `get_run_history(project_id: str, limit: int = 10) -> List[RunSummary]`
**Zweck:** Lernt aus vergangenen Iterationen  
**Rückgabe:** Letzte Runs mit Status, Scope, verwendete Worker, Erfolgs-/Misserfolgsmuster  
**Beispiel:** "Letzte 3 Runs waren 3D-Projekte → alle FAILED (OOM). Letzter 2D-Run SUCCESS."

### `get_architecture_decisions(project_id: str) -> List[Decision]`
**Zweck:** Nachvollziehbare Design-Entscheidungen  
**Rückgabe:** Getroffene Architektur-Entscheidungen (ECS vs. OOP, Rendering-Backend, etc.)  
**Beispiel:** "ECS gewählt in Run #5, nicht mehr ändern ohne Begründung."

### `get_active_constraints(project_id: str) -> Constraints`
**Zweck:** Aktuelle Limitierungen tracken  
**Rückgabe:** Budget-Verbleib, Retry-Counts, Blockierungen  
**Beispiel:** "Nur noch 3 E-Lines bis Escalation, 2 Retries verbleibend."

---

## 2. Hardware & Ressourcen Tools

### `check_hardware_compatibility(scope: str, hardware: HardwareProfile) -> CompatibilityReport`
**Zweck:** Realistische Einschätzung vor dem Start  
**Rückgabe:** Passt/nicht passt, geschätzte VRAM-Nutzung, empfohlene Quantisierung  
**Parameter:**
- `scope`: "2d_platformer", "3d_fps", "inventory_system", etc.
- `hardware`: GPU-Modell, VRAM, RAM, CPU

**Beispiel:**
```
Input: "3d_mmo", RX 6800 XT 16GB
Output: ❌ INCOMPATIBLE - Benötigt 32GB+ VRAM für Worker
        Empfohlene Reduktion: "3d_fps_arena" (passt in 14GB)
```

### `estimate_iterations(scope: str, complexity: int) -> Estimate`
**Zweck:** Zeitliche Planung  
**Rückgabe:** Geschätzte TMP-S Iterationen, geschätzte Zeit, Token-Budget  
**Beispiel:** "2D Platformer ≈ 25 Iterationen ≈ 20 Minuten auf 6800 XT"

### `get_worker_registry() -> WorkerCatalog`
**Zweck:** Verfügbare Worker auflisten  
**Rückgabe:** Alle registrierten Worker mit Größe, Fähigkeiten, Hardware-Anforderungen  
**Beispiel:**
```
- ecs_worker (7B, Q4 = 6GB VRAM) - ECS Komponenten-Systeme
- render_2d (3B, Q4 = 2.5GB) - 2D Rendering, Sprite-Batching
- phys_2d (3B, Q4 = 2.5GB) - 2D Physik, Collision
- render_3d (14B, Q8 = 16GB) - 3D Rendering ⚠️ Exklusivmodus nötig
```

---

## 3. Scope-Analyse Tools

### `classify_scope(user_request: str) -> ScopeClassification`
**Zweck:** Vage Anfragen einordnen  
**Rückgabe:** Kategorie (2d/3d/gameplay/system/tool), Komplexität (1-5), Unklarheiten  
**Beispiel:**
```
Input: "Mach ein Spiel wie Mario"
Output: {
  "category": "2d_platformer",
  "complexity": 3,
  "ambiguities": ["Welche Features?", "Welche Engine?", "Umfang?"],
  "suggested_questions": ["2D oder 3D?", "Wie viele Level?", "Combat-System?"]
}
```

### `check_scope_realistic(scope: Scope, constraints: Constraints) -> RealityCheck`
**Zweck:** Sanity-Check vor Commit  
**Rückgabe:** Machbar ja/nein, Risiken, Alternativvorschläge  
**Beispiel:** "Scope 'MMORPG' bei 16GB VRAM: ❌ Unrealistisch. Alternative: 'Multiplayer-Lobby mit 4 Spielern'."

### `decompose_request(request: str) -> List[SubTask]`
**Zweck:** Aufteilung in handhabbare Teile  
**Rückgabe:** Liste von Sub-Aufgaben mit Abhängigkeiten  
**Beispiel:**
```
Input: "RPG mit Inventar, Combat, Quests"
Output: [
  {"task": "ecs_setup", "deps": [], "worker": "ecs_worker"},
  {"task": "inventory", "deps": ["ecs_setup"], "worker": "gameplay"},
  {"task": "combat", "deps": ["ecs_setup"], "worker": "gameplay"},
  {"task": "quests", "deps": ["inventory", "combat"], "worker": "gameplay"}
]
```

---

## 4. Codebase-Analyse Tools

### `analyze_existing_code(project_id: str) -> CodebaseSummary`
**Zweck:** Kontinuität sicherstellen  
**Rückgabe:** Struktur, verwendete Muster, Hauptdateien  
**Beispiel:** "Rust-Projekt, ECS mit Bevy, Rendering mit wgpu. Hauptmodul: src/engine/"

### `check_consistency(request: str, codebase: CodebaseSummary) -> ConsistencyReport`
**Zweck:** Konflikte erkennen  
**Rückgabe:** Passend/nicht passend, notwendige Refactors  
**Beispiel:** "Anfrage: 'React-Komponente hinzufügen' → Codebase ist Vue.js. ⚠️ Inkonsistent!"

### `get_code_patterns(project_id: str) -> List[Pattern]`
**Zweck:** Stil-Konsistenz  
**Rückgabe:** Etablierte Patterns (Naming, Architektur, Testing)  
**Beispiel:** "snake_case, Komponenten in modules/, Tests in tests/unit/"

---

## 5. Prompt-Optimierung Tools

### `compile_super_prompt(request: str, context: Context) -> SuperPrompt`
**Zweck:** Aus vage → präzise  
**Rückgabe:** Strukturierter Prompt mit Constraints, Kontext, Akzeptanzkriterien  
**Output-Format:**
```yaml
super_prompt: |
  [Kontext]
  [Spezifische Anforderung]
  [Akzeptanzkriterien]
  [Einschränkungen]
constraints:
  max_lines: 50
  allowed_imports: ["bevy", "wgpu"]
  forbidden_patterns: ["unsafe", "unwrap()"]
```

### `generate_constraints_yaml(scope: Scope, hardware: HardwareProfile) -> Constraints`
**Zweck:** Validator-Constraints generieren  
**Rückgabe:** YAML mit hard/soft limits, decision-matrix  
**Beispiel:**
```yaml
decision_matrix:
  perfect: {action: "A", max_retries: 0}
  partial: {action: "R", max_retries: 2}
  failed: {action: "X", max_retries: 1}
hard_constraints:
  max_vram_mb: 14336
  max_lines_per_response: 50
```

### `select_prompt_template(type: str, context: Context) -> Template`
**Zweck:** Bewährte Templates wiederverwenden  
**Rückgabe:** Optimiertes Template für den Anwendungsfall  
**Verfügbare Templates:**
- `system_architecture` - ECS/Architektur-Entscheidungen
- `component_impl` - Einzelne ECS-Komponenten
- `rendering_2d` - 2D Rendering-Systeme
- `rendering_3d` - 3D Rendering-Systeme
- `physics` - Physik-Integration
- `ui` - UI-Systeme
- `gameplay` - Gameplay-Logik

---

## 6. Validierung & Quality-Tools

### `validate_syntax(code: str, language: str) -> SyntaxCheck`
**Zweck:** Offensichtliche Fehler früh erkennen  
**Rückgabe:** Syntax-OK, gefundene Fehler, Vorschläge  
**Beispiel:** Prüft Rust-Code auf `cargo check` Kompatibilität ohne Compilation

### `check_dependencies(code: str, allowed: List[str]) -> DependencyCheck`
**Zweck:** Sicherstellen dass nur erlaubte Crates/Module genutzt werden  
**Rückgabe:** Unbekannte Dependencies, Version-Konflikte  
**Beispiel:** "Verwendet 'rand 0.8', Projekt hat 'rand 0.7' → Warnung"

### `estimate_complexity_metrics(code_snippet: str) -> Metrics`
**Zweck:** Komplexität quantifizieren  
**Rückgabe:** Lines, Cyclomatic Complexity, Cognitive Complexity  
**Beispiel:** "Function hat CC=15 → Empfohlene Refaktorierung"

---

## 7. Externe API-Tools

### `fetch_documentation(symbol: str, crate: str) -> DocString`
**Zweck:** Aktuelle API-Dokumentation abrufen  
**Rückgabe:** Docs.rs oder äquivalent  
**Beispiel:** `fetch_documentation("Query", "bevy")` → Aktuelle Bevy Query API

### `search_code_examples(query: str, language: str) -> List[Example]`
**Zweck:** Best Practices finden  
**Rückgabe:** Kuratierte Code-Beispiele  
**Quellen:** docs.rs, GitHub (filterbar), interne Knowledge-Base

### `check_crate_status(crate_name: str) -> CrateInfo`
**Zweck:** Dependencies validieren  
**Rückgabe:** Version, Downloads, Maintenance-Status, bekannte Issues  
**Beispiel:** "Crate 'foo' wurde 3 Jahre nicht aktualisiert, 12 offene Security-Issues"

---

## 8. Interaktive Klärung Tools

### `generate_clarification_questions(request: str, ambiguities: List[str]) -> List[Question]`
**Zweck:** Systematische Anforderungsklärung  
**Rückgabe:** Priorisierte Fragen zur Scope-Reduktion  
**Beispiel:**
```
Input: "Mach ein Spiel"
Output: [
  {"priority": 1, "question": "2D oder 3D?"},
  {"priority": 1, "question": "Welche Platform? (PC/Mobile/Web)"},
  {"priority": 2, "question": "Welcher Genre?"},
  {"priority": 3, "question": "Multiplayer?"}
]
```

### `suggest_scope_reduction(scope: Scope, reason: str) -> List[Alternative]`
**Zweck:** Konstruktive Alternativen bei unrealistischen Requests  
**Rückgabe:** Reduzierte Varianten mit Trade-offs  
**Beispiel:**
```
Input: "MMORPG", Reason: "Hardware zu schwach"
Output: [
  {"scope": "Singleplayer-RPG", "keeps": ["Story", "Quests"], "loses": ["Multiplayer"]},
  {"scope": "Multiplayer-Lobby (4P)", "keeps": ["Multiplayer"], "loses": ["Persistenz", "MMO-Skala"]}
]
```

---

## Tool-Chain Workflow

```
User-Input: "Mach ein Spiel wie Dark Souls"
↓
1. classify_scope() → "3d_action_rpg", complexity=5
2. get_run_history() → Letzte 3D-Projekte FAILED
3. check_hardware_compatibility() → ❌ Nicht machbar auf 16GB
4. suggest_scope_reduction() → 2D-Soulslike vorgeschlagen
5. check_scope_realistic() → ✅ Passt
6. generate_clarification_questions() → "Soll es Kämpfe oder nur Exploration sein?"
↓
[User antwortet]
↓
7. compile_super_prompt() → Strukturierter Prompt
8. generate_constraints_yaml() → Validator-Config
9. Weitergabe an TMP-S v3.0 Validator
```

---

## Implementierungs-Notizen

- **Synchrone Tools:** Hardware-Checks, Code-Analyse (lokal, <10ms)
- **Asynchrone Tools:** Docs-Lookup, Crate-Status (API-Calls, gecached)
- **Stateful Tools:** Projekt-Historie, Architektur-Entscheidungen (SQLite/JSON)
- **Deterministisch:** Keine LLM-Generierung, nur Datenabfrage und Template-Füllung

---

*Stand: 2026-02-28 | Integration geplant mit TMP-S v3.0*
