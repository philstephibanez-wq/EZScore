from __future__ import annotations

import importlib.metadata as metadata

version = metadata.version("madmom-infer")
print("madmom-infer version:", version)

from madmom_infer.features.downbeats import (
    DBNDownBeatTrackingProcessor,
    RNNDownBeatProcessor,
)

print("RNNDownBeatProcessor:", RNNDownBeatProcessor)
print("DBNDownBeatTrackingProcessor:", DBNDownBeatTrackingProcessor)
print("MADMOM 0.2.0 DOWNBEAT API OK")
