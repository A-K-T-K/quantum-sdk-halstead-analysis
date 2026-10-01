"""Functional-equivalence test for the 64 analysed source files.

    python functional_equivalence.py                 verify With_import/ and Without_import/
    python functional_equivalence.py --mutation      also run the mutation test of the checker
    python functional_equivalence.py --audit <rev>   additionally verify the files as they were
                                                     at git revision <rev> (e.g. the SSRN version)

What is checked for every With_import/ program
----------------------------------------------
1. The file itself is executed through its own SDK (Qiskit `QuantumCircuit.data`, Cirq
   operations, the PennyLane tape, Q# compiled to QIR and runtime-checked with 64 shots
   for this corpus), so the test runs
   exactly the code that is tokenised -- no re-typed copies.
2. The resulting gate-level program is simulated exactly (every measurement branch is
   followed, no sampling). Terminal measurements are deferred, so the pre-measurement state
   is available.
3. That state is compared, up to global phase, with an analytic reference derived from the
   algorithm's mathematical definition (closed-form amplitudes, the DFT matrix, the QAOA
   Hamiltonian exponentials, ...), never from the gate sequence of the implementation.
   Acceptance: fidelity >= 1 - 1e-8. Deutsch-Jozsa is checked on the input register,
   teleportation per measurement branch on Bob's qubit, and the three-qubit QFT
   on all eight computational-basis inputs with a common global phase.
4. Every branch must measure the specified qubits. Teleportation must have the four
   resolved Alice outcomes, each with probability 1/4. Additional compiler ancillas
   must return to |0>; the Deutsch-Jozsa working ancilla is traced out.
   The finite-shot Q# runtime check must finish without a runtime error.

Without_import/ files are not standalone programs; they are verified to be exactly the
With_import/ file with its import / namespace / entry-point preamble removed
(tools/derive_without_import.py), ignoring outer blank lines and trailing whitespace.

Results: data/functional_equivalence.csv (and data/functional_equivalence_audit_<rev>.csv)
"""
import argparse
import subprocess
import sys
import tempfile
import time
import warnings
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from equivalence import extract, specs  # noqa: E402
from tools.derive_without_import import strip_python, strip_qsharp  # noqa: E402

warnings.filterwarnings("ignore")

# Benchmark directory -> specification (see the manuscript, Section 3.3)
SPECS = {
    "bell":     dict(algo="ghz", n=2),                                   # |Phi+>
    "GHZ":      dict(algo="ghz", n=3),
    "DJ":       dict(algo="dj", n=3),                                    # balanced f(x) = x0 XOR x1
    "P_ansatz": dict(algo="ansatz", n=3, shared_theta=True),             # Ry(theta) layer + CNOT ladder
    "QFT":      dict(algo="qft", n=3),
    "qaoa":     dict(algo="qaoa", n=3),                                  # MaxCut on the 3-path, p = 1
    "teleport": dict(algo="teleport", n=3),                              # |psi> = T H |0>
    "Grover":   dict(algo="grover", n=3, marked="111", iterations=1),   # one Grover iteration
}
# The submitted version teleported |+> and hard-coded theta = 0.785 in Q#; the audit uses
# those values so that only genuine defects are reported.
AUDIT_OVERRIDES = {"teleport": {"input": "plus"}, "P_ansatz": {"theta_value": 0.785}}
ORDER = ["bell", "GHZ", "DJ", "P_ansatz", "QFT", "qaoa", "teleport", "Grover"]


def verify_file(path, bench, sdk, spec_overrides=None):
    opts = {k: v for k, v in SPECS[bench].items() if k not in ("algo", "n")}
    opts.update(spec_overrides or {})
    spec = specs.make_spec(SPECS[bench]["algo"], SPECS[bench]["n"], **opts)
    t0 = time.time()
    try:
        prog, _ = extract.load_program(sdk, path, spec.values, spec.n)
        res = specs.check(spec, prog)
    except Exception as ex:
        msg = " ".join(str(ex).strip().splitlines()[:2])[:200]
        res = {"status": "ERROR", "fidelity": float("nan"), "leaked": float("nan"), "branches": 0,
               "width": 0, "measured": "", "notes": [f"{type(ex).__name__}: {msg}"]}
    res["notes"] = "; ".join(res["notes"])
    res["seconds"] = round(time.time() - t0, 2)
    return res


def verify_tree(base: Path, label: str, overrides=None):
    rows = []
    for bench in ORDER:
        for f in sorted((base / "With_import" / bench).glob("*")):
            if f.suffix not in (".py", ".qs"):
                continue
            sdk = f.name.split("_")[0]
            r = verify_file(f, bench, sdk, (overrides or {}).get(bench))
            rows.append({"benchmark": bench, "sdk": sdk, "file": f"With_import/{bench}/{f.name}", **r})
            print(f"[{r['status']:>9}] {label} {bench:9} {sdk:9} fidelity={r['fidelity']:.12f}  {r['notes'][:90]}",
                  flush=True)
    return pd.DataFrame(rows)


def check_without_import(base: Path):
    rows = []
    for bench in ORDER:
        for f in sorted((base / "With_import" / bench).glob("*")):
            if f.suffix not in (".py", ".qs"):
                continue
            g = base / "Without_import" / bench / f.name
            text = f.read_text(encoding="utf-8")
            expect = strip_qsharp(text) if f.suffix == ".qs" else strip_python(text)
            norm = lambda t: "\n".join(l.rstrip() for l in t.strip().splitlines())  # noqa: E731
            ok = g.exists() and norm(g.read_text(encoding="utf-8")) == norm(expect)
            rows.append({"file": f"Without_import/{bench}/{f.name}", "matches_with_import_minus_preamble": ok})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- mutation test
MUTANTS = [
    ("Grover/qiskit_grover.py", "qc.ccz(qr[0], qr[1], qr[2])\nqc.x(qr[0])", "qc.h(qr[2])\nqc.ccz(qr[0], qr[1], qr[2])\nqc.h(qr[2])\nqc.x(qr[0])",
     "Grover diffuser wrapped in H on the target (the defect of the submitted version)"),
    ("Grover/cirq_grover.py", "circuit.append(cirq.CCZ(q[0], q[1], q[2]))\ncircuit.append([cirq.X", "circuit.append(cirq.CCX(q[0], q[1], q[2]))\ncircuit.append([cirq.X",
     "Grover diffuser uses CCX instead of CCZ"),
    ("qaoa/cirq_qaoa.py", "for i in range(3):\n    circuit.append(cirq.H(q[i]))\n", "", "QAOA without the |+> initial layer"),
    ("qaoa/qsharp_qaoa.qs", "Rzz(2.0 * gamma", "Rzz(gamma", "QAOA cost angle convention error"),
    ("teleport/cirq_teleport.py", "circuit.append(cirq.Z(q[2]).with_classical_controls('m0'))\n", "", "teleportation without Z correction"),
    ("teleport/qsharp_teleport.qs", "{ X(q[2]); }", "{ Y(q[2]); }", "teleportation with the wrong Pauli correction"),
    ("teleport/pennylane_teleport.py", "qml.cond(m1, qml.PauliX)", "qml.cond(m0, qml.PauliX)", "correction conditioned on the wrong measurement"),
    ("QFT/qiskit_qft.py", "qc.cp(np.pi/4, qr[2], qr[0])", "qc.cp(np.pi/8, qr[2], qr[0])", "QFT with a wrong rotation angle"),
    ("QFT/pennylane_qft.py", "import numpy as np\n", "", "missing import (program does not run)"),
    ("P_ansatz/pennylane_ansatz.py", "qml.RY(theta, wires=1)", "qml.RX(theta, wires=1)", "ansatz with a wrong rotation axis"),
    ("DJ/cirq_dj.py", "circuit.append(cirq.measure(q1, key='m1'))", "circuit.append(cirq.measure(q1, key='m1'))\ncircuit.append(cirq.measure(q2, key='m2'))",
     "ancilla measured as well (scope differs from specification)"),
    ("GHZ/qsharp_ghz.qs", "        ResetAll(q);\n", "", "Q# qubits released without reset (runtime error)"),
    ("bell/qiskit_bell.py", "qc.cx(qr[0], qr[1])", "qc.cx(qr[1], qr[0])", "control and target swapped"),
    ("bell/pennylane_bell.py", "return qml.probs(wires=[0, 1])", "return qml.state()", "no measurement"),
    ("teleport/cirq_teleport.py", None,
     "import cirq\nq = cirq.LineQubit.range(3)\ncircuit = cirq.Circuit(\n"
     "    cirq.H(q[2]), cirq.T(q[2]),\n"
     "    cirq.measure(q[0], key='m0'), cirq.measure(q[1], key='m1'),\n"
     "    cirq.measure(q[2], key='m2'))\n",
     "known state prepared directly on Bob without teleportation"),
]


def mutation_test():
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for k, (rel, a, b, desc) in enumerate(MUTANTS):
            src = ROOT / "With_import" / rel
            text = src.read_text(encoding="utf-8")
            if a is not None:
                assert a in text, (rel, a)
            p = Path(tmp) / f"m{k}" / src.name
            p.parent.mkdir()
            p.write_text(b if a is None else text.replace(a, b, 1), encoding="utf-8")
            r = verify_file(p, rel.split("/")[0], src.name.split("_")[0])
            caught = r["status"] not in ("pass", "pass-dist")
            rows.append({"mutated_file": rel, "fault": desc, "status": r["status"], "caught": caught,
                         "notes": r["notes"]})
            print(f"{'caught' if caught else 'MISSED':7} {desc}", flush=True)
    return pd.DataFrame(rows)


def audit(rev):
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        files = subprocess.run(["git", "ls-tree", "-r", "--name-only", rev, "With_import"], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.split()
        for f in files:
            if not f.endswith((".py", ".qs")):
                continue
            blob = subprocess.run(["git", "show", f"{rev}:{f}"], cwd=ROOT, capture_output=True, check=True).stdout
            (base / f).parent.mkdir(parents=True, exist_ok=True)
            (base / f).write_bytes(blob)
        return verify_tree(base, f"[{rev}]", AUDIT_OVERRIDES)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutation", action="store_true")
    ap.add_argument("--audit", metavar="REV")
    a = ap.parse_args()
    (ROOT / "data").mkdir(exist_ok=True)

    df = verify_tree(ROOT, "")
    wi = check_without_import(ROOT)
    df.to_csv(ROOT / "data" / "functional_equivalence.csv", index=False)
    wi.to_csv(ROOT / "data" / "functional_equivalence_without_import.csv", index=False)
    print(f"\nWith_import: {(df.status == 'pass').sum()}/{len(df)} pass; "
          f"Without_import: {wi.matches_with_import_minus_preamble.sum()}/{len(wi)} match")
    mutation_ok = True
    if a.mutation:
        mt = mutation_test()
        mt.to_csv(ROOT / "data" / "functional_equivalence_mutation_test.csv", index=False)
        print(f"Mutation test: {mt.caught.sum()}/{len(mt)} injected faults rejected")
        mutation_ok = len(mt) == len(MUTANTS) and mt.caught.all()
    if a.audit:
        au = audit(a.audit)
        au.to_csv(ROOT / "data" / f"functional_equivalence_audit_{a.audit}.csv", index=False)
        print(f"Audit of {a.audit}: " + ", ".join(f"{k}={v}" for k, v in au.status.value_counts().items()))
    expected = {(bench, sdk) for bench in ORDER for sdk in ("cirq", "pennylane", "qiskit", "qsharp")}
    complete = len(df) == len(expected) and set(zip(df.benchmark, df.sdk)) == expected
    ok = (complete and len(wi) == len(expected) and (df.status == "pass").all()
          and wi.matches_with_import_minus_preamble.all() and mutation_ok)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
