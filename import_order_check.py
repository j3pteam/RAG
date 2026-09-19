#!/usr/bin/env python3
"""Catch NameErrors that only appear at import time.

ast.parse validates syntax and nothing else, which is why a decorator
referencing a function defined 300 lines later passed every check I ran and
then failed the deploy. Decorators, default arguments and any other
expression at module level are evaluated the moment the module is imported,
so a name used there must already exist at that point in the file.

This walks the module top to bottom, tracking what has been defined, and
reports anything referenced too early.
"""
import ast
import builtins
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "app.py"
tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)

defined = set(dir(builtins))
problems = []


def names_in(node):
    """Loaded names, minus the ones the expression binds itself.

    A comprehension target and a lambda argument are local to the
    expression, so they are not "used before definition" however early in
    the file they appear.
    """
    bound = set()
    for sub in ast.walk(node):
        if isinstance(sub, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for gen in sub.generators:
                for t in ast.walk(gen.target):
                    if isinstance(t, ast.Name):
                        bound.add(t.id)
        elif isinstance(sub, ast.Lambda):
            for a in sub.args.args + sub.args.kwonlyargs:
                bound.add(a.arg)
    return {n.id for n in ast.walk(node)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)} - bound


for node in tree.body:
    # Expressions evaluated NOW, before the body of anything runs.
    eager = []
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        eager += list(node.decorator_list)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            eager += [d for d in node.args.defaults if d]
            eager += [d for d in node.args.kw_defaults if d]
    elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        if getattr(node, "value", None) is not None:
            eager.append(node.value)
    elif isinstance(node, ast.Expr):
        eager.append(node.value)
    elif isinstance(node, (ast.If, ast.Try, ast.For, ast.While, ast.With)):
        # Compound statements bind names inside themselves — loop targets,
        # "except ... as e", assignments earlier in the same block — so
        # anything they define counts as available to the rest of the block.
        eager.append(node)
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                defined.add(sub.id)
            elif isinstance(sub, ast.ExceptHandler) and sub.name:
                defined.add(sub.name)
            elif isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined.add(sub.name)

    for expr in eager:
        for name in names_in(expr):
            if name not in defined:
                problems.append((getattr(node, "lineno", 0), name,
                                 type(node).__name__))

    # Then record what this statement defines.
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        defined.add(node.name)
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
        for a in node.names:
            defined.add((a.asname or a.name).split(".")[0])
    else:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                defined.add(sub.id)
            elif isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined.add(sub.name)
            elif isinstance(sub, (ast.Import, ast.ImportFrom)):
                for a in sub.names:
                    defined.add((a.asname or a.name).split(".")[0])

if problems:
    print(f"{len(problems)} name(s) used at module level before being defined:\n")
    for lineno, name, kind in problems:
        print(f"  line {lineno:>6}  {name}  (in a {kind})")
    sys.exit(1)

print(f"{path}: every module-level name is defined before it is used")
