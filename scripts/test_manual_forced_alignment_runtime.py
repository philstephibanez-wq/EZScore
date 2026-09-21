from __future__ import annotations

import sys

import torch
import torchaudio

try:
    import uroman
except Exception as exc:
    raise SystemExit(
        "UROMAN MISSING - run: "
        ".\\.venv-py313\\Scripts\\python.exe -m pip install "
        "-r requirements-forced-alignment.txt"
    ) from exc

assert hasattr(torchaudio.pipelines, "MMS_FA")
bundle = torchaudio.pipelines.MMS_FA
assert callable(bundle.get_model)
assert callable(bundle.get_tokenizer)
assert callable(bundle.get_aligner)

print("FORCED ALIGNMENT RUNTIME OK")
print("python:", sys.version.split()[0])
print("torch:", torch.__version__)
print("torchaudio:", torchaudio.__version__)
print("MMS_FA sample rate:", bundle.sample_rate)
print("CUDA:", torch.cuda.is_available())
print("uroman:", getattr(uroman, "__version__", "installed"))
print("NOTE: model weights are downloaded only on first real alignment.")
