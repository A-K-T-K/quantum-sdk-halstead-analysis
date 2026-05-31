# Halstead Metric Comparison of Quantum SDKs

The study investigates lexical software complexity across four major quantum software development kits (SDKs): IBM Qiskit, Google Cirq, Xanadu PennyLane, and Microsoft Q#. Complexity is quantified using Halstead software metrics and evaluated through a controlled repeated-measures experimental design.

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
│   └── rq3_import_condition.csv
│
├── batch_halstead.py
├── functional_equivalence.ipynb
├── stats_test.ipynb
├── operator_set.json
├── requirements.txt
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
* `*.ipynb` — Reference notebook used during development and verification

Across both parsing conditions, the repository contains 64 analyzed source-code implementations derived from 8 benchmark circuits, 4 SDKs, and 2 import-treatment conditions.

### Directory Description

| Path                            | Description                                                                            |
| ------------------------------- | -------------------------------------------------------------------------------------- |
| `With_import/`                  | Benchmark implementations including SDK import preambles.                              |
| `Without_import/`               | Benchmark implementations with import statements removed prior to analysis.            |
| `data/halstead_results.csv`     | Complete extracted Halstead metric dataset for all benchmark implementations.          |
| `data/desc_by_circuit.csv`      | Descriptive statistics aggregated by benchmark circuit.                                |
| `data/desc_by_condition.csv`    | Descriptive statistics aggregated by import-condition treatment.                       |
| `data/desc_overall.csv`         | Overall descriptive statistics across the full corpus.                                 |
| `data/posthoc_effect_sizes.csv` | Pairwise post-hoc comparisons and effect-size calculations.                            |
| `data/rq3_import_condition.csv` | Results associated with the import-condition analysis.                                 |
| `batch_halstead.py`             | Deterministic cross-language tokenization and Halstead metric extraction pipeline.     |
| `functional_equivalence.ipynb`  | Verification notebook demonstrating functional equivalence across SDK implementations. |
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
| Microsoft Q# | Modern Q# SDK |

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

This step parses all benchmark implementations and generates `halstead_results.csv` in the repository root directory.

### Verify Functional Equivalence

```bash
jupyter notebook functional_equivalence.ipynb
```

This notebook verifies that equivalent benchmark implementations across SDKs produce the expected quantum behavior.

### Run Statistical Analyses

```bash
jupyter notebook stats_test.ipynb
```

This notebook performs the descriptive, inferential, and post-hoc statistical analyses reported in the manuscript.

---



## License

This repository is provided for research and educational purposes.
