# Halstead Metric Comparison of Quantum SDKs

The study investigates lexical software complexity across four major quantum software development kits (SDKs): IBM Qiskit, Google Cirq, Xanadu PennyLane, and Microsoft Q#. Complexity is quantified using Halstead software metrics and evaluated through a controlled repeated-measures experimental design.

**Versions.** Tag [`v2.0`](https://github.com/A-K-T-K/quantum-sdk-halstead-analysis/tree/v2.0) is the code and data behind the second (revised) SSRN version of the manuscript; its Data Availability Statement cites this tag. Tag [`v1.0`](https://github.com/A-K-T-K/quantum-sdk-halstead-analysis/tree/v1.0) is the original version accompanying the first SSRN posting (see *Corrections* below).

---

## Methodology Overview

The evaluation consists of:

* **4 quantum SDKs**

  * Qiskit
  * Cirq
  * PennyLane
  * Q#

* **8 benchmark quantum circuits**

  * Bell State
  * GHZ State
  * Deutsch–Jozsa
  * Parametric Ansatz
  * Quantum Fourier Transform (QFT)
  * QAOA (p = 1)
  * Quantum Teleportation
  * Grover's Search

* **2 parsing conditions**

  * Source code including import statements
  * Source code excluding import statements

This design yields **64 analyzed source-code implementations** (4 SDKs × 8 circuits × 2 conditions).

### Benchmark Circuit Suite

1. **Bell State** — Two-qubit entangled state preparation.
2. **GHZ State** — Three-qubit multipartite entanglement circuit.
3. **Deutsch–Jozsa Algorithm** — Oracle-based quantum algorithm with ancilla utilization.
4. **Parametric Ansatz** — Symbolic parameterized quantum circuit representative of variational workflows.
5. **Quantum Fourier Transform (QFT)** — Controlled-phase rotation network implementing the discrete quantum Fourier transform.
6. **QAOA (p = 1)** — Single-layer Quantum Approximate Optimization Algorithm ansatz.
7. **Quantum Teleportation** — State transfer protocol involving measurement and classical feed-forward operations.
8. **Grover's Search** — Amplitude amplification circuit with oracle and diffusion operators.

---

## Repository Structure

```text
├── With_import/
│   ├── bell/
│   ├── DJ/
│   ├── GHZ/
│   ├── Grover/
│   ├── P_ansatz/
│   ├── qaoa/
│   ├── QFT/
│   └── teleport/
│
├── Without_import/
│   ├── bell/
│   ├── DJ/
│   ├── GHZ/
│   ├── Grover/
│   ├── P_ansatz/
│   ├── qaoa/
│   ├── QFT/
│   └── teleport/
│
├── data/
│   ├── desc_by_circuit.csv
│   ├── desc_by_condition.csv
│   ├── desc_overall.csv
│   ├── halstead_results.csv
│   ├── posthoc_effect_sizes.csv
│   ├── rq3_import_condition.csv
│   ├── friedman_results.csv
│   ├── condition_friedman_results.csv
│   ├── condition_posthoc_results.csv
│   ├── functional_equivalence.csv
│   ├── functional_equivalence_without_import.csv
│   ├── functional_equivalence_mutation_test.csv
│   └── functional_equivalence_audit_471afb3.csv
│
├── equivalence/            # simulator, SDK extractors, analytic references
├── figures/                # figures produced by stats_test.ipynb
├── tools/
│   ├── derive_without_import.py
│   ├── revise_analysis.py
│   └── refresh_verification_notebook.py
├── batch_halstead.py
├── corrected_stats.py
├── functional_equivalence.py
├── functional_equivalence.ipynb
├── stats_test.ipynb
├── operator_set.json
├── requirements.txt
├── requirements-lock.txt
└── README.md
```

### Benchmark Source Layout

Each benchmark directory contains functionally equivalent implementations of the same quantum circuit across the evaluated SDKs.

Example:

```text
With_import/
└── bell/
    ├── bell_state.ipynb
    ├── cirq_bell.py
    ├── pennylane_bell.py
    ├── qiskit_bell.py
    └── qsharp_bell.qs
```

The corresponding directory under `Without_import/` contains the same implementations with SDK import statements removed prior to Halstead analysis.

### SDK Implementations

For each benchmark circuit, the repository includes:

* `qiskit_*.py` — IBM Qiskit implementation
* `cirq_*.py` — Google Cirq implementation
* `pennylane_*.py` — Xanadu PennyLane implementation
* `qsharp_*.qs` — Microsoft Q# implementation
* `*.ipynb` — Convenience notebook containing the Qiskit, Cirq, and PennyLane programs of the verified `With_import/` files (with imports, so the cells run in both folders). Notebooks are not tokenised or verified; the `.py`/`.qs` files are the analysed corpus and functional equivalence is established by `functional_equivalence.py`

Across both parsing conditions, the repository contains 64 analyzed source-code implementations derived from 8 benchmark circuits, 4 SDKs, and 2 import-treatment conditions.

### Directory Description

| Path                            | Description                                                                            |
| ------------------------------- | -------------------------------------------------------------------------------------- |
| `With_import/`                  | Benchmark implementations including SDK import preambles.                              |
| `Without_import/`               | `With_import/` files with the import / namespace / entry-point preamble removed (generated by `tools/derive_without_import.py`). |
| `data/halstead_results.csv`     | Complete extracted Halstead metric dataset for all benchmark implementations.          |
| `data/desc_by_circuit.csv`      | Descriptive statistics aggregated by benchmark circuit.                                |
| `data/desc_by_condition.csv`    | Descriptive statistics aggregated by import-condition treatment.                       |
| `data/desc_overall.csv`         | Overall descriptive statistics across the full corpus.                                 |
| `data/posthoc_effect_sizes.csv` | Pairwise post-hoc comparisons and effect-size calculations.                            |
| `data/rq3_import_condition.csv` | Results associated with the import-condition analysis.                                 |
| `data/friedman_results.csv`     | Exact circuit-blocked Friedman tests (pooled over both import conditions).             |
| `data/condition_*_results.csv`  | Condition-specific sensitivity analyses (omnibus and post-hoc).                        |
| `batch_halstead.py`             | Deterministic cross-language tokenization and Halstead metric extraction pipeline.     |
| `corrected_stats.py`            | Exact circuit-blocked Friedman and signed-rank tests used by `stats_test.ipynb`.       |
| `functional_equivalence.py`     | Functional-equivalence test of the analysed files against analytic specifications, with a mutation test of the checker. |
| `functional_equivalence.ipynb`  | Runs `functional_equivalence.py` and displays the verdicts. |
| `equivalence/`                  | Exact simulator, per-SDK circuit extraction (Qiskit, Cirq, PennyLane, Q# via QIR), analytic reference semantics. |
| `stats_test.ipynb`              | Statistical analysis workflow implementing Friedman and Wilcoxon procedures.           |
| `operator_set.json`             | Canonical operator vocabulary used during token classification.                        |
| `requirements.txt`              | Reproducible software environment specification.                                       |
| `README.md`                     | Project overview, methodology summary, and replication instructions.                   |

---

## Reproducibility Environment

The experiments were conducted using the following software environment:

| Component    | Version       |
| ------------ | ------------- |
| Python       | 3.13.5        |
| SciPy        | 1.17.0        |
| Pingouin     | 0.5.5         |
| NumPy        | 2.4.2         |
| Pandas       | 2.3.3         |
| Matplotlib   | 3.10.8        |
| Seaborn      | 0.13.2        |
| Qiskit       | 2.3.0         |
| Cirq         | 1.6.1         |
| PennyLane    | 0.44.0        |
| Microsoft Q# (`qsharp` package) | 1.28.0 |

All Python dependencies are specified in `requirements.txt`.

---

## 🚀 Running the Analysis

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Extract Halstead Metrics

```bash
python batch_halstead.py
```

This step parses all benchmark implementations and generates `data/halstead_results.csv`.

### Verify Functional Equivalence

```bash
python functional_equivalence.py --mutation      # or: jupyter notebook functional_equivalence.ipynb
```

Every `With_import/` file is executed through its own SDK: Qiskit circuit data, Cirq operations, the PennyLane
tape, and Q# compiled to QIR and run on the Q# simulator. The resulting circuit is simulated exactly, following
every relevant measurement branch without sampling (conditional probabilities at most 1e-12 are omitted). The pre-measurement state is compared up to global phase with an
analytic reference derived from the algorithm's definition, not from the implementation's gate sequence;
the three-qubit QFT is checked on all eight basis inputs with a common global phase; a program is accepted when its fidelity is at least 1 − 1e-8. In addition:

* the measured qubits must match the specification in every branch; teleportation requires all four resolved Alice outcomes, each with probability 1/4 within tolerance 1e-8;
* additional compiler ancilla qubits must be returned to |0⟩; the Deutsch–Jozsa working ancilla is traced out;
* Q# programs undergo an additional 64-shot runtime check with fixed quantum and classical seeds (7); this is separate from the exact fidelity simulation and cannot exhaust all possible runtime paths;
* every `Without_import/` file must equal its `With_import/` counterpart minus the preamble, ignoring outer blank lines and trailing whitespace. Python import/from lines are removed; Q# open declarations, the namespace wrapper, and @EntryPoint() are removed, and the body is dedented.

`--mutation` injects 15 known faults, and every one must be rejected. `--audit 471afb3` re-verifies the files of
the first public version (see *Corrections* below). The script exits with a non-zero code for a missing implementation, failed current verification, stripped-file mismatch, or missed mutation. Historical audit verdicts are reported separately and do not determine the current corpus exit status.

### Run Statistical Analyses

```bash
python tools/revise_analysis.py
```

This runs every code cell in `stats_test.ipynb`, saves fresh notebook outputs, and writes tables to `data/` and plots to `figures/`. The notebook can also be opened in a separately installed Jupyter frontend.

Inference uses eight circuit blocks. Both import conditions are retained: SDK labels are permuted jointly across a circuit's two conditions for the exact Friedman test, and signed-rank tests use one joint sign flip per circuit. Exact distributions cover `24^8` SDK-label configurations and `2^8` sign configurations. BH correction is applied within each metric's six SDK contrasts and separately across the three omnibus tests and three import tests. `corrected_stats.py` implements these tests and exports condition-specific sensitivity analyses. Descriptive summaries still contain 16 source observations per SDK.

---

## Corrections

The first public version of this repository (commit `471afb3`, the version accompanying the first SSRN posting)
verified each benchmark against a reference built from the *same gate sequence* as the implementation, and
re-typed the circuits instead of executing the analysed files. That check did not detect the following defects;
all of them are corrected in the current version.

| Benchmark | Defect in the first version | Correction |
| --- | --- | --- |
| Grover (all SDKs) | Diffuser applied `H(q2) CCZ H(q2)` (a Toffoli) instead of `CCZ`; fidelity with the Grover state was 0.14 | Diffuser is `H X CCZ X H` |
| QAOA (Cirq, PennyLane, Qiskit) | No initial `H` layer, so the circuit was not the QAOA state | `H` layer added |
| QAOA (Q#) | File contained the parametric ansatz, not QAOA | Rewritten as QAOA |
| Ansatz (Q#) | Mis-nested braces and a hard-coded angle | Parametric operation |
| QFT (PennyLane) | `np` used without being imported; the program did not run | Import added |
| GHZ (Q#) | Measured qubits released without reset (Q# runtime error) | `ResetAll` added |
| All | Inconsistent scope: some programs measured, others returned states or expectation values | Every program measures the specified qubits |
| Teleportation | Teleported `\|+⟩`, for which a missing X correction is undetectable | Teleports `T H\|0⟩` |

Because the analysed files changed, all Halstead values and statistical results were regenerated.
`data/functional_equivalence_audit_471afb3.csv` lists the verdict for every original file:
9 pass, 1 passes on its output distribution only, 19 fail, and 3 raise errors: two programs do not run, and the PennyLane ansatz returns an expectation value, which the checker rejects.
The statistical notebook follows the stated circuit-blocked analysis plan and reports exact p-values.

## License

This repository is provided for research and educational purposes.

## Validation

```powershell
python audit/test_verification.py
python audit/token_audit.py
```

`test_verification.py` contains regression tests for the verification acceptance
rules and the CLI exit status. `token_audit.py` checks lexical fixtures (call
classification, delimiters, numeric and string literals, dot and brace omission,
Q# range syntax), confirms that every row of `data/halstead_results.csv` is
reproduced from the source files, and exports every emitted token with its
classification (`audit/token_classification.csv`) and every character omitted by
the lexer (`audit/omitted_characters.csv`).

## Notes

The lexer is deliberately restricted; unmatched punctuation is omitted before
operator/operand classification. The supplied corpus contains no comments/docstrings
or display code; the extractor does not implement a general comment-removal
preprocessor for arbitrary future files.

For the complete tested Windows environment on Python 3.13.5, install
`requirements-lock.txt`. Refresh the verification notebook with
`python tools/refresh_verification_notebook.py`.
