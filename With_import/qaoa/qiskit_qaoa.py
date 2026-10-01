from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit import Parameter
gamma = Parameter('γ')
beta = Parameter('β')
qr = QuantumRegister(3)
cr = ClassicalRegister(3)
qc = QuantumCircuit(qr, cr)
for i in range(3):
    qc.h(qr[i])
for i in range(2):
    qc.rzz(2 * gamma, qr[i], qr[i+1])
for i in range(3):
    qc.rx(2 * beta, qr[i])
for i in range(3):
    qc.measure(qr[i], cr[i])
