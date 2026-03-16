from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

# Suppress the harmless urllib3/requests dependency warning from Python 3.14 beta environments
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message="urllib3 .* or chardet .* doesn't match a supported version!", category=UserWarning)
    # The import statement triggers the warning, so we place it here or just suppress globally
    
warnings.filterwarnings("ignore", module="requests")

from maestro.config import RunnerConfig
from maestro.llm import build_specialist_client, build_validator_client
from maestro.orch.orchestrator import Orchestrator
from maestro.orch.forest_orchestrator import ForestOrchestrator
from maestro.session_controller import SessionController

def get_latest_run_id() -> tuple[str, str]:
    """Helper to find the most recent run_id if none is provided."""
    runs_dir = Path("runs")
    if not runs_dir.exists():
        return None, None
        
    all_runs = list(runs_dir.glob("*/*"))
    if not all_runs:
        return None, None
        
    # Sort by modification time (most recent first)
    all_runs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    latest = all_runs[0]
    return latest.parent.name, latest.name


def main() -> None:
    parser = argparse.ArgumentParser(prog="maestro")
    sub = parser.add_subparsers(dest="cmd", required=True)
    
    run = sub.add_parser("run")
    run.add_argument("--repo", required=True)
    run.add_argument("--request", required=True)
    run.add_argument("--cfg", required=True)
    run.add_argument("--sandboxed", action="store_true")
    run.add_argument("--unsafe-local", action="store_true")
    run.add_argument("--forest", action="store_true", help="Use the new Raven/Luna/Trees architecture")

    # ACCEPT command
    accept_parser = sub.add_parser("accept", help="Apply a completed run to the main repository.")
    accept_parser.add_argument("sid", nargs="?", help="Session ID")
    accept_parser.add_argument("runid", nargs="?", help="Run ID")

    # DISCARD command
    discard_parser = sub.add_parser("discard", help="Delete a completed run and its sandbox.")
    discard_parser.add_argument("sid", nargs="?", help="Session ID")
    discard_parser.add_argument("runid", nargs="?", help="Run ID")
    
    # PREVIEW command
    preview_parser = sub.add_parser("preview", help="Run a command inside the isolated production_ready folder.")
    preview_parser.add_argument("sid", nargs="?", help="Session ID")
    preview_parser.add_argument("runid", nargs="?", help="Run ID")
    preview_parser.add_argument("--cmd", required=True, help="Command to run (e.g., 'pytest' or 'npm start')")

    args = parser.parse_args()
    
    if args.cmd in ["accept", "discard", "preview"]:
        sid, runid = args.sid, args.runid
        if not sid or not runid:
            sid, runid = get_latest_run_id()
            if not sid:
                print("[!] No runs found in the 'runs/' directory.")
                sys.exit(1)
            print(f"[*] Auto-selected latest run: {sid}/{runid}")
            
        run_root = str(Path("runs") / sid / runid)
        work_repo = str(Path(".maestro/work") / sid / runid / "repo")
        controller = SessionController(Path("."))
        
        if args.cmd == "accept":
            try:
                controller.apply_to_main(run_root)
            except FileNotFoundError as e:
                print(f"[!] Error: {e}")
                print("[!] The selected run likely failed or did not generate a final patch.")
                sys.exit(1)
        elif args.cmd == "discard":
            controller.discard_run(run_root, work_repo)
        elif args.cmd == "preview":
            print(f"[*] Attempting to preview Run: {sid}/{runid}")
            print("[*] Press Ctrl+C to stop the preview server.")
            try:
                process = controller.host_preview(run_root, args.cmd)
                # Stream the output live to the console
                for line in iter(process.stdout.readline, ''):
                    print(line, end='')
                process.stdout.close()
                process.wait() # Block until user stops it
            except FileNotFoundError as e:
                print(f"[!] Error: {e}")
                print("[!] The selected run likely failed and did not create a 'production_ready' export.")
                sys.exit(1)
            except KeyboardInterrupt:
                print("\n[*] Stopping preview.")
                process.kill()
        sys.exit(0)

    if args.cmd == "run":
        cfg = RunnerConfig.from_json_file(args.cfg)
        if args.sandboxed:
            cfg.execution_mode = "sandboxed"
        if args.unsafe_local:
            cfg.execution_mode = "unsafe-local"

        req_arg = args.request
        req_path = Path(req_arg)
        request_text = req_path.read_text() if req_path.exists() else req_arg

        if args.forest:
            orch = ForestOrchestrator(
                cfg,
                llm_client=build_specialist_client(cfg),
                validator_client=build_validator_client(cfg),
            )
        else:
            orch = Orchestrator(
                cfg,
                llm_client=build_specialist_client(cfg),
                validator_client=build_validator_client(cfg),
            )
        result = orch.run(Path(args.repo), request_text)
        print(result)


if __name__ == "__main__":
    main()
