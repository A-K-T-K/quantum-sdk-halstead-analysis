gamma = sympy.Symbol('gamma')
beta = sympy.Symbol('beta')
q = cirq.LineQubit.range(3)
circuit = cirq.Circuit()
for i in range(2):
    circuit.append(cirq.ZZPowGate(exponent=2*gamma/np.pi)(q[i], q[i+1]))
for i in range(3):
    circuit.append(cirq.rx(2*beta)(q[i]))