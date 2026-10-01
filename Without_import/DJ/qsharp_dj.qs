operation DeutschJozsa() : (Result, Result) {
    use q = Qubit[3];
    X(q[2]);
    H(q[0]);
    H(q[1]);
    H(q[2]);
    CNOT(q[0], q[2]);
    CNOT(q[1], q[2]);
    H(q[0]);
    H(q[1]);
    let r0 = M(q[0]);
    let r1 = M(q[1]);
    ResetAll(q);
    return (r0, r1);
}
