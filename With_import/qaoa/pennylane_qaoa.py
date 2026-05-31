import pennylane as qml
dev = qml.device("default.qubit", wires=3)
@qml.qnode(dev)
def qaoa_layer(gamma, beta):
    for i in range(2):
        qml.IsingZZ(2 * gamma, wires=[i, i+1])
    for i in range(3):
        qml.RX(2 * beta, wires=i)      
    return qml.state()