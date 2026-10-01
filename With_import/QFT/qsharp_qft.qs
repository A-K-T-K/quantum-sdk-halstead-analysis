namespace QFTResearch {
    open Microsoft.Quantum.Intrinsic;
    open Microsoft.Quantum.Math;
    @EntryPoint()
    operation QFT3() : (Result, Result, Result) {
        use q = Qubit[3];
        H(q[0]);
        Controlled R1([q[1]], (PI() / 2.0, q[0]));
        Controlled R1([q[2]], (PI() / 4.0, q[0]));
        H(q[1]);
        Controlled R1([q[2]], (PI() / 2.0, q[1]));
        H(q[2]);
        SWAP(q[0], q[2]);
        let r0 = M(q[0]);
        let r1 = M(q[1]);
        let r2 = M(q[2]);
        ResetAll(q);
        return (r0, r1, r2);
    }
}
