from pathlib import Path

root = Path(__file__).resolve().parents[1]
cfg = (root / "config" / "packages" / "web_profiler.yaml").read_text(
    encoding="utf-8"
)

needle = "collect_parameter: '_ezs_profile'"
if needle not in cfg:
    raise SystemExit("missing profiler collect_parameter contract")

print("EZSCORE_DEV_PROFILER_POLLING_R1_CONTRACT_OK")
