import cirq
q = cirq.LineQubit.range(3)
circuit = cirq.Circuit()
circuit.append([cirq.H(q[1]), cirq.CNOT(q[1], q[2])])
circuit.append(cirq.H(q[0]))
circuit.append([cirq.CNOT(q[0], q[1]), cirq.H(q[0])])
circuit.append([cirq.measure(q[0], key='m0'), cirq.measure(q[1], key='m1')])
circuit.append(cirq.X(q[2]).with_classical_controls('m1'))
circuit.append(cirq.Z(q[2]).with_classical_controls('m0'))