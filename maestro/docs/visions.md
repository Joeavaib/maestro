# 🦅 The Forest Architecture: Raven, Luna & The Trees

Diese Vision beschreibt die Evolution des Orchestrierungssystems weg von einer starren, deterministischen State-Machine (TMP-S) hin zu einer dezentralen, asynchronen Agenten-Pipeline. Das Ziel ist es, "Validator Fatigue" zu eliminieren, Token-Kosten durch chirurgischen Kontext zu senken und die Erfolgsquote durch lokale Retry-Loops zu maximieren.

---

## 🏗️ Das Trio-Konzept

Das System teilt sich in drei hochspezialisierte Rollen auf, die sequenziell (und teilweise parallel) interagieren:

### 1. 🦅 Raven (The Planner & Architect)
**"Kräht in den Wald und gibt die Richtung vor."**
*   **Verantwortung:** Versteht das übergeordnete Ziel des Users und zerlegt es in einen "Forest Plan" (eine Liste von unabhängigen Sub-Tasks).
*   **Output:** Generiert pro Sub-Task präzise **Keywords & Intents** (z. B. "Schreibe die API-Route für User-Auth", "Optimiere die DB-Query in Zeile 40").
*   **Vorteil:** Raven muss sich nicht mehr mit Syntax, Formatierungen (B-Lines, C-Lines) oder dem Managen von Retries herumschlagen. Raven ist rein strategisch.

### 2. 🧲 CXM (The Context Machine - Die Brücke)
**"Sammelt den Boden für die Bäume."**
*   **Integration:** Das externe Projekt `cxm` wird über einen optimierten CLI-Call eingebunden.
*   **Der "Harvest"-Modus:** Statt eines interaktiven Dialogs nutzt das System einen direkten Call:
    ```bash
    cxm harvest "<Task-Keywords>" --intent "<Task-Intent>" --output-format "context-block"
    ```
*   **Funktion:** Dieser Befehl triggert das Hybrid-RAG in CXM. Es identifiziert die betroffenen Dateien im Hintergrund (`File Backgrounds`), extrahiert relevante Code-Snippets und formatiert sie als injizierbaren Kontext-Block.
*   **Ergebnis:** Ein maßgeschneiderter, kontext-reicher aber token-effizienter Prompt für die Trees. Luna nimmt diesen Output und setzt ihn als "Background Info" über die eigentliche Coding-Aufgabe.

---

## 🛠️ Technische Umsetzung (Bash-Pipeline)

Die Kommunikation zwischen Luna, CXM und den Trees erfolgt über standardisierte Unix-Pipes oder temporäre Artefakte:

1.  **Raven-Plan extrahieren:**
    `Raven` -> `forest_plan.json`
2.  **Kontext-Harvesting (pro Task):**
    ```bash
    # Luna ruft CXM auf, um den Boden für Tree X zu bereiten
    CONTEXT=$(cxm harvest "auth_logic.py, jwt_helper" --intent "add_refresh_token")
    ```
3.  **Tree-Injektion:**
    Luna kombiniert den `CONTEXT` mit dem `Specialist-Prompt` und sendet ihn an das Coder-Modell (z.B. Qwen2.5-Coder oder DeepSeek-V3).
4.  **Hook-Validierung:**
    Luna führt den vom Tree generierten Code aus und validiert ihn gegen den `Hook` (z.B. `pytest tests/test_auth.py`).

### 3. 🌕 Luna (The Monitor & Orchestrator)
**"Erleuchtet den Wald, überwacht die Ausführung und initiiert Retries."**
*   **Verantwortung:** Luna nimmt den Forest Plan von Raven (angereichert durch CXM) und delegiert ihn an die Trees. Sie ist die unerbittliche Wächterin der Qualität.
*   **Hooks:** Luna definiert und überwacht die Erfolgskriterien (Hooks). Das können Unit-Tests, Linter-Checks, oder kleine semantische LLM-Prüfungen sein.
*   **Lokale Retries:** Wenn ein Tree scheitert, meldet Luna den Fehler (Compiler-Error, Test-Fail) direkt an den Tree zurück und initiiert einen Retry (z.B. max 3 Versuche). 
*   **Schutz:** Raven wird erst wieder kontaktiert, wenn Luna trotz aller Retries scheitert (Eskalation) oder die gesamte Kette erfolgreich durchlaufen wurde.

### 4. 🌲 The Trees (The Specialist Coders)
**"Wachsen im Wald und erledigen die Arbeit."**
*   **Verantwortung:** Reine Ausführung. Ein Tree ist ein Coder-LLM, das den durch CXM perfekten Prompt (Aufgabe + Dateikontext) erhält.
*   **Vervielfältigung (Parallelisierung):** Für komplexe Hooks kann Luna mehrere Trees (verschiedene Modelle oder verschiedene Temperaturen) *parallel* spawnen. Der Tree, der den Hook als Erster erfolgreich passiert, gewinnt (MCTS-ähnlicher Ansatz).
*   **Fokus:** Trees müssen das Gesamtprojekt nicht kennen. Sie schreiben nur die Funktion, die verlangt wird, und reparieren sie basierend auf Lunas Fehlermeldungen.

---

## 🔄 Der Workflow (Beispiel)

1. **User Request:** "Mach die Funktion X schneller und thread-safe."
2. **Raven Plan:** 
   - Task 1: Lock-Mechanismus in `x.py` einbauen (Keywords: "Thread lock, mutex").
   - Task 2: Schleife in `x.py` vektorisieren (Keywords: "Optimize loop, numpy").
3. **CXM Contexting:** Das System holt via `cxm` für Task 1 & 2 exakt die relevanten Klassen aus `x.py` und den dazugehörigen Tests.
4. **Luna Delegation:** Luna startet Tree A für Task 1 und Tree B für Task 2.
5. **Tree Execution & Hooks:** 
   - Tree A liefert Code. Luna checkt den Hook (Linting + Run Test). Test schlägt fehl (Deadlock).
   - Luna gibt Fehler an Tree A zurück (Retry 1/3). Tree A repariert. Hook passt.
6. **Completion:** Luna meldet an Raven: "Wald erfolgreich gewachsen."

## 🎯 Warum dieses Design?

*   **Keine Validator-Fatigue:** Das Architekten-Modell (Raven) ermüdet nicht an Formatierungs-Fehlern.
*   **Skalierbarkeit:** Durch die Trees lassen sich Aufgaben hervorragend parallelisieren.
*   **Präzision durch CXM:** Die Einbindung der ContextMachine löst das Halluzinations- und Token-Limit-Problem der Arbeiter-Agenten. Jeder Tree bekommt genau die Dateien, die er braucht.
