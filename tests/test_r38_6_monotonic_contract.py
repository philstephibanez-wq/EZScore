from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts'/'install_r38_6.py'
s=p.read_text(encoding='utf-8')
assert 'There is no global matching pass after this point.' in s
assert 'lookahead: int = 18' in s
assert 'cursor = heard_start + seed_len' in s
print('R38_6_MONOTONIC_CONTRACT_OK')
