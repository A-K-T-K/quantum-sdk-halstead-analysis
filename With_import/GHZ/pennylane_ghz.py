import pennylane as qml
dev = qml.device("default.qubit", wires=3)
@qml.qnode(dev)
def circuit():
    qml.Hadamard(wires=0)
    qml.CNOT(wires=[0, 1])
    qml.CNOT(wires=[1, 2])
    return (
        qml.measure(wires=0),
        qml.measure(wires=1),
        qml.measure(wires=2)
    )