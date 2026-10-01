"""Regression tests for verification acceptance and CLI failure propagation."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import functional_equivalence as fe
from equivalence import sim, specs


class VerificationTests(unittest.TestCase):
    def test_direct_bob_preparation_is_rejected(self):
        h = np.array([[1, 1], [1, -1]], complex) / np.sqrt(2)
        t = np.diag([1, np.exp(1j * np.pi / 4)])
        ops = [sim.Op("gate", (2,), h), sim.Op("gate", (2,), t)]
        ops += [sim.Op("measure", (q,), result=f"m{q}") for q in range(3)]
        result = specs.check(specs.make_spec("teleport", 3), sim.Program.linear(3, ops))
        self.assertAlmostEqual(result["fidelity"], 1)
        self.assertEqual(result["branches"], 1)
        self.assertEqual(result["status"], "FAIL")

    def test_measurement_union_cannot_hide_missing_scope_in_a_branch(self):
        state = specs.ref_ghz(2).reshape(2, 2)
        branches = [sim.Branch(0.5, state, {}, {}, {"m0": 0}),
                    sim.Branch(0.5, state, {}, {}, {"m1": 1})]
        with patch.object(sim, "run", return_value=branches):
            result = specs.check(specs.make_spec("ghz", 2), sim.Program.linear(2, []))
        self.assertEqual(result["measured"], "0 1")
        self.assertEqual(result["status"], "FAIL")

    def test_four_duplicate_alice_outcomes_are_rejected(self):
        state = np.kron([1, 0, 0, 0], specs.teleport_input()).reshape(2, 2, 2)
        branches = [sim.Branch(0.25, state, {"m0": 0, "m1": 0}, {},
                              {"m0": 0, "m1": 1, "m2": 2}) for _ in range(4)]
        with patch.object(sim, "run", return_value=branches):
            result = specs.check(specs.make_spec("teleport", 3), sim.Program.linear(3, []))
        self.assertAlmostEqual(result["fidelity"], 1)
        self.assertEqual(result["status"], "FAIL")

    def test_qft_rejects_input_dependent_column_phases(self):
        matrix = specs.dft_matrix(3) @ np.diag(np.exp(1j * np.arange(8) * 0.1))
        ops = [sim.Op("gate", (0, 1, 2), matrix)]
        ops += [sim.Op("measure", (q,), result=f"m{q}") for q in range(3)]
        result = specs.check(specs.make_spec("qft", 3), sim.Program.linear(3, ops))
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("input-dependent phase" in note for note in result["notes"]))

    def run_cli(self, caught=True, complete=True):
        records = [{"benchmark": bench, "sdk": sdk, "status": "pass"}
                   for bench in fe.ORDER for sdk in ["cirq", "pennylane", "qiskit", "qsharp"]]
        if not complete:
            records.pop()
        current = pd.DataFrame(records)
        stripped = pd.DataFrame({"matches_with_import_minus_preamble": [True] * len(records)})
        mutants = pd.DataFrame({"caught": [caught] * len(fe.MUTANTS)})
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()), \
                patch.object(fe, "ROOT", Path(tmp)), \
                patch.object(fe, "verify_tree", return_value=current), \
                patch.object(fe, "check_without_import", return_value=stripped), \
                patch.object(fe, "mutation_test", return_value=mutants), \
                patch.object(sys, "argv", ["functional_equivalence.py", "--mutation"]):
            with self.assertRaises(SystemExit) as result:
                fe.main()
            return result.exception.code

    def test_missed_mutation_fails_cli(self):
        self.assertEqual(self.run_cli(caught=False), 1)

    def test_missing_implementation_fails_cli(self):
        self.assertEqual(self.run_cli(complete=False), 1)

    def test_complete_success_exits_zero(self):
        self.assertEqual(self.run_cli(), 0)


if __name__ == "__main__":
    unittest.main()
