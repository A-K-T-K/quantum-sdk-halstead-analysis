dev = qml.device("default.qubit", wires=2)
@qml.qnode(dev)
def circuit():
    qml.Hadamard(wires=0)
    qml.CNOT(wires=[0, 1])
    return qml.measure(wires=0), qml.measure(wires=1)