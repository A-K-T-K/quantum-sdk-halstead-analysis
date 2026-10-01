"""Analytic reference semantics for every benchmark, independent of any gate decomposition.

Each reference is computed from the *mathematical definition* of the algorithm
(closed-form amplitudes, the DFT matrix, matrix exponentials of the QAOA
Hamiltonians, ...), never by replaying the gate sequence used to write the SDK
programs.  This answers the reviewer concern that "the reference states are
constructed from the same canonical decomposition used to write the SDK programs".

Big-endian convention throughout: qubit 0 is the most significant bit.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import reduce

import numpy as np

from . import sim

TOL = 1e-8
MAX_WIDTH = 22          # largest simulated register (program + ancilla qubits)

# fixed, non-special parameter values used to bind symbolic parameters
GAMMA, BETA = 0.37, 0.81


def theta_values(n):
    return np.array([0.3 + 0.17 * i for i in range(n)])


def alternating(k):
    """'1010...' of length k (bit i is 1 for even i)."""
    return "".join("1" if i % 2 == 0 else "0" for i in range(k))


def grover_iterations(n):
    return int(math.floor(math.pi / 4 * math.sqrt(2 ** n)))


def _bits(i, k):
    return [(i >> (k - 1 - j)) & 1 for j in range(k)]


# ----------------------------------------------------------------------------
# reference constructions
# ----------------------------------------------------------------------------

def ref_ghz(n):
    v = np.zeros(2 ** n, complex)
    v[0] = v[-1] = 1 / np.sqrt(2)
    return v


def ref_bv(secret):
    k = len(secret)
    v = np.zeros(2 ** k, complex)
    v[int(secret, 2)] = 1
    return v


def dj_function(k):
    """Balanced f(x) = x_0 XOR (x_1 AND ... AND x_{k-1})."""
    def f(bits):
        rest = all(bits[1:]) if k > 1 else True
        return bits[0] ^ int(rest) if k > 1 else bits[0]
    return f


def _bit_table(k):
    """(2^k, k) array of big-endian bits."""
    x = np.arange(2 ** k)
    return (x[:, None] >> (k - 1 - np.arange(k))[None, :]) & 1


def _apply_each_axis(vec, mat, k):
    t = np.asarray(vec, complex).reshape((2,) * k)
    for ax in range(k):
        t = np.moveaxis(np.tensordot(mat, t, axes=([1], [ax])), 0, ax)
    return t.reshape(-1)


def ref_dj(k):
    """amp(y) = 2^-k sum_x (-1)^(f(x) + x.y), evaluated as a Walsh-Hadamard transform of (-1)^f."""
    bits = _bit_table(k)
    rest = bits[:, 1:].all(axis=1) if k > 1 else np.ones(2 ** k, bool)
    f = bits[:, 0] ^ rest.astype(int) if k > 1 else bits[:, 0]
    sign = (-1.0) ** f
    wht = _apply_each_axis(sign, np.array([[1, 1], [1, -1]], float), k)
    return wht / 2 ** k


def ref_grover(n, marked, iterations):
    N = 2 ** n
    th = math.asin(1 / math.sqrt(N))
    a_m = math.sin((2 * iterations + 1) * th)
    a_o = math.cos((2 * iterations + 1) * th) / math.sqrt(N - 1)
    v = np.full(N, a_o, complex)
    v[int(marked, 2)] = a_m
    return v


def dft_matrix(n):
    N = 2 ** n
    j = np.arange(N)
    return np.exp(2j * np.pi * np.outer(j, j) / N) / np.sqrt(N)


def ref_qaoa(n, gamma, beta):
    """exp(-i beta sum X) exp(-i gamma sum_{i} Z_i Z_{i+1}) |+>^n  (path graph)."""
    z = 1 - 2 * _bit_table(n)
    cost = (z[:, :-1] * z[:, 1:]).sum(axis=1) if n > 1 else np.zeros(2 ** n)
    psi = np.exp(-1j * gamma * cost) / np.sqrt(2 ** n)
    mix1 = np.array([[np.cos(beta), -1j * np.sin(beta)], [-1j * np.sin(beta), np.cos(beta)]])
    return _apply_each_axis(psi, mix1, n)


def ref_ansatz(thetas):
    """CNOT-ladder( (x) Ry(theta_i)|0> ) evaluated as a basis permutation (prefix parity)."""
    n = len(thetas)
    single = [np.array([np.cos(t / 2), np.sin(t / 2)]) for t in thetas]
    prod = reduce(np.kron, single).astype(complex)
    out = np.zeros_like(prod)
    for x in range(2 ** n):
        b = _bits(x, n)
        y = []
        acc = 0
        for bit in b:
            acc ^= bit
            y.append(acc)
        out[int("".join(map(str, y)), 2)] += prod[x]
    return out


def teleport_input(kind="ht"):
    if kind == "plus":
        return np.array([1, 1], complex) / np.sqrt(2)
    return np.array([1, np.exp(1j * np.pi / 4)], complex) / np.sqrt(2)   # T H |0>


# ----------------------------------------------------------------------------
# spec objects
# ----------------------------------------------------------------------------

@dataclass
class Spec:
    algo: str
    n: int                      # number of program qubits
    measured: tuple             # program qubits that must be measured
    kind: str                   # 'state' | 'register' | 'operator' | 'teleport'
    values: dict = field(default_factory=dict)     # bindings for symbolic parameters
    ref: object = None          # vector / matrix
    register: tuple = ()        # for kind == 'register'
    meta: dict = field(default_factory=dict)


def make_spec(algo, n, **opt):
    allq = tuple(range(n))
    if algo == "ghz":
        return Spec(algo, n, allq, "state", ref=ref_ghz(n))
    if algo == "bv":
        secret = opt.get("secret", alternating(n - 1))
        return Spec(algo, n, tuple(range(n - 1)), "register", ref=ref_bv(secret),
                    register=tuple(range(n - 1)), meta={"secret": secret})
    if algo == "dj":
        return Spec(algo, n, tuple(range(n - 1)), "register", ref=ref_dj(n - 1),
                    register=tuple(range(n - 1)))
    if algo == "grover":
        marked = opt.get("marked", alternating(n))
        it = opt.get("iterations", grover_iterations(n))
        return Spec(algo, n, allq, "state", ref=ref_grover(n, marked, it),
                    meta={"marked": marked, "iterations": it})
    if algo == "qft":
        return Spec(algo, n, allq, "operator", ref=dft_matrix(n) if n <= 10 else None)
    if algo == "qaoa":
        return Spec(algo, n, allq, "state", values={"gamma": GAMMA, "beta": BETA},
                    ref=ref_qaoa(n, GAMMA, BETA))
    if algo == "ansatz":
        if opt.get("shared_theta"):
            th = np.full(n, opt.get("theta_value", theta_values(1)[0]))
            values = {"theta": float(th[0])}
        else:
            th = theta_values(n)
            values = {"theta": th}
        return Spec(algo, n, allq, "state", values=values, ref=ref_ansatz(th))
    if algo == "teleport":
        return Spec(algo, 3, (0, 1, 2), "teleport", ref=teleport_input(opt.get("input", "ht")))
    raise ValueError(algo)


# ----------------------------------------------------------------------------
# checker
# ----------------------------------------------------------------------------

def _apply_dft(vec, n):
    # big-endian DFT with omega = exp(+2 pi i / N): F v = sqrt(N) * ifft(v)
    return np.fft.ifft(vec) * np.sqrt(2 ** n)


def check(spec: Spec, program: sim.Program, seed=0):
    """Return dict(status, fidelity, leaked, measured, notes, branches, width)."""
    W = program.width
    out = {"width": W, "notes": []}
    if W > MAX_WIDTH:
        out.update(status="skipped", fidelity=np.nan, leaked=np.nan, branches=0, measured="")
        out["notes"].append(f"register width {W} > {MAX_WIDTH}: not simulated")
        return out
    n = spec.n
    keep = list(range(n))

    branches = sim.run(program)
    out["branches"] = len(branches)
    measured_q = sorted({q for b in branches for q in b.measured.values()})
    out["measured"] = " ".join(map(str, measured_q))
    expected_measured = set(spec.measured)
    meas_ok = bool(branches) and all(set(b.measured.values()) == expected_measured for b in branches)
    if not meas_ok:
        out["notes"].append(f"measurement scope differs from {list(spec.measured)} in at least one branch "
                            f"(union: {measured_q})")

    protocol_ok = True

    fid, leaked = np.nan, 0.0
    if spec.kind in ("state", "register", "operator"):
        if len(branches) != 1 and spec.kind != "operator":
            # e.g. "M; if r == One { X }" reset idioms: only the output distribution is comparable
            tvd = _distribution_tvd(spec, branches, keep)
            out["notes"].append(f"classical feed-forward after measurement ({len(branches)} branches): "
                                f"compared output distributions only (TVD={tvd:.1e})")
            fid = 1.0 - tvd
            out["dist_only"] = True
        elif len(branches) != 1:
            out["notes"].append(f"unexpected mid-circuit collapse ({len(branches)} branches)")
            fid = 0.0
        else:
            vec, leaked = sim.restrict(branches[0].state, keep)
            if spec.kind == "state":
                fid = sim.fidelity_pure(vec, spec.ref)
            elif spec.kind == "register":
                fid = sim.register_fidelity(vec, n, list(spec.register), spec.ref)
            else:  # Complete computational basis for the small benchmark operator.
                rng = np.random.default_rng(seed)
                fids, phases = [], []
                if n <= 10:
                    inputs = np.eye(2 ** n, dtype=complex).T
                else:
                    inputs = rng.normal(size=(3, 2 ** n)) + 1j * rng.normal(size=(3, 2 ** n))
                    inputs /= np.linalg.norm(inputs, axis=1, keepdims=True)
                for psi in inputs:
                    init = np.zeros((2,) * W, complex)
                    idx = tuple([slice(None)] * n + [0] * (W - n))
                    init[idx] = psi.reshape((2,) * n)
                    br = sim.run(program, init)
                    if len(br) != 1:
                        fids.append(0.0)
                        continue
                    v, lk = sim.restrict(br[0].state, keep)
                    leaked = max(leaked, lk)
                    target = _apply_dft(psi, n)
                    ov = np.vdot(target, v)
                    fids.append(float(abs(ov) ** 2))
                    phases.append(np.angle(ov))
                fid = min(fids)
                if phases and np.ptp(np.unwrap(phases)) > 1e-6:
                    out["notes"].append("input-dependent phase: not equal to DFT up to a global phase")
                    fid = 0.0
    elif spec.kind == "teleport":
        fids = []
        probs = []
        for b in branches:
            vec, lk = sim.restrict(b.state, keep)
            leaked = max(leaked, lk)
            fids.append(sim.register_fidelity(vec, n, [2], spec.ref))
            probs.append(b.prob)
        fid = min(fids) if fids else 0.0
        if len(branches) != 4:
            out["notes"].append(f"expected 4 measurement branches, got {len(branches)}")
            protocol_ok = False
        outcomes = set()
        for b in branches:
            alice = {q: b.results[key] for key, q in b.measured.items()
                     if q in (0, 1) and key in b.results}
            if set(alice) != {0, 1}:
                protocol_ok = False
            else:
                outcomes.add((alice[0], alice[1]))
        if outcomes != {(0, 0), (0, 1), (1, 0), (1, 1)}:
            out["notes"].append("Alice's four resolved measurement outcomes are required")
            protocol_ok = False
        if len(probs) != 4 or not np.allclose(probs, 0.25, rtol=0, atol=TOL):
            out["notes"].append("teleportation branches must each have probability 1/4")
            protocol_ok = False

    out["fidelity"] = fid
    out["leaked"] = leaked
    ok = meas_ok and protocol_ok and fid >= 1 - TOL and leaked <= TOL
    if leaked > TOL:
        out["notes"].append(f"ancilla/leak probability {leaked:.2e}")
    if not (fid >= 1 - TOL):
        out["notes"].append(f"fidelity {fid:.6f} < 1")
    out["status"] = ("pass-dist" if out.get("dist_only") else "pass") if ok else "FAIL"
    return out


def _distribution_tvd(spec, branches, keep):
    """Total-variation distance between reference and program output distributions on spec.measured."""
    mq = list(spec.measured)
    k = len(mq)
    if spec.kind == "register":
        ref_p = np.abs(spec.ref) ** 2
        reg = list(spec.register)
        ref_full = np.zeros(2 ** k)
        for i, p in enumerate(ref_p):
            bits = _bits(i, len(reg))
            idx = sum(bits[reg.index(q)] << (k - 1 - j) for j, q in enumerate(mq))
            ref_full[idx] += p
        ref_p = ref_full
    else:
        full = np.abs(spec.ref) ** 2
        ref_p = np.zeros(2 ** k)
        for i, p in enumerate(full):
            bits = _bits(i, spec.n)
            ref_p[int("".join(str(bits[q]) for q in mq), 2)] += p
    got = np.zeros(2 ** k)
    for b in branches:
        known = {q: b.results[key] for key, q in b.measured.items() if key in b.results}
        probs = np.abs(b.state.reshape(-1)) ** 2
        W = b.state.ndim
        for i, p in enumerate(probs):
            if p < 1e-15:
                continue
            bits = _bits(i, W)
            vals = [known.get(q, bits[q]) for q in mq]
            got[int("".join(map(str, vals)), 2)] += b.prob * p
    return 0.5 * float(np.abs(got - ref_p).sum())
