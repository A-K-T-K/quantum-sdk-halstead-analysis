"""Small exact state-vector simulator used for functional-equivalence checking.

Design goals
------------
* Exact (no sampling): every measurement outcome with non-zero probability is
  followed as a separate *branch* with its probability.
* Terminal measurements are *deferred*: a measurement only collapses the state
  when something later depends on it (a gate on the measured qubit, or a
  classical condition reading the result).  At the end of the program the
  pre-measurement state is therefore still available and can be compared, up
  to global phase, with an analytic reference state.
* Programs are given as a control-flow graph of blocks so that Q#/QIR branching
  can be executed directly; linear programs from the Python SDKs are a single
  block whose ops may carry classical conditions.

Qubit convention: big-endian, qubit 0 is the most significant tensor axis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

PROB_EPS = 1e-12


@dataclass
class Op:
    kind: str                       # 'gate' | 'measure' | 'reset'
    targets: tuple = ()
    matrix: Optional[np.ndarray] = None   # 2^k x 2^k, big-endian over `targets`
    controls: tuple = ()
    ctrl_vals: tuple = ()
    cond: Optional[tuple] = None    # (result_key, value) -> op applies only if result == value
    result: Optional[str] = None    # result key for measurements (None = discarded)
    label: str = ""


@dataclass
class Block:
    ops: list
    # terminator: None (end), ('jmp', name), ('br', result_key, value_if_true, then_name, else_name)
    term: Optional[tuple] = None


@dataclass
class Program:
    width: int
    blocks: dict = field(default_factory=dict)
    entry: str = "entry"
    measured_keys: dict = field(default_factory=dict)   # result_key -> qubit (filled while simulating)

    @staticmethod
    def linear(width, ops):
        return Program(width=width, blocks={"entry": Block(list(ops))}, entry="entry")


@dataclass
class Branch:
    prob: float
    state: np.ndarray               # tensor of shape (2,)*W, normalised
    results: dict                   # result_key -> 0/1 (collapsed)
    pending: dict                   # qubit -> {'key': str|None, 'reset': bool}
    measured: dict                  # result_key -> qubit, for every measurement seen

    def copy(self):
        return Branch(self.prob, self.state.copy(), dict(self.results),
                      {q: dict(v) for q, v in self.pending.items()}, dict(self.measured))


def apply_matrix(state, mat, targets, controls=(), ctrl_vals=()):
    """Apply `mat` on `targets` (big-endian) conditioned on `controls` having `ctrl_vals`."""
    W = state.ndim
    k = len(targets)
    idx = [slice(None)] * W
    for c, v in zip(controls, ctrl_vals):
        idx[c] = int(v)
    idx = tuple(idx)
    sub = state[idx]
    remaining = [a for a in range(W) if a not in controls]
    tpos = [remaining.index(t) for t in targets]
    m = np.asarray(mat, dtype=complex).reshape((2,) * (2 * k))
    res = np.tensordot(m, sub, axes=(list(range(k, 2 * k)), tpos))
    res = np.moveaxis(res, list(range(k)), tpos)
    state[idx] = res


X_MAT = np.array([[0, 1], [1, 0]], dtype=complex)


def _collapse(branch: Branch, q: int):
    """Collapse the pending measurement on qubit q. Returns the non-zero outcome branches."""
    info = branch.pending[q]
    out = []
    for v in (0, 1):
        st = branch.state.copy()
        idx = [slice(None)] * st.ndim
        idx[q] = 1 - v
        st[tuple(idx)] = 0.0
        p = float(np.vdot(st, st).real)
        if p <= PROB_EPS:
            continue
        st /= np.sqrt(p)
        if info["reset"] and v == 1:
            apply_matrix(st, X_MAT, (q,))
        pending = {k: dict(x) for k, x in branch.pending.items() if k != q}
        results = dict(branch.results)
        if info["key"] is not None:
            results[info["key"]] = v
        out.append(Branch(branch.prob * p, st, results, pending, dict(branch.measured)))
    return out


def _resolve(branches, q):
    out = []
    for b in branches:
        if q in b.pending:
            out.extend(_collapse(b, q))
        else:
            out.append(b)
    return out


def _resolve_key(branches, key):
    out = []
    for b in branches:
        if key in b.results:
            out.append(b)
            continue
        q = next((qq for qq, inf in b.pending.items() if inf["key"] == key), None)
        if q is None:
            raise KeyError(f"classical result '{key}' read before being measured")
        out.extend(_collapse(b, q))
    return out


def _apply_op(branches, op: Op):
    if op.cond is not None:
        branches = _resolve_key(branches, op.cond[0])
    # A reset on an already-measured (pending) qubit is unobservable: no collapse needed.
    lazy_reset = op.kind == "reset"
    touched = tuple(op.targets) + tuple(op.controls)
    for q in touched:
        if lazy_reset:
            continue
        branches = _resolve(branches, q)
    out = []
    for b in branches:
        if op.cond is not None and b.results[op.cond[0]] != op.cond[1]:
            out.append(b)
            continue
        if op.kind == "gate":
            apply_matrix(b.state, op.matrix, op.targets, op.controls, op.ctrl_vals)
        elif op.kind in ("measure", "mreset"):
            (q,) = op.targets
            b.pending[q] = {"key": op.result, "reset": op.kind == "mreset"}
            if op.result is not None:
                b.measured[op.result] = q
        elif op.kind == "reset":
            (q,) = op.targets
            if q in b.pending:
                b.pending[q]["reset"] = True
            else:
                b.pending[q] = {"key": None, "reset": True}
        else:
            raise ValueError(op.kind)
        out.append(b)
    return out


def run(program: Program, init_state: Optional[np.ndarray] = None, max_branches=4096):
    """Execute `program`; return list of final branches."""
    W = program.width
    if init_state is None:
        st = np.zeros((2,) * W, dtype=complex)
        st[(0,) * W] = 1.0
    else:
        st = np.asarray(init_state, dtype=complex).reshape((2,) * W).copy()
    # active items: (block_name, branch)
    work = [(program.entry, Branch(1.0, st, {}, {}, {}))]
    finished = []
    while work:
        name, br = work.pop()
        block = program.blocks[name]
        branches = [br]
        for op in block.ops:
            branches = _apply_op(branches, op)
            if len(branches) > max_branches:
                raise RuntimeError("too many branches")
        term = block.term
        if term is None:
            finished.extend(branches)
        elif term[0] == "jmp":
            work.extend((term[1], b) for b in branches)
        elif term[0] == "br":
            _, key, val, then_name, else_name = term
            for b in _resolve_key(branches, key):
                work.append((then_name if b.results[key] == val else else_name, b))
        else:
            raise ValueError(term)
    return finished


# ----------------------------------------------------------------------------
# helpers for comparing final states
# ----------------------------------------------------------------------------

def restrict(state, keep, ancilla_tol=1e-9):
    """Project state onto ancillas (= qubits not in `keep`) being |0>.

    Returns (vector over `keep` in big-endian order, leaked_probability)."""
    W = state.ndim
    idx = [slice(None)] * W
    for a in range(W):
        if a not in keep:
            idx[a] = 0
    sub = state[tuple(idx)]
    remaining = [a for a in range(W) if a in keep]
    order = [remaining.index(k) for k in keep]
    sub = np.transpose(sub, order).reshape(-1)
    leaked = 1.0 - float(np.vdot(sub, sub).real)
    return sub, leaked


def reduced_density(vec, n, keep):
    """Reduced density matrix on qubits `keep` of an n-qubit pure state vector."""
    t = np.asarray(vec).reshape((2,) * n)
    other = [a for a in range(n) if a not in keep]
    t = np.transpose(t, list(keep) + other).reshape(2 ** len(keep), -1)
    return t @ t.conj().T


def register_fidelity(vec, n, keep, ref):
    """<ref| rho_keep |ref> without forming rho: || M^dagger ref ||^2 with M = vec reshaped (keep, rest)."""
    t = np.asarray(vec).reshape((2,) * n)
    other = [a for a in range(n) if a not in keep]
    M = np.transpose(t, list(keep) + other).reshape(2 ** len(keep), -1)
    return float(np.linalg.norm(M.conj().T @ ref) ** 2)


def fidelity_pure(a, b):
    """|<a|b>|^2 for normalised vectors."""
    return float(abs(np.vdot(a, b)) ** 2)
