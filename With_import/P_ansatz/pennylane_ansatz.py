import pennylane as qml
dev = qml.device("default.qubit", wires=3)
@qml.qnode(dev)
def ansatz(theta):
    qml.RY(theta, wires=0)
    qml.RY(theta, wires=1)
    qml.RY(theta, wires=2)
    qml.CNOT(wires=[0, 1])
    qml.CNOT(wires=[1, 2])  
    return qml.expval(qml.PauliZ(0))