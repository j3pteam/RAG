"""Check that every url_for(...) names a route that exists.

This exists because url_for("admin", ...) shipped and produced a 500 the
moment the button was clicked. Nothing caught it: the syntax is valid, the
name is a string rather than an identifier so pyflakes sees nothing, and the
render test never followed a redirect. It only fails at the moment a user
clicks, which is the worst time to find out.

Eight call sites were wrong, and four of them predated the change being made
— so the same mistake had been sitting in a rarely used admin action for
some time, waiting.

Catches both Python call sites and url_for(...) inside the Jinja templates,
since the templates are strings in the same file and are never imported.
"""
import ast
import re
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "app.py"
src = open(PATH, encoding="utf-8").read()
tree = ast.parse(src)

# Endpoint names: the view function's name, unless the route sets endpoint=.
endpoints = set()
for node in ast.walk(tree):
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        continue
    routed = False
    named = None
    for dec in node.decorator_list:
        if not isinstance(dec, ast.Call):
            continue
        func = dec.func
        attr = getattr(func, "attr", "")
        if attr in ("route", "get", "post", "add_url_rule"):
            routed = True
            for kw in dec.keywords:
                if kw.arg == "endpoint" and isinstance(kw.value, ast.Constant):
                    named = kw.value.value
    if routed:
        endpoints.add(named or node.name)

# Flask provides this one itself.
endpoints.add("static")

# Routes registered from the assessment/ blueprints, as "<blueprint>.<view>".
# Every blueprint there is built from the same views, so each blueprint name
# (a literal Blueprint("...") or a _build("...", ...) call) gets every view.
import os
_bp_path = os.path.join(os.path.dirname(os.path.abspath(PATH)), "assessment", "routes.py")
if os.path.exists(_bp_path):
    _bp_src = open(_bp_path, encoding="utf-8").read()
    _bp_names = set(re.findall(r'(?:Blueprint|_build)\(\s*["\'](\w+)["\']', _bp_src))
    _views = [node.name for node in ast.walk(ast.parse(_bp_src))
              if isinstance(node, ast.FunctionDef) and any(
                  isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "route"
                  for d in node.decorator_list)]
    endpoints.update(f"{b}.{v}" for b in _bp_names for v in _views)

bad = []
for m in re.finditer(r'url_for\(\s*["\']([A-Za-z_][\w.]*)["\']', src):
    name = m.group(1)
    if name not in endpoints:
        bad.append((src[:m.start()].count("\n") + 1, name))

if bad:
    print(f"     {len(bad)} url_for target(s) that do not exist:")
    for line, name in bad:
        close = [e for e in endpoints
                 if e.startswith(name) or name.startswith(e.split("_")[0])]
        hint = f"  (did you mean {close[0]}?)" if close else ""
        print(f"       {PATH}:{line}  url_for(\"{name}\"){hint}")
    sys.exit(1)

print(f"     ok  ({len(endpoints)} routes, every url_for resolves)")
