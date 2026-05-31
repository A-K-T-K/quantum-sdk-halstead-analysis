import pennylane as qml
dev = qml.device("default.qubit", wires=3)
@qml.qnode(dev)
def qft():
    qml.Hadamard(wires=0)
    qml.ControlledPhaseShift(np.pi/2, wires=[1, 0])
    qml.ControlledPhaseShift(np.pi/4, wires=[2, 0])
    qml.Hadamard(wires=1)
    qml.ControlledPhaseShift(np.pi/2, wires=[2, 1])
    qml.Hadamard(wires=2)
    qml.SWAP(wires=[0, 2]) 
    return qml.state()