"""Chess Trainer Agent — single entry point.

Usage:
    python run.py              # start backend + frontend
    python run.py --backend    # backend only
    python run.py --check      # health check only (no start)
"""

import argparse
import os
import signal
import subprocess
import sys
import time

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
DIM = "\033[2m"
RESET = "\033[0m"

BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "5173"))
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(PROJECT_ROOT, ".venv", "bin", "python3")


def _get_python():
    """Return the venv Python if available, otherwise sys.executable."""
    if os.path.isfile(VENV_PYTHON):
        return VENV_PYTHON
    return sys.executable


def check(label, ok, detail=""):
    status = f"{GREEN}OK{RESET}" if ok else f"{RED}FAIL{RESET}"
    msg = f"  [{status}] {label}"
    if detail:
        msg += f" {DIM}({detail}){RESET}"
    print(msg)
    return ok


def run_health_checks():
    """Check all prerequisites and running services."""
    print(f"\n{'='*50}")
    print("  Chess Trainer Agent — Health Check")
    print(f"{'='*50}\n")

    all_ok = True

    # 1. Environment variables
    print("Environment:")
    for var, required in [
        ("STOCKFISH_PATH", True),
        ("LICHESS_TOKEN", True),
        ("LICHESS_USERNAME", True),
        ("ANTHROPIC_API_KEY", True),
    ]:
        val = os.getenv(var, "")
        if required:
            ok = bool(val)
            detail = f"{val[:8]}..." if ok and "KEY" in var or "TOKEN" in var else (val or "missing")
            all_ok &= check(var, ok, detail)
        else:
            check(var, True, val or "default")

    # 2. Stockfish binary
    print("\nBinaries:")
    sf_path = os.getenv("STOCKFISH_PATH", "bin/stockfish")
    sf_exists = os.path.isfile(sf_path) and os.access(sf_path, os.X_OK)
    all_ok &= check("Stockfish", sf_exists, sf_path if sf_exists else f"not found at {sf_path}")

    # 3. Database
    print("\nDatabase:")
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./chess_trainer.db")
    db_path = db_url.split("///")[-1] if "sqlite" in db_url else db_url
    db_exists = os.path.isfile(db_path)
    all_ok &= check("Database file", db_exists, db_path)

    if db_exists:
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT COUNT(*) FROM games")
            game_count = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT engine_status, COUNT(*) FROM games GROUP BY engine_status"
            )
            statuses = {r[0]: r[1] for r in cursor.fetchall()}
            conn.close()

            check("Games", True, f"{game_count} total")
            for status, count in sorted(statuses.items()):
                label = "complete" if status == "complete" else status
                check(f"  engine_{label}", status != "failed", f"{count}")
        except Exception as e:
            all_ok &= check("Database readable", False, str(e))

    # 4. Registry
    print("\nRegistry:")
    reg_path = os.getenv("REGISTRY_PATH", "registry/patterns.yaml")
    reg_exists = os.path.isfile(reg_path)
    all_ok &= check("Pattern registry", reg_exists, reg_path)

    if reg_exists:
        try:
            import yaml
            with open(reg_path) as f:
                registry = yaml.safe_load(f)
            version = registry.get("registry_version", "?")
            count = len(registry.get("patterns", []))
            check("Registry loaded", True, f"v{version}, {count} patterns")
        except Exception as e:
            all_ok &= check("Registry parse", False, str(e))

    # 5. Frontend
    print("\nFrontend:")
    fe_dir = os.path.join(PROJECT_ROOT, "frontend")
    node_modules = os.path.join(fe_dir, "node_modules")
    all_ok &= check("node_modules", os.path.isdir(node_modules),
                     "run 'cd frontend && npm install'" if not os.path.isdir(node_modules) else "installed")

    # 6. Running services
    print("\nServices:")
    backend_up = _check_port(BACKEND_PORT)
    check("Backend", backend_up,
          f"http://localhost:{BACKEND_PORT}" if backend_up else "not running")

    frontend_up = _check_port(FRONTEND_PORT)
    check("Frontend", frontend_up,
          f"http://localhost:{FRONTEND_PORT}" if frontend_up else "not running")

    # 7. Pipeline processes
    print("\nPipeline:")
    engine_running = _process_running("run_engine.py")
    check("Engine analysis", engine_running or True,
          "running" if engine_running else "not running")

    pipeline_running = _process_running("run_pipeline.py")
    check("Pipeline (annotation/conditions)", pipeline_running or True,
          "running" if pipeline_running else "not running")

    print(f"\n{'='*50}")
    if all_ok:
        print(f"  {GREEN}All checks passed{RESET}")
    else:
        print(f"  {RED}Some checks failed — see above{RESET}")
    print(f"{'='*50}\n")

    return all_ok


def _check_port(port):
    """Check if a port is in use."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def _process_running(script_name):
    """Check if a Python script is running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", script_name],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def _kill_port(port):
    """Kill any process listening on the given port. Returns True if something was killed."""
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True,
        )
        pids = result.stdout.strip().split()
        if not pids or not pids[0]:
            return False
        for pid in pids:
            try:
                os.kill(int(pid), signal.SIGTERM)
            except (ProcessLookupError, ValueError):
                pass
        # Wait for port to free up
        for _ in range(10):
            if not _check_port(port):
                return True
            time.sleep(0.5)
        # Force kill if still holding
        for pid in pids:
            try:
                os.kill(int(pid), signal.SIGKILL)
            except (ProcessLookupError, ValueError):
                pass
        time.sleep(0.5)
        return True
    except Exception:
        return False


def start_app(backend_only=False):
    """Start backend and optionally frontend."""
    from dotenv import load_dotenv
    load_dotenv()

    print(f"\n{GREEN}Starting Chess Trainer Agent...{RESET}\n")

    # Run health checks first
    run_health_checks()

    # Stop existing services on our ports
    for port, name in [(BACKEND_PORT, "Backend"), (FRONTEND_PORT, "Frontend")]:
        if backend_only and port == FRONTEND_PORT:
            continue
        if _check_port(port):
            print(f"{YELLOW}Stopping existing {name} on port {port}...{RESET}")
            _kill_port(port)

    processes = []

    # Start backend
    python = _get_python()
    if python != sys.executable:
        print(f"{DIM}Using venv: {python}{RESET}")
    print(f"Starting backend on port {BACKEND_PORT}...")
    backend = subprocess.Popen(
        [
            python, "-m", "uvicorn", "main:app",
            "--host", "0.0.0.0",
            "--port", str(BACKEND_PORT),
            "--reload",
        ],
        cwd=PROJECT_ROOT,
    )
    processes.append(("Backend", backend))

    frontend = None
    if not backend_only:
        fe_dir = os.path.join(PROJECT_ROOT, "frontend")
        if os.path.isdir(os.path.join(fe_dir, "node_modules")):
            print(f"Starting frontend on port {FRONTEND_PORT}...")
            frontend = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=fe_dir,
            )
            processes.append(("Frontend", frontend))
        else:
            print(f"{YELLOW}Skipping frontend — run 'cd frontend && npm install' first{RESET}")

    # Wait for backend to be ready
    print("\nWaiting for backend...", end="", flush=True)
    for _ in range(30):
        if _check_port(BACKEND_PORT):
            print(f" {GREEN}ready{RESET}")
            break
        time.sleep(1)
        print(".", end="", flush=True)
    else:
        print(f" {RED}timeout{RESET}")

    print(f"\n{GREEN}App running:{RESET}")
    print(f"  Backend:  http://localhost:{BACKEND_PORT}")
    print(f"  API docs: http://localhost:{BACKEND_PORT}/docs")
    if frontend:
        print(f"  Frontend: http://localhost:{FRONTEND_PORT}")
    print(f"\n  Press Ctrl+C to stop\n")

    # Handle shutdown
    def shutdown(sig, frame):
        print(f"\n{YELLOW}Shutting down...{RESET}")
        for name, proc in processes:
            proc.terminate()
            try:
                proc.wait(timeout=5)
                print(f"  {name} stopped")
            except subprocess.TimeoutExpired:
                proc.kill()
                print(f"  {name} killed")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Wait for processes
    try:
        while True:
            for name, proc in processes:
                ret = proc.poll()
                if ret is not None:
                    print(f"{RED}{name} exited with code {ret}{RESET}")
                    shutdown(None, None)
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    # Load .env for health checks
    sys.path.insert(0, PROJECT_ROOT)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description="Chess Trainer Agent")
    parser.add_argument("--check", action="store_true", help="Health check only")
    parser.add_argument("--backend", action="store_true", help="Backend only (no frontend)")
    args = parser.parse_args()

    if args.check:
        ok = run_health_checks()
        sys.exit(0 if ok else 1)
    else:
        start_app(backend_only=args.backend)
