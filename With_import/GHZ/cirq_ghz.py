import cirq
q0, q1, q2 = cirq.LineQubit.range(3)
circuit = cirq.Circuit()
circuit.append(cirq.H(q0))
circuit.append(cirq.CNOT(q0, q1))
circuit.append(cirq.CNOT(q1, q2))
circuit.append(cirq.measure(q0, key='m0'))
circuit.append(cirq.measure(q1, key='m1'))
circuit.append(cirq.measure(q2, key='m2'))