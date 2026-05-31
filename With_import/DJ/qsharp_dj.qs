namespace DJResearch {
    open Microsoft.Quantum.Intrinsic;
    open Microsoft.Quantum.Measurement;
    @EntryPoint()
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
        if (r0 == One) { X(q[0]); }
        if (r1 == One) { X(q[1]); }
        let r2 = M(q[2]);
        if (r2 == One) { X(q[2]); }
        return (r0, r1);
    }
}