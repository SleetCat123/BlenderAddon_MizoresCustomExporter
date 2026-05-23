import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import time


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[2]
TEXMAN_RUNNER = PROJECT_ROOT / "addons" / "BlenderAddon_TextureManager" / "tests" / "manual" / "run_window_tests.py"
DEFAULT_BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"


def load_texman_runner():
    spec = importlib.util.spec_from_file_location("texman_run_window_tests", TEXMAN_RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("script")
    parser.add_argument("--blender", default=os.environ.get("BLENDER_EXE", DEFAULT_BLENDER_EXE))
    parser.add_argument("--timeout-sec", type=int, default=240)
    parser.add_argument("--status-file")
    parser.add_argument("--crash-log")
    args = parser.parse_args()

    target_script = (SCRIPT_DIR / args.script).resolve()
    if not target_script.exists():
        raise FileNotFoundError(target_script)

    if not Path(args.blender).exists():
        raise FileNotFoundError(args.blender)

    texman_runner = load_texman_runner()

    log_dir = SCRIPT_DIR / "output_export_sets_flow" / "isolated_window_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = f"{target_script.stem}_{os.getpid()}"
    stdout_path = log_dir / f"{stamp}.out.log"
    stderr_path = log_dir / f"{stamp}.err.log"
    wrapper_path = log_dir / f"{stamp}.cmd"

    cmd = [
        args.blender,
        "--factory-startup",
        "--python",
        str(target_script),
    ]

    original_addon_root = texman_runner._addon_root
    try:
        texman_runner._addon_root = lambda: SCRIPT_DIR.parent
        texman_runner._write_windows_cmd_wrapper(
            cmd,
            wrapper_path=wrapper_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )
        ps_cmd = texman_runner._powershell_isolated_desktop_command(
            wrapper_path=wrapper_path,
            timeout_sec=args.timeout_sec,
        )
        crash_log_path = Path(args.crash_log).resolve() if args.crash_log else None
        status_path = Path(args.status_file).resolve() if args.status_file else None
        crash_log_mtime = None
        if crash_log_path is not None and crash_log_path.exists():
            crash_log_mtime = crash_log_path.stat().st_mtime

        proc = subprocess.Popen(
            ps_cmd,
            cwd=SCRIPT_DIR.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        forced_returncode = None
        while True:
            returncode = proc.poll()
            if returncode is not None:
                break
            if crash_log_path is not None and crash_log_path.exists():
                current_mtime = crash_log_path.stat().st_mtime
                if crash_log_mtime is None or current_mtime > crash_log_mtime:
                    forced_returncode = 201
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=5)
                    break
            if status_path is not None and status_path.exists():
                forced_returncode = 0
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
                break
            time.sleep(0.5)
        stdout_text = proc.stdout.read() if proc.stdout is not None else ""
    finally:
        texman_runner._addon_root = original_addon_root

    combined = []
    for path in (stdout_path, stderr_path):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if text:
            print(text, end="" if text.endswith("\n") else "\n")
            combined.append(text)
    if stdout_text:
        print(stdout_text, end="" if stdout_text.endswith("\n") else "\n")
        combined.append(stdout_text)

    if forced_returncode is not None:
        raise SystemExit(forced_returncode)
    raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
