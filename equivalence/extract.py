"""Load benchmark programs written for each SDK and convert them to the common IR in `sim`.

Each SDK's *own* circuit introspection is used (Qiskit `QuantumCircuit.data`,
Cirq operations, PennyLane tapes, Q# compiled to QIR), so verification runs on
exactly the programs that are measured lexically, not on re-typed copies.

Program contracts (what a source file must define)
--------------------------------------------------
qiskit     a module-level ``QuantumCircuit`` named ``qc``
cirq       a module-level ``cirq.Circuit`` named ``circuit``
pennylane  exactly one module-level QNode (any name)
qsharp     an ``@EntryPoint()`` operation, an operation named ``Main``, or (for
           parameterised programs) an operation named ``Circuit``
"""
from __future__ import annotations

import inspect
import re
import runpy
import warnings

import numpy as np

from .sim import Op, Block, Program

SIMPLE_MAX_QUBITS = 3       # dense matrices are used for gates on at most this many targets

# ----------------------------------------------------------------------------
# parameter binding helpers
# ----------------------------------------------------------------------------

_GREEK = {"θ": "theta", "γ": "gamma", "β": "beta"}


def _norm_param_name(name: str):
    """Map parameter names like 'θ', 'theta[2]', 'theta2', 'γ[0]' to (base, index|None)."""
    for g, latin in _GREEK.items():
        name = name.replace(g, latin)
    m = re.fullmatch(r"([A-Za-z_]+?)_?\[?(\d+)?\]?", name)
    if not m:
        raise ValueError(f"unrecognised parameter name {name!r}")
    base, idx = m.group(1), m.group(2)
    return base, (int(idx) if idx is not None else None)


def _param_value(values: dict, name: str):
    base, idx = _norm_param_name(name)
    v = values[base]
    if np.ndim(v) == 0:
        return float(v)
    return float(v[idx if idx is not None else 0])


# ----------------------------------------------------------------------------
# Qiskit
# ----------------------------------------------------------------------------

def _qiskit_ops(circ, qmap, cmap, ops):
    from qiskit.circuit import ControlledGate
    from qiskit.quantum_info import Operator

    for inst in circ.data:
        op = inst.operation
        qs = [qmap[q] for q in inst.qubits]
        name = op.name
        if name in ("barrier", "delay", "id"):
            continue
        if name == "measure":
            ops.append(Op("measure", (qs[0],), result=cmap[inst.clbits[0]], label="measure"))
        elif name == "reset":
            ops.append(Op("reset", (qs[0],), label="reset"))
        elif name == "if_else":
            target, value = op.condition
            if not hasattr(target, "_register") and not type(target).__name__ == "Clbit":
                raise NotImplementedError("only single-clbit conditions are supported")
            key = cmap[target]
            body = op.blocks[0]
            inner_q = {bq: qs[i] for i, bq in enumerate(body.qubits)}
            inner_c = {bc: cmap[inst.clbits[i]] for i, bc in enumerate(body.clbits)}
            sub = []
            _qiskit_ops(body, inner_q, inner_c, sub)
            for o in sub:
                o.cond = (key, int(value))
            ops.extend(sub)
            if len(op.blocks) > 1 and op.blocks[1] is not None and len(op.blocks[1].data):
                raise NotImplementedError("else-branches are not supported")
        elif isinstance(op, ControlledGate) and op.base_gate.num_qubits <= SIMPLE_MAX_QUBITS:
            nc = op.num_ctrl_qubits
            cs = op.ctrl_state
            cvals = tuple((cs >> i) & 1 for i in range(nc))
            base = Operator(op.base_gate).data          # little-endian over targets
            targets = tuple(reversed(qs[nc:]))
            ops.append(Op("gate", targets, base, tuple(qs[:nc]), cvals, label=name))
        elif op.num_qubits <= SIMPLE_MAX_QUBITS and op.num_clbits == 0:
            try:
                mat = Operator(op).data
            except Exception:
                mat = None
            if mat is not None:
                ops.append(Op("gate", tuple(reversed(qs)), mat, label=name))
            else:
                _qiskit_definition(op, qs, cmap, inst, ops)
        else:
            _qiskit_definition(op, qs, cmap, inst, ops)


def _qiskit_definition(op, qs, cmap, inst, ops):
    defn = op.definition
    if defn is None:
        raise NotImplementedError(f"cannot decompose Qiskit instruction {op.name}")
    inner_q = {bq: qs[i] for i, bq in enumerate(defn.qubits)}
    inner_c = {bc: cmap[inst.clbits[i]] for i, bc in enumerate(defn.clbits)}
    _qiskit_ops(defn, inner_q, inner_c, ops)


def qiskit_program(path, values):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ns = runpy.run_path(str(path))
    qc = ns["qc"]
    if qc.parameters:
        qc = qc.assign_parameters({p: _param_value(values, p.name) for p in qc.parameters})
    qmap = {q: i for i, q in enumerate(qc.qubits)}
    cmap = {c: f"c{i}" for i, c in enumerate(qc.clbits)}
    ops = []
    _qiskit_ops(qc, qmap, cmap, ops)
    return Program.linear(qc.num_qubits, ops), qc.num_qubits


# ----------------------------------------------------------------------------
# Cirq
# ----------------------------------------------------------------------------

def _cirq_op(op, qmap, ops, extra_controls=(), extra_vals=(), cond=None):
    import cirq

    if isinstance(op, cirq.ClassicallyControlledOperation):
        conds = op.classical_controls
        if len(conds) != 1:
            raise NotImplementedError("multiple classical controls")
        (c,) = conds
        keys = c.keys
        if len(keys) != 1:
            raise NotImplementedError("composite classical condition")
        _cirq_op(op.without_classical_controls(), qmap, ops, extra_controls, extra_vals,
                 cond=(f"m:{keys[0]}", 1))
        return
    if cirq.is_measurement(op):
        key = cirq.measurement_key_name(op)
        qubits = op.qubits
        for i, q in enumerate(qubits):
            k = f"m:{key}" if len(qubits) == 1 else f"m:{key}[{i}]"
            ops.append(Op("measure", (qmap[q],), result=k, cond=cond, label="measure"))
        return
    if isinstance(op.gate, cirq.ResetChannel):
        ops.append(Op("reset", (qmap[op.qubits[0]],), cond=cond, label="reset"))
        return
    if isinstance(op, cirq.ControlledOperation):
        ctrl = tuple(qmap[q] for q in op.controls)
        vals = _control_tuple(op)
        _cirq_op(op.sub_operation, qmap, ops, extra_controls + ctrl, extra_vals + vals, cond)
        return
    if len(op.qubits) <= SIMPLE_MAX_QUBITS and cirq.has_unitary(op):
        mat = cirq.unitary(op)
        ops.append(Op("gate", tuple(qmap[q] for q in op.qubits), mat, extra_controls, extra_vals,
                      cond=cond, label=str(op.gate)))
        return
    sub = cirq.decompose_once(op, default=None)
    if sub is None:
        raise NotImplementedError(f"cannot decompose Cirq op {op}")
    for s in sub:
        _cirq_op(s, qmap, ops, extra_controls, extra_vals, cond)


def _control_tuple(op):
    vals = []
    for v in op.control_values:
        v = tuple(v) if not isinstance(v, int) else (v,)
        if len(v) != 1:
            raise NotImplementedError("non-trivial control values")
        vals.append(int(v[0]))
    return tuple(vals)


def cirq_program(path, values):
    import cirq

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ns = runpy.run_path(str(path))
    circuit = ns["circuit"]
    params = cirq.parameter_names(circuit)
    if params:
        circuit = cirq.resolve_parameters(circuit, {p: _param_value(values, p) for p in params})
    qubits = sorted(circuit.all_qubits())
    qmap = {q: i for i, q in enumerate(qubits)}
    ops = []
    for op in circuit.all_operations():
        _cirq_op(op, qmap, ops)
    return Program.linear(len(qubits), ops), len(qubits)


# ----------------------------------------------------------------------------
# PennyLane
# ----------------------------------------------------------------------------

def _pl_op(op, wmap, ops, cond=None):
    import pennylane as qml
    from pennylane.measurements import MidMeasureMP
    from pennylane.ops.op_math import Conditional, Controlled

    if isinstance(op, MidMeasureMP):
        key = f"pl:{op.id}"
        kind = "mreset" if op.reset else "measure"
        ops.append(Op(kind, (wmap[op.wires[0]],), result=key, cond=cond, label="measure"))
        return
    if isinstance(op, Conditional):
        mv = op.meas_val
        if len(mv.measurements) != 1:
            raise NotImplementedError("conditions on several mid-circuit measurements")
        key = f"pl:{mv.measurements[0].id}"
        truth = [bool(mv.processing_fn(v)) for v in (0, 1)]
        if truth == [False, True]:
            c = (key, 1)
        elif truth == [True, False]:
            c = (key, 0)
        else:
            raise NotImplementedError("unsupported condition")
        _pl_op(op.base, wmap, ops, cond=c)
        return
    if isinstance(op, Controlled) and len(op.base.wires) <= SIMPLE_MAX_QUBITS:
        ctrl = tuple(wmap[w] for w in op.control_wires)
        vals = tuple(int(v) for v in op.control_values)
        mat = qml.matrix(op.base, wire_order=op.base.wires)
        ops.append(Op("gate", tuple(wmap[w] for w in op.base.wires), mat, ctrl, vals, cond=cond,
                      label=op.name))
        return
    if len(op.wires) <= SIMPLE_MAX_QUBITS and op.has_matrix:
        mat = qml.matrix(op, wire_order=op.wires)
        ops.append(Op("gate", tuple(wmap[w] for w in op.wires), mat, cond=cond, label=op.name))
        return
    if op.name == "MultiControlledX":
        ctrl = tuple(wmap[w] for w in op.wires[:-1])
        vals = tuple(int(v) for v in op.hyperparameters.get("control_values", [1] * len(ctrl)))
        ops.append(Op("gate", (wmap[op.wires[-1]],), np.array([[0, 1], [1, 0]], complex), ctrl, vals,
                      cond=cond, label=op.name))
        return
    if op.has_decomposition:
        for s in op.decomposition():
            _pl_op(s, wmap, ops, cond)
        return
    raise NotImplementedError(f"cannot convert PennyLane op {op}")


def pennylane_program(path, values):
    import pennylane as qml
    from pennylane.measurements import MidMeasureMP

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ns = runpy.run_path(str(path))
        qnodes = [v for v in ns.values() if isinstance(v, qml.QNode)]
        if len(qnodes) != 1:
            raise ValueError(f"expected exactly one QNode, found {len(qnodes)}")
        qnode = qnodes[0]
        sig = inspect.signature(qnode.func)
        args = []
        for pname in sig.parameters:
            base, _ = _norm_param_name(pname)
            v = values[base]
            args.append(np.array(v) if np.ndim(v) else float(v))
        tape = qml.workflow.construct_tape(qnode)(*args)
    wires = sorted(set(tape.wires.tolist()) | set(qnode.device.wires.tolist()))
    wmap = {w: i for i, w in enumerate(wires)}
    ops = []
    for op in tape.operations:
        _pl_op(op, wmap, ops)
    # terminal measurements of the QNode = return statement
    for k, m in enumerate(tape.measurements):
        if getattr(m, "mv", None) is not None:
            continue  # statistics of mid-circuit measurements; already measured
        mw = m.wires.tolist() if len(m.wires) else wires
        name = type(m).__name__
        if name in ("StateMP", "DensityMatrixMP"):
            continue
        if name in ("ExpectationMP", "VarianceMP"):
            raise ValueError("expectation-value outputs are not computational-basis measurements")
        for w in mw:
            ops.append(Op("measure", (wmap[w],), result=f"ret{k}:{w}", label="measure"))
    return Program.linear(len(wires), ops), len(wires)


# ----------------------------------------------------------------------------
# Q# (via QIR)
# ----------------------------------------------------------------------------

_I = np.eye(2, dtype=complex)
_H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
_X = np.array([[0, 1], [1, 0]], dtype=complex)
_Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
_Z = np.diag([1, -1]).astype(complex)
_S = np.diag([1, 1j])
_T = np.diag([1, np.exp(1j * np.pi / 4)])


def _rx(t):
    return np.array([[np.cos(t / 2), -1j * np.sin(t / 2)], [-1j * np.sin(t / 2), np.cos(t / 2)]])


def _ry(t):
    return np.array([[np.cos(t / 2), -np.sin(t / 2)], [np.sin(t / 2), np.cos(t / 2)]], dtype=complex)


def _rz(t):
    return np.diag([np.exp(-1j * t / 2), np.exp(1j * t / 2)])


def _r2(pauli, t):
    P = {"x": _X, "y": _Y, "z": _Z}[pauli]
    PP = np.kron(P, P)
    return np.cos(t / 2) * np.eye(4) - 1j * np.sin(t / 2) * PP


_SWAP = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=complex)

_QIR_CALL = re.compile(r"call\s+(?:void|i1|i64|double)\s+@__quantum__(qis|rt)__(\w+?)(?:__(body|adj|ctl))?\((.*)\)\s*$")
_QIR_ASSIGN = re.compile(r"(%[\w.]+)\s*=\s*(.*)$")


def _qir_args(argstr):
    out = []
    for a in re.split(r",\s*(?![^()]*\))", argstr):
        a = a.strip()
        if not a:
            continue
        if a.startswith("double"):
            out.append(("d", float(a.split()[1])))
        elif "%Qubit*" in a or "%Result*" in a:
            kind = "q" if "%Qubit*" in a else "r"
            if "null" in a.split("*", 1)[1] and "inttoptr" not in a:
                out.append((kind, 0))
            else:
                m = re.search(r"i64\s+(\d+)", a)
                out.append((kind, int(m.group(1)) if m else 0))
        elif a.startswith("i1"):
            out.append(("v", a.split()[1]))
        else:
            out.append(("x", a))
    return out


def parse_qir(qir: str):
    """Parse the entry function of an adaptive/base-profile QIR module into a Program."""
    body = qir[qir.index("@ENTRYPOINT__main"):]
    body = body[body.index("{") + 1: body.index("\n}")]
    blocks = {}
    order = []
    cur = None
    values = {}          # %var -> ('res', key) | ('not', var)
    width = 0
    m = re.search(r'"required_num_qubits"="(\d+)"', qir)
    if m:
        width = int(m.group(1))
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith(";"):
            continue
        if line.endswith(":") and not line.startswith("call"):
            cur = line[:-1]
            blocks[cur] = Block([])
            order.append(cur)
            continue
        assign = None
        am = _QIR_ASSIGN.match(line)
        if am:
            assign, line = am.group(1), am.group(2).strip()
        if line.startswith("br "):
            mm = re.match(r"br i1 (%[\w.]+|true|false), label %([\w.]+), label %([\w.]+)", line)
            if mm:
                v = mm.group(1)
                key, val = _qir_value(values, v)
                blocks[cur].term = ("br", key, val, mm.group(2), mm.group(3))
            else:
                mm = re.match(r"br label %([\w.]+)", line)
                blocks[cur].term = ("jmp", mm.group(1))
            continue
        if line.startswith("ret"):
            blocks[cur].term = None
            continue
        if line.startswith("icmp"):
            mm = re.match(r"icmp (eq|ne) i1 (%[\w.]+), (true|false)", line)
            if not mm:
                raise NotImplementedError(line)
            negate = (mm.group(1) == "eq") == (mm.group(3) == "false")
            values[assign] = ("not", mm.group(2)) if negate else ("same", mm.group(2))
            continue
        if line.startswith("xor"):
            mm = re.match(r"xor i1 (%[\w.]+), true", line)
            values[assign] = ("not", mm.group(1))
            continue
        cm = _QIR_CALL.match(line)
        if not cm:
            if line.startswith("phi") or line.startswith("select") or line.startswith("add") or \
                    line.startswith("sub") or line.startswith("zext"):
                continue
            raise NotImplementedError(f"unsupported QIR line: {line}")
        ns_, name, variant, argstr = cm.groups()
        args = _qir_args(argstr)
        if ns_ == "rt":
            if name == "read_result":
                values[assign] = ("res", f"r{args[0][1]}")
            continue
        variant = variant or "body"
        _qir_gate(blocks[cur].ops, name, variant, args)
        for k, v in args:
            if k == "q":
                width = max(width, v + 1)
    # connect fall-through (QIR blocks always end in br/ret, but be safe)
    return Program(width=width, blocks=blocks, entry=order[0])


def _qir_value(values, v):
    if v == "true":
        raise NotImplementedError("constant branch")
    seen = values[v]
    neg = False
    while seen[0] in ("not", "same"):
        if seen[0] == "not":
            neg = not neg
        seen = values[seen[1]]
    _, key = seen
    return key, (0 if neg else 1)


def _qir_gate(ops, name, variant, args):
    qs = [v for k, v in args if k == "q"]
    ds = [v for k, v in args if k == "d"]
    rs = [v for k, v in args if k == "r"]
    adj = variant == "adj"
    single = {"h": _H, "x": _X, "y": _Y, "z": _Z, "s": _S, "t": _T}
    if name in ("s", "t") and adj:
        ops.append(Op("gate", (qs[0],), single[name].conj().T, label=name + "_adj"))
    elif name in single:
        ops.append(Op("gate", (qs[0],), single[name], label=name))
    elif name in ("rx", "ry", "rz"):
        f = {"rx": _rx, "ry": _ry, "rz": _rz}[name]
        ops.append(Op("gate", (qs[0],), f(ds[0]), label=name))
    elif name in ("rxx", "ryy", "rzz"):
        ops.append(Op("gate", (qs[0], qs[1]), _r2(name[1], ds[0]), label=name))
    elif name in ("cx", "cnot"):
        ops.append(Op("gate", (qs[1],), _X, (qs[0],), (1,), label="cx"))
    elif name == "cy":
        ops.append(Op("gate", (qs[1],), _Y, (qs[0],), (1,), label="cy"))
    elif name == "cz":
        ops.append(Op("gate", (qs[1],), _Z, (qs[0],), (1,), label="cz"))
    elif name == "ccx":
        ops.append(Op("gate", (qs[2],), _X, (qs[0], qs[1]), (1, 1), label="ccx"))
    elif name == "swap":
        ops.append(Op("gate", (qs[0], qs[1]), _SWAP, label="swap"))
    elif name in ("m", "mz"):
        ops.append(Op("measure", (qs[0],), result=f"r{rs[0]}", label="m"))
    elif name == "mresetz":
        ops.append(Op("mreset", (qs[0],), result=f"r{rs[0]}", label="mresetz"))
    elif name == "reset":
        ops.append(Op("reset", (qs[0],), label="reset"))
    elif name in ("barrier",):
        pass
    else:
        raise NotImplementedError(f"QIR gate {name}__{variant}")


_ENTRY_ATTR = re.compile(r"@EntryPoint\(\)\s*operation\s+(\w+)\s*\(([^)]*)\)")


def qsharp_entry(source: str, values: dict):
    """Return the entry expression for a Q# source file."""
    ns = re.search(r"namespace\s+([\w.]+)", source)
    prefix = ns.group(1) + "." if ns else ""
    m = _ENTRY_ATTR.search(source)
    if m:
        name, params = m.group(1), m.group(2)
    else:
        m = (re.search(r"operation\s+(Main|Circuit)\s*\(([^)]*)\)", source)
             or re.search(r"operation\s+(\w+)\s*\(([^)]*)\)", source))
        if not m:
            raise ValueError("no entry operation found")
        name, params = m.group(1), m.group(2)
    args = []
    for p in [x for x in params.split(",") if x.strip()]:
        pname, ptype = [s.strip() for s in p.split(":")]
        base, _ = _norm_param_name(pname)
        v = values[base]
        if ptype.endswith("[]"):
            args.append("[" + ", ".join(repr(float(x)) for x in np.atleast_1d(v)) + "]")
        else:
            args.append(repr(float(np.atleast_1d(v)[0])))
    return f"{prefix}{name}({', '.join(args)})", bool(params.strip())


def qsharp_program(path, values, n_program_qubits):
    import qsharp
    from qsharp import TargetProfile

    src = open(path, encoding="utf-8").read()
    entry, has_params = qsharp_entry(src, values)
    qsharp.init(target_profile=TargetProfile.Adaptive_RIF)
    qsharp.eval(src)
    qir = str(qsharp.compile(entry))
    prog = parse_qir(qir)
    # QIR generation does not execute the program; run it so that runtime errors
    # (e.g. "qubit released while not in |0>", which only fires when the released
    # qubit happens to be |1>) are reported. Fixed seeds make this deterministic;
    # very wide programs get fewer shots to bound simulation time.
    qsharp.set_quantum_seed(7)
    qsharp.set_classical_seed(7)
    qsharp.run(entry, shots=64 if prog.width <= 12 else 2)
    return prog, n_program_qubits


LOADERS = {"qiskit": qiskit_program, "cirq": cirq_program, "pennylane": pennylane_program}


def load_program(sdk, path, values, n_program_qubits):
    """Return (Program, number_of_program_qubits). Ancilla qubits (if any) follow program qubits."""
    if sdk == "qsharp":
        return qsharp_program(path, values, n_program_qubits)
    return LOADERS[sdk](path, values)
