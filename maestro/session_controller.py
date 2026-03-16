from __future__ import annotations

import subprocess
import shutil
import json
from pathlib import Path
from typing import Dict, Any

class SessionController:
    """
    Manages the lifecycle of a Maestro run AFTER the AI has finished generating code.
    This acts as the primary API for any future WebUI to manage sandbox results.
    """
    def __init__(self, main_repo_path: Path):
        self.main_repo_path = main_repo_path.resolve()

    def host_preview(self, run_root: str, start_command: str) -> subprocess.Popen:
        """
        Starts a local development server or application directly from the isolated
        production_ready folder. 
        Returns the process object so the WebUI can monitor or kill it later.
        """
        target_dir = Path(run_root) / "final" / "production_ready"
        if not target_dir.exists():
            raise FileNotFoundError(f"Production ready directory not found at {target_dir}")
        
        print(f"[SessionController] Starting preview in {target_dir} using: '{start_command}'")
        # Run in background. The UI server would hold this process and stream its output.
        process = subprocess.Popen(
            start_command, 
            shell=True, 
            cwd=target_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        return process

    def apply_to_main(self, run_root: str) -> bool:
        """
        Takes the final patch from the sandbox and permanently applies it to the user's main repository.
        Equivalent to the user clicking "Accept & Merge" in the UI.
        """
        patch_file = Path(run_root) / "final" / "final_patch.diff"
        if not patch_file.exists():
            raise FileNotFoundError(f"Patch file not found at {patch_file}")
            
        print(f"[SessionController] Applying patch {patch_file} to main repo {self.main_repo_path}...")
        
        # We use git apply to cleanly inject the changes into the working directory
        result = subprocess.run(
            ["git", "apply", str(patch_file)], 
            cwd=self.main_repo_path, 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            print(f"[!] Patch application failed: {result.stderr}")
            return False
            
        print("[✅] Patch successfully applied to main repository.")
        return True

    def discard_run(self, run_root: str, work_repo: str) -> None:
        """
        Completely deletes the isolated workspace and the run artifacts.
        Equivalent to the user clicking "Discard / Delete" in the UI.
        """
        print(f"[SessionController] Discarding run artifacts...")
        
        run_path = Path(run_root)
        work_path = Path(work_repo)
        
        if run_path.exists():
            shutil.rmtree(run_path, ignore_errors=True)
            print(f"[-] Deleted logs and diffs at {run_path}")
            
        # The work_repo is nested inside .maestro/work/... We delete the parent ID folder to be clean.
        if work_path.exists():
            # Get the session ID parent folder to delete the whole tree
            sid_folder = work_path.parent.parent 
            shutil.rmtree(sid_folder, ignore_errors=True)
            print(f"[-] Deleted sandbox environment at {sid_folder}")
            
        print("[✅] Run completely discarded.")

    def format_retry_request(self, original_request: str, user_feedback: str) -> str:
        """
        Utility for the WebUI. If the user wants to retry with changes, this formats 
        a new master prompt that Maestro can understand.
        """
        return (
            f"Original Request: {original_request}\n\n"
            f"User Feedback on Previous Output:\n{user_feedback}\n\n"
            f"Please modify the codebase to address the user's feedback."
        )

