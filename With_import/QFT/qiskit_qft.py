from qiskit import QuantumCircuit, QuantumRegister
import numpy as np
qr = QuantumRegister(3)
qc = QuantumCircuit(qr)
qc.h(qr[0])
qc.cp(np.pi/2, qr[1], qr[0])
qc.cp(np.pi/4, qr[2], qr[0])
qc.h(qr[1])
qc.cp(np.pi/2, qr[2], qr[1])
qc.h(qr[2])
qc.swap(qr[0], qr[2])