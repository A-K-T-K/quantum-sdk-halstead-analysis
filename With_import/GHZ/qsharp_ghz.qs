namespace GHZResearch {
    open Microsoft.Quantum.Diagnostics;
    open Microsoft.Quantum.Measurement;
    open Microsoft.Quantum.Intrinsic;
    @EntryPoint()
    operation GHZState() : (Result, Result, Result) {
        use q = Qubit[3];      
        H(q[0]);
        CNOT(q[0], q[1]);
        CNOT(q[1], q[2]);       
        let m0 = M(q[0]);
        let m1 = M(q[1]);
        let m2 = M(q[2]);        
        return (m0, m1, m2);
    }
}