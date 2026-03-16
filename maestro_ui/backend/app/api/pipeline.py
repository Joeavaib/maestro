import asyncio
import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pathlib import Path

router = APIRouter()

class RunRequest(BaseModel):
    repo_path: str
    request: str

@router.post("/run")
async def start_run_stream(run_req: RunRequest, req: Request):
    """
    Starts the Maestro pipeline as a background process and streams its stdout
    back to the client using Server-Sent Events (SSE).
    """
    repo_path = run_req.repo_path
    request_text = run_req.request

    # This resolves to: /home/joe/Dokumente/projects/Apps/maestro
    # __file__ is maestro_ui/backend/app/api/pipeline.py
    root_dir = Path(__file__).parent.parent.parent.parent.parent.resolve()
    cfg_path = root_dir / "cfg.json"
    cli_path = root_dir / "maestro" / "cli.py"

    cmd = [
        "python3",
        # Force unbuffered output so we stream immediately, line by line
        "-u", 
        str(cli_path),
        "run",
        "--repo", repo_path,
        "--request", request_text,
        "--cfg", str(cfg_path),
        "--forest",
        "--unsafe-local"
    ]

    async def event_generator():
        # Let the client know we are starting
        yield f"data: {json.dumps({'type': 'status', 'content': f'Starting Maestro pipeline in {repo_path}...'})}\n\n"

        process = None
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(root_dir),
                env={"PYTHONUNBUFFERED": "1", "PATH": __import__('os').environ['PATH']}
            )

            async def read_stdout():
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    yield line

            async def check_disconnect():
                while True:
                    if await req.is_disconnected():
                        return True
                    await asyncio.sleep(1)

            stdout_iter = read_stdout()
            
            while True:
                # Race the stdout reading against the disconnect checker
                read_task = asyncio.create_task(anext(stdout_iter, None))
                disconnect_task = asyncio.create_task(check_disconnect())
                
                done, pending = await asyncio.wait(
                    [read_task, disconnect_task], 
                    return_when=asyncio.FIRST_COMPLETED
                )

                if disconnect_task in done and disconnect_task.result() is True:
                    # Client disconnected
                    if process and process.returncode is None:
                        process.terminate()
                    for p in pending:
                        p.cancel()
                    break

                if read_task in done:
                    line = read_task.result()
                    if line is None:
                        # Process finished
                        for p in pending:
                            p.cancel()
                        break
                        
                    decoded_line = line.decode('utf-8', errors='replace')
                    yield f"data: {json.dumps({'type': 'log', 'content': decoded_line})}\n\n"
                    
                    # Cancel the disconnect task for this loop iteration
                    disconnect_task.cancel()

            # Wait for process to finish completely if it hasn't
            if process and process.returncode is None:
                await process.wait()
                
            yield f"data: {json.dumps({'type': 'status', 'content': f'Process exited with code {process.returncode}', 'exit_code': process.returncode})}\n\n"

        except asyncio.CancelledError:
            # This happens if FastAPI cancels the response task
            if process and process.returncode is None:
                process.terminate()
            raise
        except Exception as e:
             yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        finally:
            if process and process.returncode is None:
                process.terminate()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
