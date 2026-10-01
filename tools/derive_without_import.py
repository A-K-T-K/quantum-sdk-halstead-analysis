"""Derive Without_import/ from With_import/ by the rule used in the study.

Python: delete `import ...` / `from ... import ...` lines.
Q#:     delete the namespace wrapper, `open ...;` lines and the `@EntryPoint()`
        attribute, and dedent the body by one level.

Usage:  python tools/derive_without_import.py [--check]
        --check only reports files whose Without_import version differs.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def strip_python(src):
    keep = [ln for ln in src.splitlines() if not ln.lstrip().startswith(("import ", "from "))]
    return "\n".join(keep) + "\n"


def strip_qsharp(src):
    lines = src.splitlines()
    out = []
    in_ns = any(ln.strip().startswith("namespace ") for ln in lines)
    for ln in lines:
        s = ln.strip()
        if s.startswith("namespace ") or s.startswith("open ") or s == "@EntryPoint()":
            continue
        out.append(ln)
    if in_ns:
        while out and not out[-1].strip():
            out.pop()
        assert out[-1].strip() == "}", "namespace must end with a closing brace"
        out.pop()
        out = [ln[4:] if ln.startswith("    ") else ln for ln in out]
    return "\n".join(out) + "\n"


def main():
    check = "--check" in sys.argv
    diffs = 0
    for src in sorted((ROOT / "With_import").rglob("*")):
        if src.suffix not in (".py", ".qs"):
            continue
        dst = ROOT / "Without_import" / src.relative_to(ROOT / "With_import")
        text = src.read_text(encoding="utf-8")
        new = strip_qsharp(text) if src.suffix == ".qs" else strip_python(text)
        old = dst.read_text(encoding="utf-8") if dst.exists() else None
        norm = lambda t: "\n".join(l.rstrip() for l in t.strip().splitlines())  # noqa: E731
        if old is None or norm(old) != norm(new):
            diffs += 1
            print(("DIFFERS  " if check else "written  ") + str(dst.relative_to(ROOT)))
            if not check:
                dst.write_text(new, encoding="utf-8", newline="\n")
    print(f"{diffs} file(s) {'differ' if check else 'updated'}")


if __name__ == "__main__":
    main()
