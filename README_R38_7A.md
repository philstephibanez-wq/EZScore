# EZScore_v1 R38.7A — structural hotfix

R38.7 failed because its installer expected one exact analyzer block. R38.7A patches `align_provided_text()` structurally by function boundaries, so it accepts the R38.4/R38.5/R38.6 variants.

Scope: acoustic first-vocal onset from time-aligned `lead_vocals`, immutable first-word anchor, monotonic forward alignment, shared ChordsLab/LyricsLab song card, Tempo from canonical beat events, stable per-song diagram persistence.
