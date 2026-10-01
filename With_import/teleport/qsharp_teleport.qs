namespace TeleportResearch {
    open Microsoft.Quantum.Intrinsic;
    open Microsoft.Quantum.Measurement;
    @EntryPoint()
    operation Teleport() : (Result, Result, Result) {
        use q = Qubit[3];
        H(q[1]);
        CNOT(q[1], q[2]);
        H(q[0]);
        T(q[0]);
        CNOT(q[0], q[1]);
        H(q[0]);
        let m0 = M(q[0]);
        let m1 = M(q[1]);
        if (m1 == One) { X(q[2]); }
        if (m0 == One) { Z(q[2]); }
        let m2 = M(q[2]);
        ResetAll(q);
        return (m0, m1, m2);
    }
}
