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
echo "1/3  syntax"
python3 -c "import ast,sys; ast.parse(open('app.py').read()); print('     ok')"
echo "2/3  undefined names"
if python3 -m pyflakes app.py 2>/dev/null | grep -i 'undefined name'; then
  echo "     FAILED — fix the names above before deploying"; exit 1
else
  echo "     ok"
fi
echo "3/3  module-level definition order"
python3 import_order_check.py app.py >/dev/null && echo "     ok"
echo
echo "All checks passed."
