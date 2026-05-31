gamma = Parameter('γ')
beta = Parameter('β')
qr = QuantumRegister(3)
qc = QuantumCircuit(qr)
for i in range(2):
    qc.rzz(2*gamma, qr[i], qr[i+1])
for i in range(3):
    qc.rx(2*beta, qr[i])