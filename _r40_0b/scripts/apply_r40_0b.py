#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

BASE_COMMIT = "ab8714d6acc63f10df2d09baed89ab4aa0a5f23d"
ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
BUNDLE = Path(__file__).resolve().parents[1]
PAYLOAD = BUNDLE / "payload"

WORKER = ROOT / "worker_app" / "ezscore_analysis_worker.pyw"
KERNEL = ROOT / "src" / "Kernel.php"
START_WEB = ROOT / "scripts" / "start_ezscore_web.ps1"
LAUNCH_BACKEND = ROOT / "scripts" / "launch_ezscore_backend.ps1"
SERVER_CONTROL = ROOT / "worker_app" / "server_control.py"
GATEWAY = ROOT / "worker_app" / "online_gateway.py"


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, encoding="utf-8", errors="replace", check=False)
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(cmd)}\n{p.stdout}")
    return p


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".r40_0b_tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly 1 anchor, found {count}. STOP.")
    return text.replace(old, new, 1)


def verify_clean_base() -> None:
    head = run(["git", "rev-parse", "HEAD"]).stdout.strip()
    if head != BASE_COMMIT:
        raise RuntimeError(f"Unexpected Git base: {head}. Expected {BASE_COMMIT}. STOP.")
    status = run(["git", "status", "--porcelain=v1", "-uall"]).stdout.splitlines()
    dirty = [line for line in status if "_r40_0b/" not in line.replace("\\", "/")]
    if dirty:
        raise RuntimeError("Working tree is not clean before R40.0B. STOP.\n" + "\n".join(dirty[:30]))


def main() -> None:
    verify_clean_base()
    required = [WORKER, KERNEL, START_WEB, LAUNCH_BACKEND,
                PAYLOAD / "worker_app" / "server_control.py",
                PAYLOAD / "worker_app" / "online_gateway.py",
                PAYLOAD / "worker_app" / "worker_tail_r40.pyfrag",
                PAYLOAD / "scripts" / "start_ezscore_web.ps1",
                PAYLOAD / "scripts" / "launch_ezscore_backend.ps1"]
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"Missing prerequisite: {path}. STOP.")

    worker = read_text(WORKER)
    kernel = read_text(KERNEL)

    checks = [
        ("worker baseline version", 'APP_VERSION = "R39.4"' in worker),
        ("worker baseline configure", 'os.environ.get("EZSCORE_WORKER_URL")' in worker),
        ("worker baseline monitor", 'class LocalServerMonitor:' in worker),
        ("worker baseline window", 'class WorkerWindow:' in worker),
        ("kernel baseline", 'final class Kernel extends BaseKernel' in kernel and 'use MicroKernelTrait;' in kernel),
        ("no prior server control", not SERVER_CONTROL.exists()),
        ("no prior gateway", not GATEWAY.exists()),
    ]
    bad = [name for name, ok in checks if not ok]
    if bad:
        raise RuntimeError("Unexpected clean R39.5 baseline: " + ", ".join(bad) + ". STOP.")

    # Build all modified contents in memory BEFORE touching source files.
    worker_new = replace_once(worker, 'APP_VERSION = "R39.4"', 'APP_VERSION = "R40.0B"', "worker version")
    worker_new = replace_once(
        worker_new,
        'from tkinter import filedialog, messagebox, ttk\n',
        'from tkinter import filedialog, messagebox, ttk\nfrom server_control import ServerController\n',
        "worker server_control import",
    )
    old_base = '''        base_url = (\n            os.environ.get("EZSCORE_WORKER_URL")\n            or env.get("EZSCORE_WORKER_URL")\n            or "http://127.0.0.1:8501"\n        )'''
    new_base = '''        controller = getattr(self.app, "server_control", None)\n        base_url = controller.worker_url() if controller is not None else (\n            os.environ.get("EZSCORE_WORKER_URL")\n            or env.get("EZSCORE_WORKER_URL")\n            or "http://127.0.0.1:8501"\n        )'''
    worker_new = replace_once(worker_new, old_base, new_base, "worker effective API target")
    tail_index = worker_new.find("class LocalServerMonitor:")
    if tail_index < 0:
        raise RuntimeError("Worker tail anchor missing. STOP.")
    worker_tail = read_text(PAYLOAD / "worker_app" / "worker_tail_r40.pyfrag")
    worker_new = worker_new[:tail_index] + worker_tail.rstrip() + "\n"

    old_kernel = '''final class Kernel extends BaseKernel\n{\n    use MicroKernelTrait;\n}\n'''
    new_kernel = '''final class Kernel extends BaseKernel\n{\n    use MicroKernelTrait;\n\n    public function getCacheDir(): string\n    {\n        $instance = (string) (getenv('EZSCORE_INSTANCE') ?: '');\n        if (!in_array($instance, ['online', 'local'], true)) {\n            return parent::getCacheDir();\n        }\n\n        return $this->getProjectDir().'/var/cache/'.$instance.'/'.$this->environment;\n    }\n\n    public function getLogDir(): string\n    {\n        $instance = (string) (getenv('EZSCORE_INSTANCE') ?: '');\n        if (!in_array($instance, ['online', 'local'], true)) {\n            return parent::getLogDir();\n        }\n\n        return $this->getProjectDir().'/var/log/'.$instance;\n    }\n}\n'''
    kernel_new = replace_once(kernel, old_kernel, new_kernel, "Kernel isolated runtime")

    backups: dict[Path, bytes | None] = {}
    targets = [WORKER, KERNEL, START_WEB, LAUNCH_BACKEND, SERVER_CONTROL, GATEWAY]
    for path in targets:
        backups[path] = path.read_bytes() if path.exists() else None

    try:
        write_atomic(WORKER, worker_new)
        write_atomic(KERNEL, kernel_new)
        shutil.copyfile(PAYLOAD / "scripts" / "start_ezscore_web.ps1", START_WEB)
        shutil.copyfile(PAYLOAD / "scripts" / "launch_ezscore_backend.ps1", LAUNCH_BACKEND)
        shutil.copyfile(PAYLOAD / "worker_app" / "server_control.py", SERVER_CONTROL)
        shutil.copyfile(PAYLOAD / "worker_app" / "online_gateway.py", GATEWAY)

        # Compile/lint the actual installed files before declaring success.
        run([sys.executable, "-m", "py_compile", str(SERVER_CONTROL), str(GATEWAY), str(WORKER)])
        php_kernel = run(["php", "-l", str(KERNEL)])
        if "No syntax errors detected" not in php_kernel.stdout:
            raise RuntimeError("PHP syntax check did not confirm Kernel.php.")
        run(["php", "bin\\console", "lint:container"])

        # Contract-critical static assertions.
        installed_worker = read_text(WORKER)
        installed_control = read_text(SERVER_CONTROL)
        installed_gateway = read_text(GATEWAY)
        installed_start = read_text(START_WEB)
        assertions = [
            ('APP_VERSION = "R40.0B"' in installed_worker, "worker version"),
            ('from server_control import ServerController' in installed_worker, "worker controller import"),
            ('controller.worker_url()' in installed_worker, "dynamic worker target"),
            ('class ServerStatusMonitor:' in installed_worker, "new monitor"),
            ('class LocalServerMonitor:' not in installed_worker, "legacy monitor removed"),
            ('ONLINE_GATEWAY_PORT = 8501' in installed_control, "online gateway port"),
            ('ONLINE_BACKEND_PORT = 8511' in installed_control, "online backend port"),
            ('LOCAL_DEV_PORT = 8502' in installed_control, "local dev port"),
            ('ezscore-server-control.json' in installed_control, "persistent state"),
            ('restart_online' in installed_control and 'set_online_environment' in installed_control, "automatic online restart"),
            ('maintenance' in installed_gateway and '503' in installed_gateway, "maintenance gateway"),
            ('[ValidateSet("online", "local")]' in installed_start, "multi-instance powershell"),
            ('EZSCORE_INSTANCE' in installed_start and 'APP_ENV' in installed_start, "isolated env process"),
        ]
        failed = [label for ok, label in assertions if not ok]
        if failed:
            raise RuntimeError("Installed contract mismatch: " + ", ".join(failed))

    except Exception:
        for path, data in backups.items():
            try:
                if data is None:
                    path.unlink(missing_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
            except Exception:
                pass
        raise

    print("R40_0B_DUAL_SERVER_CONTROL_INSTALL_OK")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"R40_0B_INSTALL_STOP: {exc}", file=sys.stderr)
        raise SystemExit(1)
