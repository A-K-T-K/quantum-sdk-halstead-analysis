namespace BellResearch {
    open Microsoft.Quantum.Intrinsic;
    open Microsoft.Quantum.Measurement;
    @EntryPoint()
    operation BellState() : (Result, Result) {
        use q = Qubit[2];
        H(q[0]);
        CNOT(q[0], q[1]);
        let r0 = M(q[0]);
        let r1 = M(q[1]);
        if (r0 == One) { X(q[0]); }
        if (r1 == One) { X(q[1]); }
        return (r0, r1);
    }
}