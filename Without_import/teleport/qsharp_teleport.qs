operation Teleport() : Unit {
    use q = Qubit[3];
    H(q[1]);
    CNOT(q[1], q[2]);
    H(q[0]);
    CNOT(q[0], q[1]);
    H(q[0]);
    let m0 = M(q[0]);
    let m1 = M(q[1]);
    if (m1 == One) { X(q[2]); }
    if (m0 == One) { Z(q[2]); }
    ResetAll(q);
}