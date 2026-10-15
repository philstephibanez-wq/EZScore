$ErrorActionPreference = "Stop"

$orch = "H:\EZS_orchestrator"
$python = "H:\Python\pythoncore-3.14-64\python.exe"

if (-not (Test-Path -LiteralPath $orch -PathType Container)) {
    throw "ORCHESTRATOR_ROOT_MISSING: $orch"
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "PYTHON_MISSING: $python"
}

Write-Host "=== EZScore DEV - démarrage manuel canonique ==="
Write-Host "CACHE_CLEAR=YES"
Write-Host "CADDY=YES"
Write-Host "VISIBLE_CHILD_CONSOLE=NO"
Write-Host "PUBLIC=http://127.0.0.1:8502"
Write-Host ""

Push-Location $orch
try {
    @'
from config.loader import load_runtime_config
from contracts.target import Target
from server_manager.manager import ServerManager
from caddy_manager.manager import CaddyManager

config = load_runtime_config()
servers = ServerManager(config)
caddy = CaddyManager(config)

before_server = servers.view(Target.DEV, "dev")
before_caddy = caddy.view(Target.DEV)

print(f"DEV backend before: state={before_server.ownership} pid={before_server.pid}")
print(f"DEV Caddy before:   state={before_caddy.ownership} pid={before_caddy.pid}")

server = servers.start(Target.DEV, "dev")
edge = caddy.start(Target.DEV)

print(f"DEV backend: pid={server.pid} http={server.http_alive} ownership={server.ownership}")
print(f"DEV Caddy:   pid={edge.pid} http={edge.http_alive} ownership={edge.ownership}")

if not server.process_alive or not server.http_alive:
    raise SystemExit("DEV_BACKEND_NOT_HEALTHY")
if not edge.process_alive or not edge.http_alive:
    raise SystemExit("DEV_CADDY_NOT_HEALTHY")

print("DEV_START_OK http://127.0.0.1:8502")
'@ | & $python -
    if ($LASTEXITCODE -ne 0) {
        throw "DEV_START_KO"
    }
}
finally {
    Pop-Location
}
