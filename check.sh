#!/bin/sh
# Pre-deploy checks. Run from the folder containing app.py.
#
# Each of these exists because something shipped broken without it:
#   ast.parse          — syntax only; catches nothing else
#   pyflakes           — undefined names anywhere, including inside
#                        functions. Would have caught the 500 on Activity
#                        and the UnboundLocalError in the scope check.
#   import_order_check — names used at module level before they are
#                        defined. Would have caught the decorator that
#                        stopped every worker booting.
set -e
echo "1/4  syntax"
python3 -c "import ast,sys; ast.parse(open('app.py').read()); print('     ok')"
echo "2/4  undefined names"
if python3 -m pyflakes app.py 2>/dev/null | grep -i 'undefined name'; then
  echo "     FAILED — fix the names above before deploying"; exit 1
else
  echo "     ok"
fi
echo "3/4  module-level definition order"
python3 import_order_check.py app.py >/dev/null && echo "     ok"
echo "4/4  rendered HTML is well-formed"
# Catches unbalanced or stray tags in ADMIN_HTML — a </details> that should
# have been a </div>, a duplicated closing tag. Browsers paper over these,
# so they survive visual checks.
if [ -f render_test.py ]; then
  python3 - <<'PYEOF' || exit 1
import subprocess, sys
src = open("render_test.py").read()
ns = {}
exec(src.split('print(f"{\'tab\'')[0], ns)
bad = 0
for tab in ("overview","activity","advisors","biometric","knowledge",
            "users","settings","diagnostics"):
    open(f"/tmp/_check_{tab}.html","w").write(ns["tpl"].render(**ns["ctx"](tab)))
    r = subprocess.run([sys.executable,"tagcheck.py",f"/tmp/_check_{tab}.html"],
                       capture_output=True, text=True)
    if r.returncode:
        bad += 1
        print(f"     {tab}: {r.stdout.strip()}")
print("     ok" if not bad else "     FAILED")
sys.exit(1 if bad else 0)
PYEOF
else
  echo "     skipped (no render_test.py)"
fi
echo
echo "All checks passed."
