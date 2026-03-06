# 🦅 The Forest Architecture: Raven, Luna & The Trees (Evolution v2)

Diese Vision beschreibt die Evolution des Orchestrierungssystems weg von einer starren, deterministischen State-Machine (TMP-S) hin zu einer dezentralen, asynchronen Agenten-Pipeline. Das Ziel ist es, "Validator Fatigue" zu eliminieren, Token-Kosten durch chirurgischen Kontext zu senken und die Erfolgsquote durch lokale Retry-Loops zu maximieren.

---

## 🏗️ Das Evolutions-Trio (Erkenntnisse & Upgrades)

Das System teilt sich in drei hochspezialisierte Rollen auf, die wir in jüngsten Testläufen signifikant geschärft haben:

### 1. 🦅 Raven (The Planner & Architect)
**"Kräht in den Wald und gibt die Richtung vor."**
*   **Ist-Zustand:** Raven zerteilt Ziele in isolierte Nano-Tasks. Dies funktioniert hervorragend für lineare Feature-Erweiterungen.
*   **Neue Erkenntnis:** Lineare Task-Listen scheitern bei globalen Refactorings (Der Domino-Effekt). Wenn Task 1 eine Core-API ändert, brechen Task 2-20.
*   **Lösungsvorschlag (Vision v3):** Raven muss von einer flachen JSON-Liste zu einem **Directed Acyclic Graph (DAG)** wechseln. Tasks müssen Abhängigkeiten (`depends_on`) definieren. Erst wenn das "Database Core" (Task 1) kompiliert, dürfen die "Route Handlers" (Task 2 & 3) starten.

### 2. 🌕 Luna (The Monitor, Triage & Orchestrator)
**"Erleuchtet den Wald, überwacht die Ausführung und heilt Fehler."**
*   **Ist-Zustand:** Luna überwacht die Ausführung (`Luna-Shield`) und fängt Endlosschleifen ab. Sie wählt dynamisch das richtige Worker-Modell (`Light`, `Medium`, `Heavy`) basierend auf Task-Komplexität und Retry-Stufe.
*   **Neue Erkenntnis (Die "Gedächtnis-Brücke"):** Rohe Stacktraces überfordern kleine Worker-Modelle. 
*   **Der Triage-Durchbruch:** Luna agiert nun als **Triage-Analyst**. Anstatt dem Tree einen 50-zeiligen Rust-Compiler-Error zuzuwerfen, analysiert der `luna_monitor` (ein schnelles 8b-Reasoning-Modell) den Fehler und extrahiert eine **chirurgische Fix-Instruktion** (z.B. "Der `#[arg]` Tag fehlt in `cli.rs`"). Der Tree erhält nur noch diese komprimierte Essenz.

### 3. 🌲 The Trees (The Specialist Coders)
**"Wachsen im Wald und erledigen die Arbeit."**
*   **Ist-Zustand:** Rein auf Ausführung getrimmte Modelle, die streng gezwungen werden, `<rationale>` Tags vor dem Code zu schreiben, um "Chain-of-Thought" zu erzwingen (selbst bei Non-Reasoning Modellen).
*   **Neue Erkenntnis:** Modelle leiden an kreativer Formatierungs-Wut (erfinden `<File>`, `[file]`, etc.). Der Parser muss kugelsicher sein, und das System-Prompting extrem restriktiv.
*   **Das Rescue-Team:** Wenn ein Medium-Tree dreimal scheitert, eskalieren wir an den **Heavy-Planner (Phi4)**. Dieser bekommt von Luna ein "Rescue Briefing" (inkl. Triage-Analyse) und baut einen deterministischen Bauplan für den Heavy-Worker (`TeichAI/Qwen3-14B`).

### 4. 🧲 CXM (The Context Machine - Intelligent Harvesting)
**"Sammelt gezielt, was fehlt."**
*   **Ist-Zustand:** CXM sucht basierend auf initialen Keywords.
*   **Die Evolution (Dynamic Harvesting):** Bei einem Fehler generiert Luna eine **neue, maßgeschneiderte Suchanfrage** für CXM, basierend auf dem Fehler. Wenn der Tree ein Trait nicht findet, sucht CXM gezielt nach der Definition dieses Traits in der Codebase, um das "Rescue Team" mit dem fehlenden Wissen zu versorgen.

---

## 🚀 Roadmap to "Full Dev": Mastering the Modern Stack

Um von isolierten Single-File Änderungen zu kompletten, skalierbaren Applikationen zu kommen, fokussieren wir die Entwicklung auf drei strategische Säulen:

### 1. Die Technologische Speerspitze
Wir meistern Stacks, die Typsicherheit und deterministische Validierung fördern:
*   **Rust (Backend & CLI):** Nutzung von `axum`, `tokio` und `sqlx`. Der Rust-Compiler ist unser bester Lehrer für präzise Luna-Triage.
*   **Python 3.12+ (Logic & Data):** Einsatz von `FastAPI`, `Pydantic v2` und `SQLAlchemy 2.0`. Fokus auf **Dependency Injection**, um Trees maximale Isolation zu ermöglichen.
*   **TypeScript & Next.js 15 (Frontend):** Typsichere Brücken zwischen UI und API.

### 2. Architektonische Meilensteine (Patterns)
Full Dev erfordert, dass Raven nicht nur "Code" plant, sondern "Architektur":
*   **Schema-First Design:** Raven plant immer zuerst das Datenmodell (Contract), bevor die Logik-Trees starten.
*   **Test-Driven Development (TDD):** Einführung von **Semantic Assertion Tasks**. Ein Feature-Task gilt erst als abgeschlossen, wenn der zugehörige (parallel oder vorab erstellte) Test-Task "Grün" meldet.
*   **DevOps Integration:** Automatisches Planen von `Dockerfiles`, `GitHub Actions` und Datenbank-Migrationen (`Alembic`/`Prisma`).

### 3. Full Dev Workflow (Beispiel)
Ein typischer Forest-Plan für eine neue Applikation sieht künftig so aus:
1.  **Contract-Task:** Definiere API-Schema & DB-Models (Pydantic/Rust Structs).
2.  **Infrastructure-Task:** Erstelle Docker-Setup & Migrations-Skelett.
3.  **Assertion-Task:** Schreibe fehlgeschlagene Integrationstests (TDD).
4.  **Feature-Tasks:** Implementiere die Logik in isolierten Schichten.
5.  **Validation-Task:** Luna prüft den "Linker-Status" (Sind alle neuen Files im Projekt-Root registriert?).

---

## 🚧 Aktuelle Grenzen & Lösungsvorschläge (Vision v3)

### 1. Semantische Endlosschleifen ("Blind-Spot" Bugs)
*   **Problem:** Code kompiliert (`cargo check` grün), tut aber logisch das Falsche. 
*   **Lösung:** **Semantic Assertion Tasks** (siehe oben). Luna darf einen Feature-Task erst als "A" werten, wenn der zugehörige Test-Task "Grün" meldet.

### 2. Projekt-übergreifendes Datei-Management
*   **Problem:** Trees vergessen oft Module in Wurzel-Dateien einzutragen (z.B. `mod scanner;`).
*   **Lösung:** Luna führt nach jedem Patch einen **"Linker-Check"** durch. Wenn eine neue Datei vom AST nicht erfasst wird, triggert Luna automatisch einen "Linker-Task".

### 3. Starre Linearität verhindert echten Speed
*   **Problem:** Luna iteriert streng sequenziell.
*   **Lösung:** Sobald Raven den DAG (Directed Acyclic Graph) implementiert hat, wird Lunas Kernschleife parallelisiert. Unabhängige Tasks werden gleichzeitig an verschiedene Ollama-Instanzen gesendet.

---

## 🎯 Warum dieses Design gewinnt

Durch die **Kompaktierung des Fehlerkontexts**, das **gezielte RAG (CXM)** und den Fokus auf **Schema-First Architektur** halten wir den "Noise" im Prompt minimal. Die kleinen Trees bleiben schnell und fokussiert, während die großen Reasoning-Modelle nur dann Rechenzeit beanspruchen, wenn echte analytische Rettungsarbeit nötig ist. Das ist die perfekte Balance aus Speed und Tiefe auf dem Weg zum Full Dev Agenten.
