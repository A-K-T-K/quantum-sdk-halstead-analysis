operation Ansatz(theta : Double) : (Result, Result, Result) {
    use q = Qubit[3];
    Ry(theta, q[0]);
    Ry(theta, q[1]);
    Ry(theta, q[2]);
    CNOT(q[0], q[1]);
    CNOT(q[1], q[2]);
    let r0 = M(q[0]);
    let r1 = M(q[1]);
    let r2 = M(q[2]);
    ResetAll(q);
    return (r0, r1, r2);
}
