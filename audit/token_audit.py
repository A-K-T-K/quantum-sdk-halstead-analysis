"""Export the actual lexical measurement convention and audit source-derived counts."""
import csv
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import batch_halstead as bh
import pandas as pd


def main():
    # Expected categories are written explicitly, independently of the classifier.
    fixtures = [
        ("qc.h(qr[0])", ["h", "(", "[", "]", ")"], ["qc", "qr", "0"]),
        ("let theta = 0.3;", ["let", "=", ";"], ["theta", "0.3"]),
        ('@qml.qnode(dev)', ["@", "qnode", "(", ")"], ["qml", "dev"]),
        ("{ for i in 0..2 { X(q[i]); } }", ["for", "in", "X", "(", "[", "]", ")", ";"],
         ["i", "0", "2", "q", "i"]),
        ('name = "theta"', ["="], ["name", '"theta"']),
        ("a: Int < b > c", [], ["a", "Int", "b", "c"]),
        ("x <= 2 != y", ["<=", "!="], ["x", "2", "y"]),
        ("-1 + 2.0 / 3", ["-", "+", "/"], ["1", "2.0", "3"]),
    ]
    for source, operators, operands in fixtures:
        assert bh.classify(bh.tokenize(source)) == (operators, operands), source

    rows, omissions, measurements = [], [], []
    for condition in bh.ROOT_DIRS:
        for path in sorted((ROOT / condition).rglob("*")):
            if path.suffix not in (".py", ".qs"):
                continue
            source = path.read_text(encoding="utf-8")
            matches = list(re.finditer(bh.token_pattern, source, re.VERBOSE))
            tokens = [m.group() for m in matches]
            covered = set()
            operators, operands = bh.classify(tokens)
            for i, match in enumerate(matches):
                token = tokens[i]
                # Classifying each suffix preserves the next-token context. The first
                # classified token belongs to the operator or operand stream unless skipped.
                if token in {".", "{", "}"}:
                    kind = "ignored"
                else:
                    ops, args = bh.classify(tokens[i:i + 2])
                    kind = "operator" if ops and ops[0] == token else "operand"
                rows.append(dict(file=path.relative_to(ROOT).as_posix(), index=i,
                                 offset=match.start(), token=token, classification=kind))
                covered.update(range(match.start(), match.end()))
            for offset, char in enumerate(source):
                if offset not in covered and not char.isspace():
                    omissions.append(dict(file=path.relative_to(ROOT).as_posix(), offset=offset, character=char))
            measurements.append([condition, path.parent.name, path.stem, *bh.halstead(source)])
            emitted = [r for r in rows if r["file"] == path.relative_to(ROOT).as_posix()]
            assert [r["token"] for r in emitted if r["classification"] == "operator"] == operators
            assert [r["token"] for r in emitted if r["classification"] == "operand"] == operands
    archived = pd.read_csv(ROOT / "data/halstead_results.csv")
    fresh = pd.DataFrame(measurements, columns=archived.columns)
    keys = ["dataset", "circuit", "sdk"]
    pd.testing.assert_frame_equal(fresh.sort_values(keys).reset_index(drop=True),
                                  archived.sort_values(keys).reset_index(drop=True))
    for name, data, fields in [
        ("token_classification.csv", rows, ["file", "index", "offset", "token", "classification"]),
        ("omitted_characters.csv", omissions, ["file", "offset", "character"]),
    ]:
        with (ROOT / "audit" / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(data)
    print(f"Passed {len(fixtures)} lexical fixtures; all 64 source-derived rows match; "
          f"exported {len(rows)} tokens and {len(omissions)} omitted characters")


if __name__ == "__main__":
    main()
