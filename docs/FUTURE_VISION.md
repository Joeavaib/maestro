# Future Vision: Adaptive Validator Ecosystem

> **Status:** Ideensammlung | **Letzte Aktualisierung:** 2026-02-27
> 
> Dieses Dokument dient als "Living Document" für langfristige Entwicklungsideen,
> Forschungshypothesen und architektonische Visionen für das Maestro-Ökosystem.

---

## 0. Priority Zero: Das "Repetitions-Dilemma"

**Die kritischste Hürde vor jeder weiteren Skalierung.**

### Das Problem
Aktuelle 8B-Modelle agieren oft "gedächtnislos". In langen Inferenz-Ketten (Long Inference) neigen sie dazu, in logische Schleifen zu verfallen:
*   Der Validator kritisiert einen Fehler.
*   Der Worker korrigiert ihn unzureichend.
*   Der Validator gibt in Turn N+1 exakt die gleiche Kritik wie in Turn N.
*   **Resultat:** Stagnation und Verschwendung von Rechenzeit.

### Die Lösung: Iterative Intelligenz
Bevor wir komplexe Planung (v3.0) einführen, muss Maestro die **zeitliche Dimension** beherrschen:
1.  **Turn-Awareness:** Der Validator erkennt Wiederholungen durch Zugriff auf die Historie.
2.  **Strategische Eskalation:** Wenn ein Fehler nach 2 Turns nicht behoben ist, *muss* der Validator die Strategie (E-Lines, B-Lines) ändern, statt sich zu wiederholen.
3.  **State-Caching:** Effiziente Verwaltung des Kontexts (RAM vs. VRAM), um die Historie ohne Performance-Verlust mitzuführen.

---

## 1. Vision: Das "Validator Collective"

### Kernidee
Anstatt eines einzelnen universellen Validators entwickeln wir ein **Ökosystem von Spezialisten-Validatoren**, die:
1. In ihren jeweiligen Domänen (Code, Text, Mathe, Security, etc.) perfektioniert werden
2. Sich durch gegenseitige Bewertung und Wissensdistillation kontinuierlich verbessern
3. Ihr Wissen in einen "Universal Validator" einspeisen

### Analogie
Wie ein **Orchester** aus Spezialisten (Streicher, Bläser, Percussion) unter der Leitung eines Dirigenten entsteht aus der Zusammenarbeit etwas Größeres als die Summe der Einzelteile.

---

## 2. Architektur-Konzept

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         UNIVERSAL VALIDATOR                              │
│                    (Wissensdistillation Layer)                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Synthetisiert domänenübergreifende Validierungs-Patterns       │    │
│  │  aus den Spezialisten via Knowledge Distillation                │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ Wissensaustausch
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (Meta-Controller)                        │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  - Routing: Welcher Spezialist ist für diese Aufgabe bestens?   │    │
│  │  - Konsensfindung: Wie gewichten wir widersprüchliche Bewertungen│   │
│  │  - Distillation: Welche Daten fließen in den Universal-Validator?│   │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    ▲
                    ┌───────────────┼───────────────┐
                    │               │               │
            ┌───────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
            │   CODE       │ │   TEXT      │ │   SECURITY  │
            │  VALIDATOR   │ │  VALIDATOR  │ │  VALIDATOR  │
            │  (3B params) │ │ (3B params) │ │ (3B params) │
            └──────────────┘ └─────────────┘ └─────────────┘
                    │               │               │
              ┌─────┴─────┐    ┌────┴────┐     ┌────┴────┐
              │ Python    │    │ Deutsch │     │ XSS     │
              │ Rust      │    │ Englisch│     │ SQLi    │
              │ JS/TS     │    │ Recht   │     │ Auth    │
              └───────────┘    └─────────┘     └─────────┘
```

---

## 3. Komponenten im Detail

### 3.1 Spezialisten-Validatoren (Domain Experts)

**Konzept:**
- Jeder Spezialist wird auf einer **spezifischen Domäne** trainiert
- Training auf hochwertigen, kuratierten Datensätzen der jeweiligen Domäne
- Kleinere Modelle (3B-7B Parameter) für schnelle Inferenz

**Domänen-Beispiele:**

| Domäne | Fokus | Bewertungskriterien |
|--------|-------|---------------------|
| `code-validator` | Code-Generierung | Syntax, Idiomatic, Performance, Typ-Sicherheit |
| `text-validator` | Text-Generierung | Grammatik, Stil, Faktizität, Bias |
| `math-validator` | Mathematische Lösungen | Korrektheit, Beweisgültigkeit, Notation |
| `security-validator` | Security-relevanter Code | OWASP, Injection-Resistenz, Crypto |
| `arch-validator` | Architektur/Design | Pattern-Konformität, Skalierbarkeit |
| `ux-validator` | UI/UX-Generierung | Accessibility, Consistency, Usability |

**Training pro Domäne:**
```python
# Beispiel: Code-Validator Training
specialist_config = {
    "domain": "python_code",
    "base_model": "qwen2.5-3b",
    "training_data": {
        "source": "curated_python_dataset",  # ~10k hochwertige Samples
        "augmentation": "ast_mutations",      # Syntax-Bäume mutieren
        "quality_threshold": 0.95              # Nur beste Daten
    },
    "validation_rules": [
        "syntax_correctness",
        "type_consistency", 
        "idiomatic_patterns",
        "performance_hints"
    ]
}
```

### 3.2 Der Orchestrator (Meta-Controller)

**Aufgaben:**

1. **Intelligentes Routing**
   ```python
   def route_to_specialist(user_request: str, context: Context) -> Specialist:
       # Analyse der Anfrage
       if is_code_generation(user_request):
           if contains_security_relevant_patterns(user_request):
               return MultiValidator([code_validator, security_validator])
           return code_validator
       elif is_text_generation(user_request):
           return text_validator
       # ...
   ```

2. **Konsensfindung (Consensus Mechanism)**
   - Bei widersprüchlichen Bewertungen mehrerer Spezialisten
   - Gewichtung nach Domänen-Relevanz und historischer Genauigkeit
   - TMP-S v2.4 als "Lingua Franca" für alle Validatoren

3. **Qualitäts-Gate**
   ```python
   def aggregate_decisions(decisions: List[Decision]) -> FinalDecision:
       # Gewichtetes Voting
       weights = calculate_specialist_weights(decisions)
       consensus = weighted_vote(decisions, weights)
       
       # Konflikt-Eskalation
       if disagreement_score(decisions) > THRESHOLD:
           return escalate_to_universal_validator(decisions)
       
       return consensus
   ```

### 3.3 Wissensdistillation (Knowledge Distillation)

**Ziel:** Transferiere Wissen von Spezialisten in den Universal-Validator

**Ansatz: "Teacher-Student" Distillation**

```python
class KnowledgeDistillation:
    """
    Universal Validator lernt von Spezialisten-Ensemble
    """
    
    def distill(self, 
                universal_model: Model,
                specialists: List[Model],
                unlabeled_data: Dataset) -> Model:
        """
        Training auf unlabeled Daten mit "Soft Targets" vom Ensemble
        """
        for batch in unlabeled_data:
            # Soft predictions von allen Spezialisten sammeln
            specialist_logits = []
            for specialist in specialists:
                # Nur wenn der Spezialist für diese Aufgabe kompetent ist
                if specialist.is_competent_for(batch):
                    logits = specialist.predict(batch)
                    specialist_logits.append(logits)
            
            # Ensemble-Konsens als "soft target"
            ensemble_target = aggregate_softmax(specialist_logits)
            
            # Universal-Validator lernt, das Ensemble zu replizieren
            universal_logits = universal_model(batch)
            loss = kl_divergence(universal_logits, ensemble_target)
            
            universal_model.update(loss)
        
        return universal_model
```

**Vorteile:**
- Universal-Validator wird kleiner und schneller als das Ensemble
- Behält aber domänenübergreifende Kompetenz
- Kann neue Domänen durch Transfer Learning erlernen

### 3.4 Gegenseitiges Verbessern (Adversarial Refinement)

**Konzept: "Validator Arena"**

```
┌─────────────────────────────────────────────────────────────┐
│                    VALIDATOR ARENA                          │
│                                                             │
│  Round 1: Spezialist A generiert Code                       │
│           ↓                                                 │
│           Spezialist B validiert und findet Fehler          │
│           ↓                                                 │
│           A lernt aus Fehlern (RLHF)                        │
│                                                             │
│  Round 2: Spezialist B generiert Text                       │
│           ↓                                                 │
│           Spezialist C validiert...                         │
│                                                             │
│  Ziel: Jeder wird durch die Kritik der anderen besser       │
└─────────────────────────────────────────────────────────────┘
```

**Training Loop:**
```python
class AdversarialTraining:
    def train_epoch(self, validators: List[Validator]):
        for validator_a in validators:
            for validator_b in validators:
                if validator_a == validator_b:
                    continue
                
                # A generiert, B kritisiert
                generation = validator_a.generate_challenge()
                critique = validator_b.validate(generation)
                
                # A lernt aus dem Feedback
                validator_a.improve_from_critique(generation, critique)
                
                # B lernt, bessere Kritik zu geben
                validator_b.improve_critique_skill(generation, critique)
```

---

## 4. Daten-Pipeline für Hochwertige Trainingsdaten

### 4.1 Multi-Stage Filtering

```
Rohdaten (z.B. GitHub Commits, Code-Reviews)
    ↓
Stage 1: Heuristische Filter (Syntax-Check, Größe)
    ↓
Stage 2: Spezialisten-Bewertung (nur beste Daten)
    ↓
Stage 3: Menschliche Kuratierung (Gold-Standard)
    ↓
Stage 4: Synthetische Augmentierung (Mutationen)
    ↓
Training-Datensatz für Spezialisten
```

### 4.2 Active Learning

```python
class ActiveLearningPipeline:
    """
    Identifiziere Daten, die den meisten Lerneffekt bringen
    """
    
    def select_high_value_samples(self, pool: Dataset, n: int) -> Dataset:
        # Strategie 1: Unsicherheit des Modells
        uncertain = self.find_low_confidence_predictions(pool)
        
        # Strategie 2: Diversität (Clustering)
        diverse = self.maximize_coverage(pool)
        
        # Strategie 3: Widerspruch im Ensemble
        disagreements = self.find_specialist_disagreements(pool)
        
        # Kombiniere und selektiere
        return self.weighted_selection(uncertain, diverse, disagreements, n)
```

---

## 5. TMP-S v2.4 als Universal-Protokoll

### 5.1 Erweiterung für Multi-Validator-Setup

```
V 2.4|sid|runid|turn|validator_id
A hard4|soft4|verdict|rationale
E dotpath|severity|fix_hint
B pri:agent|action
M meta_validator|weight|confidence    # ← NEU: Meta-Information
C decision|strategy|max_retries|focus
```

### 5.2 Validator-ID Mapping

```python
VALIDATOR_REGISTRY = {
    "code-py": {"model": "qwen2.5-3b-code", "weight": 0.9},
    "code-rs": {"model": "qwen2.5-3b-rust", "weight": 0.85},
    "security": {"model": "qwen2.5-3b-sec", "weight": 0.95},
    "text-de": {"model": "qwen2.5-3b-de", "weight": 0.88},
    "universal": {"model": "qwen2.5-7b-uni", "weight": 0.75},
}
```

---

## 6. Forschungsfragen & Hypothesen

### 6.1 Offene Fragen

1. **Skalierung:** Wie viele Spezialisten sind optimal, bevor der Orchestrator überfordert ist?
2. **Wissensverfall:** Wie verhindern wir "Catastrophic Forgetting" beim Universal-Validator?
3. **Bias:** Entstehen systematische Blindspots durch die Domänen-Einteilung?
4. **Evaluierung:** Wie messen wir die Qualität eines Validators objektiv?

### 6.2 Hypothesen

| Hypothese | Testmethode | Erfolgskriterium |
|-----------|-------------|------------------|
| Ensemble > Single | Benchmark-Vergleich | Ensemble schlägt besten Einzel-Validator um >5% |
| Distillation funktioniert | Universal vs. Ensemble | Universal erreicht >90% der Ensemble-Performance |
| Gegenseitiges Training hilft | Arena-Vergleich | Nach N Runden sind alle besser als vorher |
| Domänen-Spezialisierung lohnt | Latenz/Qualität | Spezialist schneller UND besser als Universal |

---

## 7. Umsetzungs-Roadmap (Vorschlag)

### Phase 1: Foundation (Q2 2026)
- [ ] TMP-S v2.4 Protokoll finalisieren und dokumentieren
- [ ] Basis-Infrastruktur für Multi-Validator-Setup
- [ ] 2-3 Spezialisten-Prototypen (Code, Text, Security)

### Phase 2: Spezialisierung (Q3 2026)
- [ ] Training der ersten Spezialisten-Validatoren
- [ ] Daten-Pipeline für hochwertige Trainingsdaten
- [ ] Erste Version des Orchestrators

### Phase 3: Integration (Q4 2026)
- [ ] Konsensmechanismus implementieren
- [ ] Wissensdistillation Experimente
- [ ] "Validator Arena" für adversariales Training

### Phase 4: Optimierung (Q1 2027)
- [ ] Universal-Validator via Distillation
- [ ] Auto-Routing und Selbst-Optimierung
- [ ] Öffentliche Benchmarks und Evaluation

---

## 8. Technische Anforderungen

### 8.1 Hardware

| Komponente | Spezialist | Orchestrator | Universal |
|------------|------------|--------------|-----------|
| GPU | 1x A10G (24GB) | 1x A100 (40GB) | 2x A100 (80GB) |
| VRAM | 16GB | 32GB | 64GB |
| Training | LoRA/QLoRA | Full-Finetune | Full-Finetune |

### 8.2 Software-Stack

```yaml
# Maestro Ecosystem Stack
base:
  - Python 3.12+
  - PyTorch 2.2+
  - Transformers 4.40+
  
training:
  - PEFT (LoRA, QLoRA)
  - DeepSpeed / FSDP
  - Weights & Biases (Logging)
  
orchestration:
  - Redis (State-Management)
  - FastAPI (API Gateway)
  - Ray (Distributed Training)
  
evaluation:
  - Custom TMP-S Parser
  - Human Feedback Interface
  - Automated Benchmarks
```

---

## 9. Mögliche Kooperationen & Use Cases

### 9.1 Interne Nutzung
- **Code-Review Automatisierung:** Spezialist für Python, Rust, etc.
- **Dokumentations-Validierung:** Text-Validator für technische Docs
- **Security-Scanning:** Sicherheits-Validator für PRs

### 9.2 Externe Kooperationen
- **Universitäten:** Forschung zu Validator-Ensembles
- **Open Source:** Community-getriebene Domänen-Validatoren
- **Enterprise:** Anpassbare Validatoren für Firmen-spezifische Guidelines

---

## 10. TMP-S v3.0 Vision: Der Validator als Project Orchestrator

> **Konzept:** Der Validator wird vom "Gatekeeper" zum "Project Manager" - er erstellt Pläne, weist Worker-Spezialisten zu, und überwacht die Ausführung über Iterationen.

### 10.1 Das Problem mit dem aktuellen Ansatz

**Aktuell (TMP-S v2.4):**
```
User Request → Validator → Worker → Validator → Worker → ... (Ping-Pong)
```
- Validator entscheidet nur "Retry/Accept/Escalate"
- Keine langfristige Planung
- Worker macht eine Sache, dann entscheidet Validator neu

**Limitierung:** Komplexe Projekte (z.B. "Baue ein 2D Platformer") brauchen 50+ Iterationen ohne Gesamtstruktur.

### 10.2 TMP-S v3.0: Multi-Worker Orchestration Protocol

#### Neue Zeilentypen:

```
V 3.0|sid|runid|turn|validator_id
A hard4|soft4|verdict|rationale
E dotpath|severity|fix_hint
B pri:agent|action
P plan_id|phase|total_phases|description    # ← NEU: Plan Header
W worker_id|task_type|est_tokens|deps       # ← NEU: Worker Assignment
M metric|value|threshold                     # ← NEU: Monitoring
C decision|strategy|max_retries|focus
```

#### Erweitertes C-Line Format:
```
C decision|strategy|max_retries|focus|plan_state|next_worker

plan_state: PLANNING|EXECUTING|REVIEW|COMPLETE
next_worker: worker_id oder "validator"
```

### 10.3 Der Workflow: Validator als Project Manager

#### Phase 1: Planung (Planning Phase)

```
User: "Erstelle einen 2D Platformer in C++"

Validator (als Architect):
├── Analysiert Anforderung
├── Erstellt Dekomposition
└── Generiert TMP-S mit PLAN:

V 3.0|game01|run_a|0|architect
A 1111|8897|P|Projekt dekompiliert in 8 Phasen
P platformer_2d|0|8|2D Platformer Entwicklung
W ecs_worker|entity_system|500|none
W ecs_worker|component_base|400|entity_system
W render_worker|sprite_renderer|800|component_base
W physics_worker|collision_system|1000|entity_system
W gameplay_worker|player_controller|600|collision_system
W gameplay_worker|enemy_ai|700|player_controller
W level_worker|tilemap_system|500|sprite_renderer
W ui_worker|hud_system|400|gameplay_systems
B 1:validator|Plane genehmigen und Phase 1 starten
C A|3|5|*|PLANNING|validator
```

#### Phase 2: Ausführung (Execution Phase)

```
Validator genehmigt Plan → Wechsel zu EXECUTING

Turn 1:
V 3.0|game01|run_a|1|validator
A 1111|9999|P|Starte Phase 1: Entity System
W ecs_worker|entity_manager|500|none
B 1:ecs_worker|Implementiere EntityManager mit UUID-Lookup
C R|1|5|ecs|EXECUTING|ecs_worker

→ Worker (ecs_worker) generiert EntityManager

Turn 2:
V 3.0|game01|run_a|2|validator
A 1111|8897|P|EntityManager akzeptiert
M coverage|100|90
M complexity|low|medium
B 1:ecs_worker|Implementiere Component Base Klassen
C R|1|5|ecs|EXECUTING|ecs_worker

→ Worker (ecs_worker) generiert Component Base
```

#### Phase 3: Monitoring & Adaption

```
Wenn Worker abweicht oder Fehler macht:

Turn 5 (Fehler erkannt):
V 3.0|game01|run_a|5|validator
A 1011|6543|H|Collision Detection fehlerhaft
E physics.aabb|H|Bounding Box Berechnung inkorrekt
M test_coverage|45|80
B 1:physics_worker|Korrigiere AABB Berechnung
B 2:validator|Überprüfe Test Coverage
C R|2|4|physics.aabb|EXECUTING|physics_worker

→ Worker korrigiert
→ Validator trackt Metrik "test_coverage"
```

#### Phase 4: Plan-Anpassung (Replanning)

```
Wenn neues Requirement hinzukommt:

Turn 10:
V 3.0|game01|run_a|10|validator
A 1111|8897|P|Neue Anforderung: Multiplayer
P platformer_2d|5|10|Erweitert um Networking
W net_worker|network_base|1000|entity_system
W net_worker|prediction|1200|network_base
B 1:net_worker|Implementiere Client-Server Architektur
C R|3|3|net|PLANNING|net_worker
```

### 10.4 Die Worker-Spezialisten

```
┌─────────────────────────────────────────────────────────────┐
│                    WORKER REGISTRY                          │
├─────────────┬─────────────────┬─────────────────────────────┤
│ Worker ID   │ Domäne          │ Spezialisierung             │
├─────────────┼─────────────────┼─────────────────────────────┤
│ ecs_worker  │ Architecture    │ Entity Component System     │
│ render_2d   │ Graphics        │ 2D Rendering (OpenGL/SDL)   │
│ render_3d   │ Graphics        │ 3D Rendering (Vulkan/GL)    │
│ phys_2d     │ Physics         │ 2D Physics (Box2D-like)     │
│ phys_3d     │ Physics         │ 3D Physics (Bullet-like)    │
│ gameplay    │ Game Logic      │ Player Controllers, AI      │
│ ui_worker   │ Interface       │ HUD, Menus, ImGui           │
│ audio       │ Sound           │ FMOD/OpenAL Integration     │
│ net_worker  │ Networking      │ Multiplayer, Prediction     │
│ io_worker   │ Serialization   │ Save/Load, Asset Pipeline   │
│ math_worker │ Mathematics     │ Linear Algebra, Random      │
│ opt_worker  │ Optimization    │ Profiling, Cache Opt        │
└─────────────┴─────────────────┴─────────────────────────────┘
```

### 10.5 Der Validator als State Machine

```python
class ValidatorOrchestrator:
    def process_turn(self, user_input, current_state):
        # 1. Aktuellen Plan validieren
        if current_state.plan.is_valid():
            # 2. Nächste Task bestimmen
            next_task = current_state.plan.get_next_task()
            
            # 3. Besten Worker für Task auswählen
            worker = self.select_optimal_worker(
                task_type=next_task.type,
                available_workers=WORKER_REGISTRY,
                past_performance=METRICS_DB
            )
            
            # 4. Dependencies prüfen
            deps_satisfied = self.check_dependencies(
                next_task.dependencies,
                completed_tasks=current_state.completed
            )
            
            if not deps_satisfied:
                # Replan: Dependencies müssen zuerst
                return self.create_replan_response()
            
            # 5. TMP-S Response mit Worker Assignment
            return self.build_tmps_response(
                phase=current_state.plan.current_phase,
                worker=worker,
                task=next_task
            )
        else:
            # Plan fehlerhaft → Replanning
            return self.create_new_plan(user_input)
    
    def select_optimal_worker(self, task_type, ...):
        # Berücksichtige:
        # - Historische Performance auf diesem Task-Typ
        # - Aktuelle Auslastung
        # - Modell-Größe vs. Task-Komplexität
        # - User-Präferenzen (z.B. "bevorzuge kleine Modelle")
```

### 10.6 Monitoring & Metriken

```
M coverage|85|90           # Code Coverage: 85%, Target 90%
M complexity|12|10         # Zyklomatische Komplexität: 12, Max 10
M compile_time|45s|60s     # Kompilierzeit OK
M test_pass|45|45          # Alle Tests passen
M perf_fps|58|60           # Performance knapp
M deps_resolved|7|8        # 7/8 Dependencies fertig
```

**Validator reagiert auf Metriken:**
- `coverage < 90%` → Weise `test_worker` zu
- `complexity > 10` → Weise `opt_worker` für Refactoring
- `perf_fps < 60` → Weise `opt_worker` für Profiling

### 10.7 Beispiel: Kompletter GameDev-Zyklus

```
User: "Erstelle einen 2D Platformer"

[PLANNING PHASE]
Validator analysiert → Erstellt 8-Phasen-Plan
→ User bestätigt oder modifiziert Plan

[EXECUTION PHASE - Iteration 1-20]
Turn 1-3:   ecs_worker → Entity System
Turn 4-6:   render_2d  → Sprite Rendering
Turn 7-10:  phys_2d    → Physics & Collision
Turn 11-15: gameplay   → Player & Enemies
Turn 16-18: level      → Tilemap & Levels
Turn 19-20: ui_worker  → HUD & Menus

[REVIEW PHASE]
Validator: "Alle Phasen complete. Metriken:"
M coverage|92|90 ✓
M perf_fps|60|60 ✓
M compile_errors|0|0 ✓
→ Projekt akzeptiert

[COMPLETE]
Validator liefert:
- Komplette Codebase
- Build-Instruktionen
- Architektur-Dokumentation
- Nächste Schritte ("Erweiterungsideen")
```

### 10.8 Vorteile dieses Ansatzes

| Aspekt | TMP-S v2.4 (Aktuell) | TMP-S v3.0 (Vision) |
|--------|---------------------|---------------------|
| **Planung** | Keine, nur reaktiv | Proaktive Dekomposition |
| **Übersicht** | Ping-Pong ohne Kontext | Gesamtplan sichtbar |
| **Worker** | Ein Generic-Worker | Spezialisierte Worker |
| **Monitoring** | Keine Metriken | Kontinuierliche Qualitätsmetriken |
| **Skalierung** | Linear mit Iterationen | Parallelisierbare Tasks |
| **User Control** | Wenig (nur "Retry/Escalate") | Plan-Approval, Modifikation |

### 10.9 Technische Umsetzung

```python
# Erweitertes TMPSRecord
@dataclass
class TMPSRecord_v3:
    v: VLine
    a: ALine
    e: List[ELine]
    b: List[BLine]
    p: Optional[PlanLine]      # Neu
    w: Optional[WorkerLine]    # Neu
    m: List[MetricLine]        # Neu
    c: CLine_v3                # Erweitert

@dataclass
class CLine_v3:
    decision: str
    strategy: int
    max_retries: int
    focus: str
    plan_state: str            # PLANNING/EXECUTING/REVIEW/COMPLETE
    next_worker: str           # Worker-ID oder "validator"
    plan_progress: float       # 0.0 - 1.0
```

### 10.10 Fazit: Von Tool zu Platform

**TMP-S v3.0 verwandelt Maestro von einem "Validator-Tool" in eine "Development Platform":**

- **Nicht mehr:** "Validiere diesen Output"
- **Sondern:** "Entwickle dieses Projekt mit meinem Team von AI-Spezialisten"

Der Validator wird zum **Project Manager**, die Worker zu **Spezialisten**, und TMP-S zum **Kommunikationsprotokoll** für das gesamte Software-Engineering-Ökosystem.

---

## 11. Zusammenfassung

### Die Vision in einem Satz
> Ein **selbstverbesserndes Ökosystem von Spezialisten-Validatoren**, die durch gegenseitige Bewertung und Wissensdistillation einen universellen Super-Validator erschaffen - **von der Validierung einzelner Outputs bis zur Orchestrierung kompletter Projekte mit spezialisierten Worker-Teams.**

### Kernprinzipien
1. **Spezialisierung** über Universalität (für Effizienz)
2. **Kollaboration** über Konkurrenz (für Qualität)
3. **Automatisierung** über manuelle Prozesse (für Skalierung)
4. **Transparenz** über Black-Box (TMP-S Protokoll)
5. **Planung** über Reaktion (Project Orchestration)

---

## Anhang: Glossar

| Begriff | Bedeutung |
|---------|-----------|
| **Validator** | LLM, das Output anderer LLMs bewertet |
| **Orchestrator** | Meta-Controller, der Validatoren koordiniert |
| **Knowledge Distillation** | Übertragung von Wissen von großen auf kleine Modelle |
| **TMP-S** | Token-Minimal Protocol - Structured |
| **Arena** | Adversariales Training durch gegenseitige Bewertung |
| **Ensemble** | Zusammenschluss mehrerer Modelle für bessere Ergebnisse |

---

*Dieses Dokument ist ein "Living Document". Ideen, Kommentare und Erweiterungen sind willkommen!*

---

## 12. Der "Pre-Flight" Project Manager (Außerhalb der Pipeline)

> **Konzept:** Ein separater, leichter Assistant (nicht der Validator!), der als "Prompt Compiler" und "Requirements Engineer" agiert - NOCH BEVOR die teure Pipeline startet.

### 12.1 Das Problem: Garbage In, Garbage Out

**Aktuelle Situation:**
```
User: "Mach ein Spiel"
↓
Pipeline startet → Worker generiert Pong
↓
User: "Nein, ich meinte Witcher 3"
↓
10 teure Iterationen verschwendet
```

**Mit Pre-Flight Manager:**
```
User: "Mach ein Spiel"
↓
Pre-Flight Assistant: "Warte - klären wir zuerst:"
├── Genre? (RPG, FPS, Platformer...)
├── Scope? (2D/3D, Single/Multiplayer)
├── Tech Stack? (C++, Unity, Godot...)
└── Timeline? (GameJam vs. AAA)
↓
User: "2D Platformer, C++, GameJam-Scope"
↓
Assistant generiert: "Super-Prompt" mit Context
↓
Pipeline startet mit KLAREN Requirements
```

### 12.2 Die Architektur: Zwei-Layer System

```
┌─────────────────────────────────────────────────────────────┐
│           LAYER 1: PRE-FLIGHT (Außerhalb Pipeline)          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Project Manager Assistant (~1-2B Modell)           │    │
│  │  • Leichtgewicht, schnell (<100ms Antwort)          │    │
│  │  • Chat-Interface (mehrere Runden möglich)          │    │
│  │  • Zugriff auf Run-History (nicht aktiven Run)      │    │
│  │  • Fokus: Scope, Requirements, Integrität            │    │
│  └─────────────────────────────────────────────────────┘    │
│                          ↓                                   │
│              Generiert: "Compiled Prompt"                    │
│              + Project Context File                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│           LAYER 2: EXECUTION (Pipeline)                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Validator (3B) → Worker (14B) → ...                │    │
│  │  • Teure GPU-Zyklen                                 │    │
│  │  • Arbeitet nur mit validiertem Super-Prompt        │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 12.3 Die Aufgaben des Pre-Flight Managers

#### A. Prompt-Verfeinerung ("Prompt Compiler")

```
User Input: "Mach ein RPG"
↓
Pre-Flight Analysis:
├── VAGUE DETECTED: "RPG" zu unspezifisch
├── IMPLICIT ASSUMPTIONS:
│   ├── 3D? (User hat Bilder von Elden Ring im Kopf)
│   ├── Multiplayer? (Freunde sollen mitspielen)
│   └── Open World? (User denkt an Skyrim)
│
└── CLARIFICATION NEEDED:
    → "Meinst du 2D (Stardew Valley) oder 3D (Skyrim)?"
    → "Singleplayer Story oder Multiplayer?"
    → "GameJam-Scope (1 Woche) oder Production (1 Jahr)?"
```

#### B. Scope-Schätzung & Reality-Check

```
User: "MMO mit 1000 Spielern, eigen Engine, in C++"
↓
Pre-Flight Reality-Check:
⚠️  WARNUNG: Scope übersteigt Hardware-Kapazitäten
    • 14B Worker kann keine Netcode-Architecture für 1000 Spieler
    • Eigen Engine = 2-3 Jahre Entwicklung
    • Empfehlung: 
      - Option A: Verwende Godot/Unity
      - Option B: Reduziere auf "Lobby-basiertes Multiplayer"
      - Option C: Scope auf Singleplayer mit Networked-Physics

User wählt: Option C
↓
Compiled Prompt: "Singleplayer Physics-Puzzle-Game mit 
                  deterministischer Physics für 
                  Replay-System, C++, GameJam-Scope"
```

#### C. Integritäts-Check (Konsistenz mit Projekt-Historie)

```
Pre-Flight Manager hat Zugriff auf:
├── Vorherige Runs (Session-History)
├── Existierende Codebase (wenn fortgeführt wird)
├── Tech-Stack Entscheidungen (warum C++ statt Rust?)
└── Architektur-Entscheidungen (ECS vs OOP)

Beispiel:
User: "Refactor zu Rust"
↓
Pre-Flight: "Letzter Run war C++ mit ECS. 
             Rust-Refactor = Kompletter Rewrite.
             Bist du sicher? (Ja/Nein/Beide behalten)"
```

#### D. "Super-Prompt" Generierung

**Aus:** `"Mach ein 2D Platformer"`

**Wird:**
```yaml
project_type: "2d_platformer"
scope: "gamejam"  # 48h-Entwicklung
language: "cpp"
engine: "custom"  # Eigen Engine, kein Unity

target_platforms: ["windows", "linux"]
key_features:
  - "tilemap_based_levels"
  - "physics_based_movement" 
  - "enemy_ai_simple"
  - "collectibles_system"
  - "2_levels_minimum"

constraints:
  - "single_threaded"  # Kein Multi-Threading nötig für Scope
  - "no_external_assets"  # Prozedurale Geometrie/Sprites
  - "sfml_or_sdl2"  # Einfache Libraries

quality_gates:
  - "compiles_without_warnings"
  - "60fps_minimum"
  - "memory_leak_free"  # Valgrind clean

super_prompt: |
  Erstelle einen 2D Platformer in C++ mit SFML.
  Scope: GameJam (einfach, funktional, nicht über-engeniert).
  
  MUST HAVE:
  - Spieler kann laufen, springen, fallen
  - Mindestens 2 Levels mit Tilemap
  - Ein einfacher Gegner mit Patrol-AI
  - Collectibles (Coins) mit Counter
  
  MUST NOT:
  - Kein über-ambitioniertes Physics-System
  - Kein Partikel-Overkill
  - Kein Audio-System (optional, nur wenn Zeit)
  
  FOKUS: Funktioniert, ist spielbar, compiled.
```

### 12.4 Das "Tool-Augmented" Prinzip: Kleines Modell, Große Fähigkeiten

> **Kernidee:** Der Pre-Flight Assistant muss kein großes Modell sein. Er glänzt durch **Zugriff auf Tools und Kontext**, nicht durch Parameter-Anzahl.

#### Warum ein kleines Modell reicht:

| Fähigkeit | Großes Modell (70B) | Kleines Modell + Tools (1.5B) |
|-----------|--------------------|--------------------------------|
| **Weltwissen** | ✅ Eingebaut | ❌ Muss nachgeschlagen werden |
| **Projekt-Historie** | ❌ Kein Zugriff | ✅ Tool: `get_run_history()` |
| **Scope-Validierung** | ⚠️ Ratet | ✅ Tool: `check_hardware_constraints()` |
| **Code-Analyse** | ⚠️ Generisch | ✅ Tool: `analyze_existing_codebase()` |
| **Latency** | ❌ Langsam (5-10s) | ✅ Schnell (<100ms) |
| **Kosten** | ❌ Teuer | ✅ Fast kostenlos |

#### Die Tool-Box des Pre-Flight Assistants:

```python
class PreFlightTools:
    """
    Tools geben dem kleinen Modell (1-2B) Superkräfte.
    """
    
    # 1. Projekt-Kontext Tools
    def get_run_history(self, project_id: str, limit: int = 10) -> List[Run]:
        """Lade vorherige Runs für dieses Projekt."""
        return db.query("SELECT * FROM runs WHERE project_id = ? ORDER BY timestamp DESC LIMIT ?", 
                       project_id, limit)
    
    def get_codebase_summary(self, project_id: str) -> dict:
        """Analysiere existierenden Code: Lines, Languages, Architecture."""
        return {
            "total_lines": 5000,
            "languages": {"cpp": 80, "hpp": 15, "cmake": 5},
            "architecture": "ECS",  # Erkannt aus Code-Struktur
            "last_modified": "2024-02-27"
        }
    
    def get_architecture_decisions(self, project_id: str) -> List[Decision]:
        """Lade dokumentierte Architektur-Entscheidungen."""
        return [
            {"date": "2024-02-20", "decision": "ECS over OOP", "reason": "Performance"},
            {"date": "2024-02-25", "decision": "SFML over SDL", "reason": "Ease of use"}
        ]
    
    # 2. Validierungs-Tools
    def check_hardware_constraints(self, scope: str, hardware: str) -> Validation:
        """Prüfe ob Scope mit Hardware kompatibel ist."""
        constraints = {
            "rx_6800_xt_16gb": {
                "max_model_size": "14B_Q4",
                "max_context": 4096,
                "estimated_tokens_per_sec": 25
            }
        }
        return self.validate_scope_against_hardware(scope, constraints[hardware])
    
    def estimate_project_complexity(self, requirements: dict) -> Complexity:
        """Schätze Lines of Code, Iterationen, Zeitaufwand."""
        # Basierend auf historischen Daten aus der Run-Datenbank
        similar_projects = self.find_similar_projects(requirements)
        avg_iterations = statistics.mean([p.iterations for p in similar_projects])
        return Complexity(estimated_iterations=avg_iterations * 1.2)
    
    def check_consistency(self, new_request: str, project_id: str) -> Consistency:
        """Prüfe ob neuer Request mit bestehendem Projekt konsistent ist."""
        existing = self.get_architecture_decisions(project_id)
        if "refactor to rust" in new_request.lower():
            if any("cpp" in d.decision.lower() for d in existing):
                return Consistency(
                    consistent=False,
                    warning="Projekt ist C++ - Rust = Kompletter Rewrite",
                    alternatives=["Keep C++", "Gradual migration", "New project"]
                )
    
    # 3. Template-Tools
    def get_prompt_template(self, project_type: str, scope: str) -> Template:
        """Lade optimierte Prompt-Templates für Projekttyp."""
        templates = {
            ("2d_platformer", "gamejam"): "templates/gamejam_2d_platformer.txt",
            ("rest_api", "production"): "templates/production_rest_api.txt"
        }
        return load_template(templates.get((project_type, scope)))
    
    def generate_constraints_yaml(self, compiled_prompt: dict) -> str:
        """Generiere maschinenlesbare Constraints für Validator."""
        return yaml.dump({
            "max_iterations": compiled_prompt["estimated_iterations"],
            "quality_gates": compiled_prompt["must_haves"],
            "forbidden_patterns": compiled_prompt["must_not_haves"],
            "focus_areas": compiled_prompt["architecture_focus"]
        })

class PreFlightAssistant:
    """
    Separater leichter Assistant (~1-2B Parameter)
    GLÄNZT DURCH TOOLS, NICHT DURCH GRÖSSE.
    """
    
    def __init__(self):
        # Klein, schnell, billig - aber mit Tool-Zugriff
        self.model = load_model("qwen2.5-1.5b-instruct")  # Oder phi-2, tinyllama, etc.
        self.tools = PreFlightTools()
        
        # Prompt-Template für Tool-Nutzung
        self.system_prompt = """
        Du bist ein Project Manager Assistant für Software-Entwicklung.
        Deine Aufgabe: User-Intention verstehen und in klare Requirements übersetzen.
        
        WICHTIG: Du hast Zugriff auf TOOLS. Nutze sie!
        - Lade Projekt-Historie mit get_run_history()
        - Prüfe Hardware-Constraints mit check_hardware_constraints()
        - Analysiere Codebase mit get_codebase_summary()
        
        Regeln:
        1. Frage NIEMANDEN nach Scope ohne erst die Historie zu checken
        2. WARN vor unrealistischen Anforderungen (Tool: check_hardware_constraints)
        3. VERWEISE auf frühere Entscheidungen (Tool: get_architecture_decisions)
        4. GENERIERE strukturierte Output-Formate (Tool: generate_constraints_yaml)
        
        Du bist klein (1.5B), aber deine Tools machen dich schlau.
        """
    
    def process_with_tools(self, user_input: str, project_id: str) -> Response:
        # Schritt 1: Hole Kontext MIT TOOLS (nicht aus dem Modell!)
        context = {
            "history": self.tools.get_run_history(project_id, limit=5),
            "codebase": self.tools.get_codebase_summary(project_id),
            "decisions": self.tools.get_architecture_decisions(project_id)
        }
        
        # Schritt 2: Analysiere mit Kontext
        analysis = self.model.analyze(user_input, context=context)
        
        # Schritt 3: Validiere Scope MIT TOOL (nicht raten!)
        if analysis.suggests_scope:
            validation = self.tools.check_hardware_constraints(
                scope=analysis.suggested_scope,
                hardware=self.get_user_hardware(project_id)
            )
            if not validation.feasible:
                return self.generate_scope_warning(validation)
        
        # Schritt 4: Generiere kompilierten Prompt
        compiled = self.compile_prompt(analysis, context)
        constraints_yaml = self.tools.generate_constraints_yaml(compiled)
        
        return Response(
            super_prompt=compiled.text,
            constraints=constraints_yaml,
            requires_approval=True
        )
```

#### Das "Tool-Use" Pattern (ähnlich wie GPT-Function Calling):

```
User: "Mach ein Spiel"
↓
Assistant denkt:
"User will ein Spiel. Ich weiß nicht welches. 
 Aber ich sehe: Dieser User hat bereits 5 Runs.
 Tool: get_run_history('user_123', limit=3)"
↓
Tool gibt zurück:
- Run 1: "Pong in Python" ✓ Success
- Run 2: "Snake in C++" ✓ Success  
- Run 3: "3D RPG in C++ mit Unity" ✗ Failed (Scope zu groß)
↓
Assistant nutzt Tool-Ergebnis:
"Ich sehe du hast Pong und Snake gemacht - beide erfolgreich!
 Aber der 3D RPG Versuch ist gescheitert (Scope zu groß für deine Hardware).

 Für dein nächstes Projekt empfehle ich:
 → 2D Platformer ( nächste Komplexitätsstufe nach Snake)
 → C++ (deine bevorzugte Sprache)
 → GameJam-Scope (realistisch für 1 Wochenende)

 Einverstanden?"
↓
User: "Ja!"
↓
Assistant nutzt Template-Tool:
Template: get_prompt_template("2d_platformer", "gamejam")
↓
Generiert: Super-Prompt + Constraints YAML
```

#### Warum das funktioniert:

1. **1.5B Modell + Tool = 70B Modell ohne Tool**
   - Das 70B Modell hat Weltwissen, aber keinen Zugriff auf DEINE Projekt-Daten
   - Das 1.5B Modell + Tools hat Zugriff auf genau die Daten, die zählen

2. **Deterministische Validierung**
   - `check_hardware_constraints()` gibt harte Fakten
   - Kein "Ich denke das könnte zu groß sein"
   - Sondern: "Deine 6800 XT hat 16GB. 14B Q4 braucht 12GB. 
              Verbleibend: 4GB für KV-Cache. 
              Max Context: 4096 Tokens. 
              Schätzung: 25 Iterationen = 45 Minuten."

3. **Konsistenz über Zeit**
   - Das Modell vergisst nach dem Turn
   - Die Tools speichern Entscheidungen dauerhaft
   - "Du hast letzte Woche ECS gewählt. Willst du wirklich zu OOP wechseln?"

### 12.6 Technische Implementierung (vereinfacht)
    
    def process_user_intent(self, raw_prompt: str, project_id: str) -> CompiledPrompt:
        # 1. Lade Projekt-Kontext
        context = self.load_project_context(project_id)
        
        # 2. Analysiere Raw Prompt
        analysis = self.analyze_prompt(raw_prompt, context)
        
        # 3. Wenn Vague/Unclear → Interaktive Klärung
        if analysis.confidence < 0.8:
            return self.generate_clarification_questions(analysis)
        
        # 4. Generiere Super-Prompt
        super_prompt = self.compile_prompt(raw_prompt, context, analysis)
        
        # 5. Reality-Check gegen Hardware/Constraints
        if not self.reality_check(super_prompt):
            return self.generate_scope_warning(super_prompt)
        
        # 6. User-Approval
        return self.present_for_approval(super_prompt)
```

#### Der Workflow:

```
1. User öffnet Maestro CLI/GUI
2. Pre-Flight Assistant startet (instant, ~50MB RAM)
3. User tippt: "Mach ein Spiel"
4. Assistant antwortet:
   "Cool! Ein paar Fragen für den Scope:
   
   [1] Genre: Platformer, RPG, FPS, Strategy?
   → User: Platformer
   
   [2] 2D (Super Meat Boy) oder 3D (Mirror's Edge)?
   → User: 2D
   
   [3] Engine: Unity (einfach) oder Eigen-Code (lernintensiv)?
   → User: Eigen-Code in C++
   
   [4] Timeline: GameJam-Wochenende oder längeres Projekt?
   → User: GameJam
   
   Perfekt! Ich compile das zu einem Super-Prompt für die Pipeline.
   Schätzung: ~15 Iterationen, 20-30 Minuten auf deiner 6800 XT.
   
   [START PIPELINE] [MODIFY] [SAVE FOR LATER]"
```

### 12.5 Integration mit TMP-S v3.0

Der Pre-Flight Manager generiert die **initiale Plan-Line (P)** für den Validator:

```
Pre-Flight Output → Wird zu TMP-S v3.0 Input:

V 3.0|platformer_jam|run_001|0|preflight
A 1111|9999|P|Projekt initialisiert und scope-validiert
P platformer_2d_jam|0|5|GameJam 2D Platformer in C++
W ecs_worker|player_controller|400|none
W render_2d|tilemap_renderer|600|none
B 1:validator|Initialisiere Projekt-Architektur
B 2:user|Review und Bestätigung
C A|0|0|project_setup|PLANNING|validator

[User bestätigt]
↓
Pipeline startet mit validiertem Super-Prompt
```

### 12.6 Vorteile des Two-Layer Systems

| Aspekt | Ohne Pre-Flight | Mit Pre-Flight |
|--------|----------------|----------------|
| **Kosten** | 20 Iterationen "falscher" Scope | 5 Klärungs-Runden (Text, billig) |
| **User Experience** | Frustrierend, trial-and-error | Dialog, Guidance, sicher |
| **Pipeline Effizienz** | 30% der GPU-Zyklen verschwendet | 95% nutzbare Iterationen |
| **Projekt Erfolg** | Hohe Abbruchrate | Klare Expectations, realistischer Scope |
| **Lernen** | User lernt nicht | Assistant lehrt Scope/Architecture |

### 12.7 Fazit: Die "Human-in-the-Loop" Schicht

Der Pre-Flight Manager ist die **Brücke zwischen menschlicher Vageheit und maschineller Präzision**:

- **Nicht:** "AI macht alles alleine"
- **Sondern:** "AI hilft dem Menschen, klare Instructions zu formulieren"

Das ist der Unterschied zwischen:
- ❌ "Prompt Engineering als Dark Art"
- ✅ "Structured Conversation mit intelligentem Assistant"

**Und das Beste:** Er läuft außerhalb der teuren Pipeline - auf der CPU, schnell, jederzeit verfügbar.

---

## 13. Zusammenfassung der Gesamtvision

### Die Drei Säulen von Maestro

```
┌─────────────────────────────────────────────────────────────┐
│  SÄULE 1: PRE-FLIGHT (Project Manager)                      │
│  → Leichtgewicht, schnell, interaktiv                       │
│  → Scope, Requirements, Super-Prompt Generierung            │
│  → Läuft auf CPU, immer verfügbar                           │
├─────────────────────────────────────────────────────────────┤
│  SÄULE 2: ORCHESTRATION (Validator v3.0)                    │
│  → Project Planning, Worker Assignment, Monitoring          │
│  → TMP-S Protocol, strukturierte Entscheidungen             │
│  → Läuft auf GPU (3B), schnelle Iterationen                 │
├─────────────────────────────────────────────────────────────┤
│  SÄULE 3: EXECUTION (Worker Spezialisten)                   │
│  → Domänen-spezifische Implementation                       │
│  → C++ Code, Assets, Systeme                                │
│  → Läuft auf GPU (14B), intensive Berechnungen              │
└─────────────────────────────────────────────────────────────┘
```

**Das Ziel:** Ein vollständiges AI-gestütztes Software-Engineering-Ökosystem - von der Idee bis zum Produkt, strukturiert, transparent, effizient.

---

*Dieses Dokument ist ein "Living Document". Ideen, Kommentare und Erweiterungen sind willkommen!*
