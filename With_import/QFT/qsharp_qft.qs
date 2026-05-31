namespace QFTResearch {
    open Microsoft.Quantum.Intrinsic;
    open Microsoft.Quantum.Math;
    @EntryPoint()
    operation QFT3() : Unit {
        use q = Qubit[3];
        H(q[0]);
        Controlled R1([q[1]], (PI() / 2.0, q[0]));
        Controlled R1([q[2]], (PI() / 4.0, q[0]));
        H(q[1]);
        Controlled R1([q[2]], (PI() / 2.0, q[1]));
        H(q[2]);
        SWAP(q[0], q[2]);
        ResetAll(q);
    }
}