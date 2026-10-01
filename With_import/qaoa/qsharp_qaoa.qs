namespace QAOAResearch {
    open Microsoft.Quantum.Intrinsic;
    open Microsoft.Quantum.Measurement;
    operation QAOALayer(gamma : Double, beta : Double) : Result[] {
        use q = Qubit[3];
        for i in 0..2 {
            H(q[i]);
        }
        for i in 0..1 {
            Rzz(2.0 * gamma, q[i], q[i + 1]);
        }
        for i in 0..2 {
            Rx(2.0 * beta, q[i]);
        }
        mutable r = [];
        for i in 0..2 {
            set r += [M(q[i])];
        }
        ResetAll(q);
        return r;
    }
}
