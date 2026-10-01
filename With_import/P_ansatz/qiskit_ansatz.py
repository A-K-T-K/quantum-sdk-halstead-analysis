from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit import Parameter
theta = Parameter('θ')
qr = QuantumRegister(3)
cr = ClassicalRegister(3)
qc = QuantumCircuit(qr, cr)
qc.ry(theta, qr[0])
qc.ry(theta, qr[1])
qc.ry(theta, qr[2])
qc.cx(qr[0], qr[1])
qc.cx(qr[1], qr[2])
qc.measure(qr[0], cr[0])
qc.measure(qr[1], cr[1])
qc.measure(qr[2], cr[2])
