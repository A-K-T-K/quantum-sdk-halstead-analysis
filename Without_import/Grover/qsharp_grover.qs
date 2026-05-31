operation Grover3() : (Result, Result, Result) {
    use q = Qubit[3];
    H(q[0]); H(q[1]); H(q[2]);
    Controlled Z([q[0], q[1]], q[2]);
    H(q[0]); H(q[1]); H(q[2]);
    X(q[0]); X(q[1]); X(q[2]);
    H(q[2]);
    Controlled Z([q[0], q[1]], q[2]);
    H(q[2]);
    X(q[0]); X(q[1]); X(q[2]);
    H(q[0]); H(q[1]); H(q[2]);
    let r0 = M(q[0]);
    let r1 = M(q[1]);
    let r2 = M(q[2]);
    ResetAll(q);
    return (r0, r1, r2);
}