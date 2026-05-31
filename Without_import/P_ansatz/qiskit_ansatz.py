theta = Parameter('θ')
qr = QuantumRegister(3)
qc = QuantumCircuit(qr)

qc.ry(theta, qr[0])
qc.ry(theta, qr[1])
qc.ry(theta, qr[2])

qc.cx(qr[0], qr[1])
qc.cx(qr[1], qr[2])