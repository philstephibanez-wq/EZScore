from pathlib import Path
ROOT = Path(r"H:\EZScore_dev")
index = (ROOT/"public/index.php").read_text(encoding="utf-8")
twig = (ROOT/"templates/base.html.twig").read_text(encoding="utf-8")
css = (ROOT/"public/assets/css/layout.css").read_text(encoding="utf-8")

assert "$_SERVER['EZSCORE_INSTANCE'] = $ezscoreInstance;" in index
assert "$_ENV['EZSCORE_INSTANCE'] = $ezscoreInstance;" in index
assert "app.request.server.get('EZSCORE_INSTANCE') == 'dev'" in twig
assert "EZScore DEV badge R1a" in css
assert "font-size:22px!important" in css
print("EZSCORE_DEV_BADGE_R1A_OK")
