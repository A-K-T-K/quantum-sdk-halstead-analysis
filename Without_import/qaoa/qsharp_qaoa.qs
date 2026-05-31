operation RunAnsatz() : Unit {
    Ansatz(0.785);
}
operation Ansatz(theta : Double) : Unit {
    use q = Qubit[3];
    Ry(theta, q[0]);
    Ry(theta, q[1]);
    Ry(theta, q[2]);
    CNOT(q[0], q[1]);
    CNOT(q[1], q[2]);
    ResetAll(q);
}